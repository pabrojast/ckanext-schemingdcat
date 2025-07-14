# encoding: utf-8
import ckan.model as model
import ckan.lib.base as base
import ckan.logic as logic
from flask import Blueprint, request, redirect, url_for, jsonify
from ckan.logic import ValidationError
from ckan.plugins.toolkit import render, g, h, _, config as tk_config
import tempfile
import os
import time
import re
import importlib

import ckanext.schemingdcat.utils as sdct_utils
import ckanext.schemingdcat.helpers as sdct_helpers
from ckanext.schemingdcat.rate_limiter import rate_limiter
from ckanext.schemingdcat.spatial_extent import extent_extractor
from ckanext.schemingdcat.file_finder import find_uploaded_file, filename_similarity

from logging import getLogger

logger = getLogger(__name__)
get_action = logic.get_action

schemingdcat = Blueprint(u'schemingdcat', __name__)

def endpoints():
    return render('schemingdcat/endpoints/index.html',extra_vars={
            u'endpoints': sdct_helpers.schemingdcat_get_catalog_endpoints(),
        })
    
def metadata_templates():
    return render('schemingdcat/metadata_templates/index.html',extra_vars={
            u'metadata_templates': sdct_helpers.schemingdcat_get_catalog_endpoints(),
        })

schemingdcat.add_url_rule("/endpoints/", view_func=endpoints, endpoint="endpoint_index", strict_slashes=False)

schemingdcat.add_url_rule("/metadata-templates/", view_func=metadata_templates, endpoint="metadata_templates", strict_slashes=False)

@schemingdcat.route(u'/dataset/linked_data/<id>')
def index(id):
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'for_view': True,
        u'auth_user_obj': g.userobj
    }
    data_dict = {u'id': id, u'include_tracking': True}

    # check if package exists
    try:
        pkg_dict = get_action(u'package_show')(context, data_dict)
        pkg = context[u'package']
        schema = get_action(u'package_show')(context, data_dict)
    except (logic.NotFound, logic.NotAuthorized):
        return base.abort(404, _(u'Dataset {dataset_id} not found').format(dataset_id=id))

    return render('schemingdcat/custom_data/index.html',extra_vars={
            u'pkg_dict': pkg_dict,
            u'endpoint': 'dcat.read_dataset',
            u'data_list': sdct_utils.get_linked_data(id),
        })

@schemingdcat.route(u'/dataset/geospatial_metadata/<id>')
def geospatial_metadata(id):
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'for_view': True,
        u'auth_user_obj': g.userobj
    }
    data_dict = {u'id': id, u'include_tracking': True}

    # check if package exists
    try:
        pkg_dict = get_action(u'package_show')(context, data_dict)
        pkg = context[u'package']
    except (logic.NotFound, logic.NotAuthorized):
        return base.abort(404, _(u'Dataset {dataset_id} not found').format(dataset_id=id))

    return render('schemingdcat/custom_data/index.html',extra_vars={
            u'pkg_dict': pkg_dict,
            u'id': id,
            u'data_list': sdct_utils.get_geospatial_metadata(),
        })

@schemingdcat.route('/verify-captcha', methods=['POST'])
def verify_captcha():
    """Verify captcha answer and redirect back."""
    captcha_answer = request.form.get('captcha_answer', '')
    redirect_url = request.form.get('redirect_url', h.url_for('dataset.search'))
    
    if rate_limiter.verify_captcha(captcha_answer):
        # Captcha verified successfully
        h.flash_success(_('Verification successful. You can continue searching.'))
        return redirect(redirect_url)
    else:
        # Captcha failed - show rate limited page with error
        captcha_question = rate_limiter.generate_captcha()
        return render('schemingdcat/rate_limited.html', extra_vars={
            'needs_captcha': True,
            'captcha_question': captcha_question,
            'captcha_error': True,
            'search_limit': rate_limiter.search_limit,
            'time_window': rate_limiter.time_window,
            'captcha_after': rate_limiter.captcha_required_after
        })

