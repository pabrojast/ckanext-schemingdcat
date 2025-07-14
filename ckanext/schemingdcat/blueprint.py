# encoding: utf-8
import ckan.model as model
import ckan.lib.base as base
import ckan.logic as logic
from flask import Blueprint, request, redirect, url_for, jsonify
from ckan.logic import ValidationError
from ckan.plugins.toolkit import render, g, h, _
import tempfile
import os
import time

import ckanext.schemingdcat.utils as sdct_utils
import ckanext.schemingdcat.helpers as sdct_helpers
from ckanext.schemingdcat.rate_limiter import rate_limiter
from ckanext.schemingdcat.spatial_extent import extent_extractor

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
        return base.abort(404, _(u'Dataset {dataset} not found').format({dataset:id}))

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
        return base.abort(404, _(u'Dataset {dataset} not found').format({dataset:id}))

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
            file_path = find_uploaded_file(file.filename)
            if file_path and os.path.exists(file_path):
                logger.info(f"Found uploaded file at: {file_path}")
                # Process the uploaded file directly
                extent = extent_extractor.extract_extent(file_path)
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
                logger.info(f"Could not find uploaded file: {file.filename}, falling back to temporary file processing")
        
        # Check if it's a supported spatial file
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

def find_uploaded_file(filename):
    """
    Try to find a recently uploaded file in CKAN's storage directories.
    
    Args:
        filename: The name of the file to find
        
    Returns:
        Full path to the file if found, None otherwise
    """
    try:
        # Common upload paths in CKAN
        upload_paths = []
        
        # Try to get the storage path from CKAN config
        try:
            import ckan.lib.uploader as uploader
            storage_path = uploader.get_storage_path()
            if storage_path:
                upload_paths.extend([
                    os.path.join(storage_path, 'storage', 'uploads'),
                    os.path.join(storage_path, 'uploads'),
                    storage_path
                ])
        except Exception as e:
            logger.info(f"Could not get CKAN storage path: {str(e)}")
        
        # Fallback paths
        upload_paths.extend([
            '/var/lib/ckan/default/storage/uploads',
            '/usr/lib/ckan/default/storage/uploads',
            '/tmp/uploads',
            tempfile.gettempdir()
        ])
        
        logger.info(f"Searching for file {filename} in paths: {upload_paths}")
        
        # Search in each path
        for base_path in upload_paths:
            if not os.path.exists(base_path):
                continue
                
            # Direct file in base path
            file_path = os.path.join(base_path, filename)
            if os.path.exists(file_path):
                logger.info(f"Found file at: {file_path}")
                return file_path
            
            # Search in subdirectories (recent uploads)
            try:
                for root, dirs, files in os.walk(base_path):
                    if filename in files:
                        full_path = os.path.join(root, filename)
                        # Check if file is recent (within last 10 minutes)
                        if os.path.getmtime(full_path) > (time.time() - 600):
                            logger.info(f"Found recent file at: {full_path}")
                            return full_path
            except Exception as e:
                logger.info(f"Error walking directory {base_path}: {str(e)}")
                continue
        
        logger.info(f"File {filename} not found in any upload paths")
        return None
        
    except Exception as e:
        logger.error(f"Error searching for uploaded file {filename}: {str(e)}")
        return None