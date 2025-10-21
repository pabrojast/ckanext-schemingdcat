# encoding: utf-8
"""
API endpoints for spatial extent extraction.
"""

import logging
import importlib
from flask import request, jsonify

log = logging.getLogger(__name__)


def is_module_available(module_name):
    """Check if a module is available for import without raising an exception."""
    try:
        importlib.import_module(module_name)
        return True
    except (ImportError, ModuleNotFoundError):
        return False


def extract_spatial_extent_endpoint():
    """
    API endpoint to extract spatial extent from uploaded geospatial files.
    
    This endpoint can work with:
    1. Direct file uploads (multipart/form-data with 'file')
    2. Resource URLs (JSON with 'resource_url' and 'resource_format')
    
    This endpoint is designed for frontend use only and does not interfere 
    with CKAN's core API operations.
    """
    try:
        if not is_module_available('ckanext.schemingdcat.upload'):
            return jsonify({
                'success': False,
                'error': 'Spatial extent extraction not available',
                'extent': None
            }), 400

        from ckanext.schemingdcat.upload import extent_extractor
        
        # Check if it's a direct file upload
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return jsonify({
                    'success': False,
                    'error': 'No file selected',
                    'extent': None
                }), 400
            
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
        log.error(f"Error in spatial extent extraction API: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Internal error: {str(e)}',
            'extent': None
        }), 500


def extract_spatial_extent_from_resource_endpoint():
    """
    API endpoint to extract spatial extent from uploaded resources (post-upload processing).
    
    This endpoint is designed for processing resources that have already been uploaded
    to cloud storage (like Azure) and processes them based on their format.
    """
    try:
        if not is_module_available('ckanext.schemingdcat.upload'):
            return jsonify({
                'success': False,
                'error': 'Spatial extent extraction not available',
                'extent': None
            }), 400

        from ckanext.schemingdcat.upload import extent_extractor
        
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
        
        log.info(f"Processing resource for spatial extent: {resource_url} (format: {resource_format})")
        
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
        log.error(f"Error in resource spatial extent extraction API: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Internal error: {str(e)}',
            'extent': None
        }), 500
