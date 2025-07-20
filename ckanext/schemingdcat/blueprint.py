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

from logging import getLogger
import ckan.plugins.toolkit as toolkit

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

@schemingdcat.route('/api/spatial-extent-status/<resource_id>', methods=['GET'])
def get_spatial_extent_status(resource_id):
    """
    API endpoint para consultar el estado del procesamiento de spatial extent de un recurso.
    
    Permite verificar si el procesamiento asíncrono ha terminado y si se actualizó el dataset.
    """
    try:
        # Verificar que el recurso existe
        context = {'ignore_auth': True}
        try:
            resource = toolkit.get_action('resource_show')(context, {'id': resource_id})
        except toolkit.ObjectNotFound:
            return jsonify({
                'success': False,
                'error': 'Resource not found',
                'status': 'not_found'
            }), 404
        
        # Obtener el dataset padre
        package_id = resource.get('package_id')
        if not package_id:
            return jsonify({
                'success': False,
                'error': 'No package_id found for resource',
                'status': 'error'
            }), 400
        
        # Verificar si el RESOURCE tiene spatial extent
        try:
            # El resource ya lo tenemos, verificar spatial_extent directamente
            spatial_extent = resource.get('spatial_extent')
            
            if spatial_extent and spatial_extent.strip():
                # Verificar si es un extent válido
                try:
                    import json
                    extent_data = json.loads(spatial_extent)
                    if extent_data.get('type') == 'Polygon' and extent_data.get('coordinates'):
                        return jsonify({
                            'success': True,
                            'status': 'completed',
                            'message': 'Spatial extent extraction completed',
                            'has_spatial_extent': True,
                            'spatial_extent': extent_data
                        })
                except:
                    pass
            
            # No hay spatial extent o no es válido
            return jsonify({
                'success': True,
                'status': 'pending',
                'message': 'Spatial extent extraction may still be processing',
                'has_spatial_extent': False,
                'spatial_extent': None
            })
                    
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error checking dataset: {str(e)}',
                'status': 'error'
            }), 500
            
    except Exception as e:
        logger.error(f"Error checking spatial extent status for resource {resource_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}',
            'status': 'error'
        }), 500


@schemingdcat.route('/api/extract-spatial-extent', methods=['POST'])
def extract_spatial_extent():
    """
    API endpoint to extract spatial extent from uploaded geospatial files.
    
    This endpoint can work with:
    1. Direct file uploads (multipart/form-data with 'file')
    2. Resource URLs (JSON with 'resource_url' and 'resource_format')
    
    This endpoint is designed for frontend use only and does not interfere 
    with CKAN's core API operations.
    """
    try:
        # Check if spatial extent extraction is available
        if not is_module_available('ckanext.schemingdcat.spatial_extent'):
            return jsonify({
                'success': False,
                'error': 'Spatial extent extraction not available',
                'extent': None
            }), 400

        from ckanext.schemingdcat.spatial_extent import extent_extractor
        
        # Check if it's a direct file upload
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return jsonify({
                    'success': False,
                    'error': 'No file selected',
                    'extent': None
                }), 400
            
            # Extract extent from uploaded file
            extent = extent_extractor.extract_extent_from_upload(file)
            
        # Check if it's a resource URL processing request
        elif request.is_json:
            data = request.get_json()
            resource_url = data.get('resource_url')
            resource_format = data.get('resource_format', '').lower()
            
            if not resource_url:
                return jsonify({
                    'success': False,
                    'error': 'No resource_url provided',
                    'extent': None
                }), 400
            
            # Extract extent from resource URL
            extent = extent_extractor.extract_extent_from_url(resource_url, resource_format)
            
        else:
            return jsonify({
                'success': False,
                'error': 'No file or resource_url provided',
                'extent': None
            }), 400
        
        if extent:
            return jsonify({
                'success': True,
                'error': None,
                'extent': extent
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Could not extract spatial extent from file',
                'extent': None
            }), 400
            
    except Exception as e:
        logger.error(f"Error in spatial extent extraction API: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Error processing file: {str(e)}',
            'extent': None
        }), 500