@schemingdcat.route('/api/spatial-extent-status', methods=['GET'])
def spatial_extent_status():
    """Get status of spatial extent extraction system."""
    try:
        from ckanext.schemingdcat.spatial_extent import get_spatial_system_status
        status = get_spatial_system_status()
        logger.debug(f"Spatial extent system status: {status}")
        return jsonify(status)
    except Exception as e:
        logger.debug(f"Error getting spatial extent status: {str(e)}")
        return jsonify({
            'available': False,
            'error': str(e)
        }), 500

@schemingdcat.route('/api/extract-spatial-extent', methods=['POST'])
def extract_spatial_extent():
    """Extract spatial extent from uploaded geospatial file."""
    try:
        logger.info("Spatial extent extraction request received")
        
        # First check if any spatial handlers are available
        if not any(extent_extractor.available_handlers.values()):
            logger.info("No spatial handlers available - dependencies missing")
            return jsonify({
                'success': False,
                'error': 'Spatial extent extraction not available - missing required dependencies'
            }), 400
        
        # Check if file is in request
        if 'file' not in request.files:
            logger.info("No file provided in request")
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        use_uploaded_file = request.form.get('use_uploaded_file', 'false').lower() == 'true'
        
        if file.filename == '':
            logger.info("Empty filename provided")
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        logger.info(f"Processing file: {file.filename}, size: {file.content_length if hasattr(file, 'content_length') else 'unknown'}")
        logger.info(f"Use uploaded file flag: {use_uploaded_file}")
        
        # If use_uploaded_file is True, try to find the file in CKAN's upload directory
        if use_uploaded_file:
            logger.info("Attempting to find uploaded file in CKAN storage")
            
            # Try to get CloudStorage helper for Azure URLs
            azure_direct_upload = False
            
            # First check if the CloudStorage module is available
            if is_module_available('ckanext.cloudstorage'):
                try:
                    # Import the helpers module
                    from ckanext.cloudstorage import helpers as cloudstorage_helpers
                    
                    # Check if the helper function exists
                    if hasattr(cloudstorage_helpers, 'use_azure_direct_upload') and callable(cloudstorage_helpers.use_azure_direct_upload):
                        azure_direct_upload = cloudstorage_helpers.use_azure_direct_upload()
                        logger.info(f"Azure direct upload enabled: {azure_direct_upload}")
                    else:
                        # Alternative method to detect Azure storage if the helper isn't available
                        if is_module_available('ckanext.cloudstorage.config'):
                            from ckanext.cloudstorage.config import config as cloudstorage_config
                            azure_direct_upload = cloudstorage_config.get('ckanext.cloudstorage.driver') == 'AZURE_BLOBS'
                            logger.info(f"Azure direct upload inferred from CloudStorage config: {azure_direct_upload}")
                        else:
                            # Fall back to checking CKAN config directly
                            azure_direct_upload = tk_config.get('ckanext.cloudstorage.driver', '').upper() == 'AZURE_BLOBS'
                            logger.info(f"Azure direct upload inferred from CKAN config: {azure_direct_upload}")
                except Exception as e:
                    logger.info(f"CloudStorage helpers access error: {str(e)}")
                    
                    # One last attempt - directly check CKAN config
                    try:
                        azure_direct_upload = tk_config.get('ckanext.cloudstorage.driver', '').upper() == 'AZURE_BLOBS'
                        logger.info(f"Azure direct upload determined from CKAN config: {azure_direct_upload}")
                    except Exception:
                        azure_direct_upload = False
            else:
                logger.info("CloudStorage module is not available")
                azure_direct_upload = False
            
            # First try to find the local file
            file_path = find_uploaded_file(file.filename)
            logger.info(f"Attempted to find file, result path: {file_path if file_path else 'Not found'}")
            
            # Only try Azure if we haven't found the file locally and Azure is enabled
            if azure_direct_upload and (not file_path or not os.path.exists(file_path)):
                logger.info("Azure direct upload is enabled - checking for Azure URL")
                azure_url = None
                
                # Check if CloudStorage module is available
                if is_module_available('ckanext.cloudstorage'):
                    try:
                        from ckanext.cloudstorage import storage
                        # Generate Azure URL for direct access
                        container_name = tk_config.get('ckanext.cloudstorage.container_name', 'resources')  # Get from config or default to "resources"
                        logger.info(f"Using container: {container_name}")
                        
                        # Try to generate an Azure URL from the CloudStorage driver
                        # The get_driver() function requires a provider parameter in newer versions
                        try:
                            # First try with the provider parameter (newer versions)
                            # The provider is typically 'AZURE_BLOBS' for Azure storage
                            driver = storage.get_driver('AZURE_BLOBS')
                        except TypeError:
                            # Fall back to the old API without parameters
                            driver = storage.get_driver()
                            
                        # If the driver still doesn't have the required get_url method,
                        # try the direct Azure approach
                        if not hasattr(driver, 'get_url') or not callable(driver.get_url):
                            logger.info("Driver doesn't have get_url method, trying direct Azure access")
                            try:
                                from azure.storage.blob import BlobServiceClient
                                
                                # Get Azure connection string from config using toolkit we imported at the top
                                azure_conn_string = tk_config.get('ckanext.cloudstorage.azure.connection_string', '')
                                if not azure_conn_string:
                                    # Try to build connection string from account name and key
                                    account_name = tk_config.get('ckanext.cloudstorage.azure.account_name', '')
                                    account_key = tk_config.get('ckanext.cloudstorage.azure.account_key', '')
                                    if account_name and account_key:
                                        azure_conn_string = f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={account_key};EndpointSuffix=core.windows.net"
                                
                                if azure_conn_string:
                                    # Get container name, default to 'resources'
                                    # Use the container name from earlier or get it from config
                                    if not container_name:
                                        container_name = tk_config.get('ckanext.cloudstorage.container_name', 'resources')
                                    
                                    # Create the blob client
                                    blob_service_client = BlobServiceClient.from_connection_string(azure_conn_string)
                                    container_client = blob_service_client.get_container_client(container_name)
                                    
                                    # Get the blob URL
                                    blob_client = container_client.get_blob_client(file.filename)
                                    azure_url = blob_client.url
                                    logger.info(f"Generated Azure URL directly: {azure_url}")
                            except Exception as azure_error:
                                logger.info(f"Could not generate Azure URL directly: {str(azure_error)}")
                        
                        if hasattr(driver, 'get_url') and callable(driver.get_url):
                            azure_url = driver.get_url(file.filename)
                            logger.info(f"Generated Azure URL: {azure_url}")
                        else:
                            logger.info("Driver does not have get_url method")
                    except Exception as driver_error:
                        logger.info(f"Could not generate Azure URL: {str(driver_error)}")
                else:
                    logger.info("CloudStorage module is not available for Azure URL generation")
                    azure_url = None
                
                # If we have an Azure URL, use it
                if azure_url:
                    # Process using the Azure URL directly
                    logger.info(f"Using Azure URL for spatial extent extraction: {azure_url}")
                    # We need to download the file from Azure first since the extraction functions expect a local file
                    import requests
                    import shutil
                    
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1])
                    try:
                        logger.info(f"Downloading file from Azure URL to: {temp_file.name}")
                        response = requests.get(azure_url, stream=True)
                        response.raise_for_status()
                        with open(temp_file.name, 'wb') as f:
                            shutil.copyfileobj(response.raw, f)
                            
                        # Check if file was downloaded correctly
                        file_size = os.path.getsize(temp_file.name)
                        logger.info(f"Downloaded file size: {file_size} bytes")
                        
                        if file_size > 0:
                            # Extract spatial extent from the downloaded file
                            extent = extent_extractor.extract_extent(temp_file.name, trust_extension=True)
                            logger.info(f"Extraction result from Azure URL: {extent}")
                            
                            if extent:
                                logger.info("Spatial extent extraction successful from Azure URL")
                                return jsonify({
                                    'success': True,
                                    'extent': extent,
                                    'message': 'Spatial extent extracted successfully from Azure URL'
                                })
                        else:
                            logger.info("Downloaded file from Azure URL is empty")
                    except Exception as e:
                        logger.error(f"Error downloading from Azure URL: {str(e)}")
                    finally:
                        # Clean up temporary file
                        try:
                            os.unlink(temp_file.name)
                        except Exception:
                            pass
            
            # Fall back to local file if Azure URL approach didn't work
            if file_path and os.path.exists(file_path):
                logger.info(f"Found uploaded file at: {file_path}")
                # Verify file has content
                file_size = os.path.getsize(file_path)
                if file_size == 0:
                    logger.info(f"Found file but it has 0 bytes: {file_path}")
                    return jsonify({
                        'success': False,
                        'error': 'Upload is still in progress or file is empty - please try again later'
                    }), 400
                    
                # Process the uploaded file directly - trust the extension since it's an uploaded file
                extent = extent_extractor.extract_extent(file_path, trust_extension=True)
                logger.info(f"Extraction result from uploaded file: {extent}")
                
                if extent:
                    logger.info("Spatial extent extraction successful from uploaded file")
                    return jsonify({
                        'success': True,
                        'extent': extent,
                        'message': 'Spatial extent extracted successfully from uploaded file'
                    })
                else:
                    logger.info("Failed to extract spatial extent from uploaded file")
                    return jsonify({
                        'success': False,
                        'error': 'Failed to extract spatial extent from uploaded file'
                    }), 400
            else:
                logger.info(f"Could not find uploaded file: {file.filename}")
                # If use_uploaded_file is true but we can't find the file, 
                # it probably means the upload is still in progress or hasn't been processed yet
                # Provide more detailed error information
                search_paths = find_uploaded_file(file.filename, return_search_paths=True)
                logger.info(f"Searched paths: {search_paths}")
                
                return jsonify({
                    'success': False,
                    'error': 'File not found in storage - upload may still be in progress',
                    'detail': f"File '{file.filename}' was not found in any of the expected upload locations. " +
                              f"If using CloudStorage, the file may not be accessible yet."
                }), 400
        
        # If we're using an uploaded file but couldn't find it, we should have already returned an error
        # No need to check extension again
        
        # For immediate file extraction (not use_uploaded_file), do full validation
        if not use_uploaded_file:
            can_extract = extent_extractor.can_extract_extent(file.filename)
            logger.info(f"Can extract extent from {file.filename}: {can_extract}")
            
            if not can_extract:
                logger.info(f"Unsupported file type for spatial extent extraction: {file.filename}")
                # Get more details about why it's unsupported
                ext = os.path.splitext(file.filename)[1].lower().lstrip('.')
                logger.info(f"File extension: {ext}")
                logger.info(f"Supported extensions: {list(extent_extractor.SUPPORTED_EXTENSIONS.keys())}")
                logger.info(f"Available handlers: {extent_extractor.available_handlers}")
                
                return jsonify({
                    'success': False,
                    'error': 'Unsupported file type for spatial extent extraction'
                }), 400
        else:
            # If we got here with use_uploaded_file=True, it means we need to check extension
            ext = os.path.splitext(file.filename)[1].lower().lstrip('.')
            
            # Just check if the extension is in the supported list
            if ext not in extent_extractor.SUPPORTED_EXTENSIONS:
                logger.info(f"Unsupported file extension for spatial extraction: {ext}")
                return jsonify({
                    'success': False,
                    'error': f'Unsupported file extension for spatial extraction: {ext}'
                }), 400
                
            logger.info(f"File extension {ext} is supported for spatial extraction")
        
        # If use_uploaded_file is True, we shouldn't get here unless there's a logic error
        # The temp file would be empty anyway, so return an error
        if use_uploaded_file:
            logger.warning("Logic error: attempting to process temp file with use_uploaded_file=True")
            return jsonify({
                'success': False,
                'error': 'Upload not yet complete - please try again later'
            }), 400
            
        # Create temporary file with proper cleanup
        tmp_file = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, 
                                           suffix=os.path.splitext(file.filename)[1]) as tmp_file:
                # Save uploaded file to temporary location
                logger.info(f"Saving file to temporary location: {tmp_file.name}")
                file.save(tmp_file.name)
                
                # Verify file was saved correctly
                file_size = os.path.getsize(tmp_file.name) if os.path.exists(tmp_file.name) else 0
                logger.info(f"File saved to temporary location: {tmp_file.name}, size: {file_size} bytes")
                
                if file_size == 0:
                    logger.info("Saved file is empty")
                    return jsonify({
                        'success': False,
                        'error': 'Uploaded file is empty'
                    }), 400
                
                # For ZIP files, let's check the contents before extraction
                if file.filename.lower().endswith('.zip'):
                    try:
                        import zipfile
                        with zipfile.ZipFile(tmp_file.name, 'r') as zip_ref:
                            file_list = zip_ref.namelist()
                            logger.info(f"ZIP file contains: {file_list}")
                            
                            # Check for shapefile components
                            has_shp = any(f.lower().endswith('.shp') for f in file_list)
                            has_shx = any(f.lower().endswith('.shx') for f in file_list)
                            has_dbf = any(f.lower().endswith('.dbf') for f in file_list)
                            logger.info(f"Shapefile components - .shp: {has_shp}, .shx: {has_shx}, .dbf: {has_dbf}")
                    except Exception as zip_error:
                        logger.info(f"Error checking ZIP contents: {str(zip_error)}")
                
                # Extract spatial extent
                logger.info("Starting spatial extent extraction...")
                extent = extent_extractor.extract_extent(tmp_file.name)
                logger.info(f"Extraction result: {extent}")
                
                if extent:
                    logger.info("Spatial extent extraction successful")
                    return jsonify({
                        'success': True,
                        'extent': extent,
                        'message': 'Spatial extent extracted successfully'
                    })
                else:
                    logger.info("Failed to extract spatial extent from file - extent is None")
                    return jsonify({
                        'success': False,
                        'error': 'Failed to extract spatial extent from file'
                    }), 400
        finally:
            # Ensure cleanup even if extraction fails
            if tmp_file and os.path.exists(tmp_file.name):
                try:
                    os.unlink(tmp_file.name)
                    logger.info(f"Cleaned up temporary file: {tmp_file.name}")
                except OSError as cleanup_error:
                    logger.info(f"Failed to cleanup temporary file: {cleanup_error}")
                
    except Exception as e:
        logger.error(f"Error extracting spatial extent: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error during spatial extent extraction'
        }), 500

