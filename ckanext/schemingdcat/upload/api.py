# encoding: utf-8
"""
API endpoints for spatial extent extraction and Azure direct upload.
"""

import logging
import importlib
from datetime import datetime, timedelta
from flask import request, jsonify
import ckan.plugins.toolkit as toolkit

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


def get_azure_upload_url_endpoint():
    """
    API endpoint to generate Azure Blob Storage SAS URL for direct upload.
    
    This allows frontend to upload files directly to Azure without going through CKAN backend.
    
    Expected JSON body:
    {
        "resource_id": "xxx",
        "filename": "myfile.csv",
        "content_type": "text/csv"
    }
    
    Returns:
    {
        "success": true,
        "upload_url": "https://...",
        "expires_at": "2025-10-21T19:00:00Z"
    }
    """
    try:
        # Check if cloudstorage is available
        if not is_module_available('ckanext.cloudstorage'):
            return jsonify({
                'success': False,
                'error': 'CloudStorage not available'
            }), 400
        
        from ckanext.cloudstorage.storage import ResourceCloudStorage
        
        # Get request data
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': 'Request must be JSON'
            }), 400
        
        data = request.get_json()
        resource_id = data.get('resource_id')
        filename = data.get('filename')
        content_type = data.get('content_type', 'application/octet-stream')
        
        if not resource_id or not filename:
            return jsonify({
                'success': False,
                'error': 'resource_id and filename are required'
            }), 400
        
        # Check if user has permission to upload to this resource
        try:
            # This will raise NotAuthorized if user doesn't have permission
            toolkit.check_access('resource_update', {'user': toolkit.g.user}, {'id': resource_id})
        except toolkit.NotAuthorized:
            return jsonify({
                'success': False,
                'error': 'Not authorized to upload to this resource'
            }), 403
        
        # Initialize storage
        storage = ResourceCloudStorage({})
        
        # Check if Azure is configured
        if not storage.can_use_advanced_azure:
            return jsonify({
                'success': False,
                'error': 'Azure Blob Storage not properly configured'
            }), 400
        
        # Generate the blob path
        blob_path = storage.path_from_filename(resource_id, filename)
        
        # Generate SAS token with write permissions
        from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas
        
        svc_client = BlobServiceClient.from_connection_string(storage.connection_link)
        container_client = svc_client.get_container_client(storage.container_name)
        blob_client = container_client.get_blob_client(blob_path)
        
        # Set permissions for writing
        permissions = BlobSasPermissions(create=True, write=True)
        token_expires = datetime.utcnow() + timedelta(hours=2)
        
        sas_token = generate_blob_sas(
            account_name=blob_client.account_name,
            account_key=blob_client.credential.account_key,
            container_name=blob_client.container_name,
            blob_name=blob_client.blob_name,
            permission=permissions,
            expiry=token_expires
        )
        
        # Generate the full URL with SAS token
        upload_url = f"{blob_client.url}?{sas_token}"
        
        return jsonify({
            'success': True,
            'upload_url': upload_url,
            'blob_path': blob_path,
            'expires_at': token_expires.isoformat() + 'Z',
            'content_type': content_type
        })
        
    except Exception as e:
        log.error(f"Error generating Azure upload URL: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Internal error: {str(e)}'
        }), 500