@schemingdcat.route('/api/analyze-file-comprehensive', methods=['POST'])
def analyze_file_comprehensive():
    """
    API endpoint to extract comprehensive metadata from uploaded files.
    
    This endpoint extracts all available metadata including:
    - Spatial information (extent, CRS, resolution, etc.)
    - Data information (fields, statistics, domains)
    - Technical information (file size, compression, integrity)
    - Content-specific information (pages, sheets, text content)
    
    This endpoint can work with:
    1. Direct file uploads (multipart/form-data with 'file')
    2. Resource URLs (JSON with 'resource_url' and 'resource_format')
    """
    try:
        # Check if comprehensive analysis is available
        if not is_module_available('ckanext.schemingdcat.spatial_extent'):
            return jsonify({
                'success': False,
                'error': 'File analysis not available',
                'metadata': {}
            }), 400

        from ckanext.schemingdcat.spatial_extent import analyze_upload_file, analyze_file_comprehensive
        
        # Check if it's a direct file upload
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return jsonify({
                    'success': False,
                    'error': 'No file selected',
                    'metadata': {}
                }), 400
            
            # Analyze uploaded file comprehensively
            metadata = analyze_upload_file(file)
            
        # Check if it's a resource URL processing request
        elif request.is_json:
            data = request.get_json()
            resource_url = data.get('resource_url')
            resource_format = data.get('resource_format', '').lower()
            
            if not resource_url:
                return jsonify({
                    'success': False,
                    'error': 'No resource_url provided',
                    'metadata': {}
                }), 400
            
            # For URL analysis, we need to download and analyze
            import tempfile
            import urllib.request
            from ckanext.schemingdcat.spatial_extent import FileAnalyzer
            
            try:
                analyzer = FileAnalyzer()
                ext = resource_format.lower() if resource_format else 'unknown'
                
                # Create temporary file with proper extension
                suffix = f".{ext}" if ext and ext != 'unknown' else ""
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                    # Download file
                    req = urllib.request.Request(resource_url)
                    req.add_header('User-Agent', 'CKAN-SchemingDCAT-FileAnalyzer/1.0')
                    
                    with urllib.request.urlopen(req, timeout=30) as response:
                        chunk_size = 8192
                        total_size = 0
                        while True:
                            chunk = response.read(chunk_size)
                            if not chunk:
                                break
                            tmp_file.write(chunk)
                            total_size += len(chunk)
                            # Limit file size to 100MB
                            if total_size > 100 * 1024 * 1024:
                                raise Exception("File too large")
                    
                    tmp_file.flush()
                    
                    if total_size == 0:
                        raise Exception("Downloaded file is empty")
                    
                    # Analyze downloaded file
                    metadata = analyzer.analyze_file(tmp_file.name, trust_extension=True)
                    
                    # Clean up
                    import os
                    try:
                        os.unlink(tmp_file.name)
                    except Exception:
                        pass
                        
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f'Error processing file from URL: {str(e)}',
                    'metadata': {}
                }), 400
            
        else:
            return jsonify({
                'success': False,
                'error': 'No file or resource_url provided',
                'metadata': {}
            }), 400
        
        if metadata:
            return jsonify({
                'success': True,
                'error': None,
                'metadata': metadata
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Could not extract metadata from file',
                'metadata': {}
            }), 400
            
    except Exception as e:
        logger.error(f"Error in comprehensive file analysis API: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Internal error: {str(e)}',
            'metadata': {}
        }), 500

@schemingdcat.route('/api/extract-spatial-extent-from-resource', methods=['POST'])
def extract_spatial_extent_from_resource():
    """
    API endpoint to extract spatial extent from uploaded resources (post-upload processing).
    
    This endpoint is designed for processing resources that have already been uploaded
    to cloud storage (like Azure) and processes them based on their format.
    """
    try:
        # Check if spatial extent extraction is available
        if not is_module_available('ckanext.schemingdcat.spatial_extent'):
            return jsonify({
                'success': False,
                'error': 'Spatial extent extraction not available',
                'extent': None
            }), 400

        from ckanext.schemingdcat.spatial_extent import extent_extractor
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided',
                'extent': None
            }), 400
        
        resource_url = data.get('resource_url')
        resource_format = data.get('resource_format', '').upper()
        
        if not resource_url:
            return jsonify({
                'success': False,
                'error': 'No resource_url provided',
                'extent': None
            }), 400
        
        logger.info(f"Processing resource for spatial extent: {resource_url} (format: {resource_format})")
        
        # Extract extent from resource
        extent = extent_extractor.extract_extent_from_resource(resource_url, resource_format)
        
        if extent:
            return jsonify({
                'success': True,
                'error': None,
                'extent': extent,
                'processed_url': resource_url,
                'format': resource_format
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Could not extract spatial extent from resource',
                'extent': None,
                'processed_url': resource_url,
                'format': resource_format
            }), 400
            
    except Exception as e:
        logger.error(f"Error in resource spatial extent extraction API: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Internal error: {str(e)}',
            'extent': None
        }), 500