@schemingdcat.route('/api/1/util/snippet/<path:snippet_path>')
def handle_malformed_snippet_url(snippet_path):
    """Handle cases where the snippet URL might be malformed with an extra quote or other characters."""
    # Remove any trailing quotes or problematic characters
    clean_path = re.sub(r'["\'\s]+$', '', snippet_path)
    
    # Extract resource_id if present in query string
    resource_id = request.args.get('resource_id')
    
    # Check if we're looking for our specific template
    if clean_path == 'scd_api_info.html' or 'scd_api_info.html' in clean_path:
        logger.info(f"Handling potentially malformed snippet URL: {snippet_path}")
        
        # Redirect to the proper URL format or render the template directly
        extra_vars = {'resource_id': resource_id} if resource_id else {}
        
        try:
            return render('ajax_snippets/scd_api_info.html', extra_vars=extra_vars)
        except Exception as e:
            logger.error(f"Error rendering scd_api_info template: {str(e)}")
            return base.abort(404, _('Template not found'))
    
    # For other templates, just pass through to the standard CKAN handler
    return base.abort(404, _('Template not found'))

def is_module_available(module_name):
    """Check if a module is available for import without raising an exception."""
    try:
        importlib.import_module(module_name)
        return True
    except (ImportError, ModuleNotFoundError):
        return False

