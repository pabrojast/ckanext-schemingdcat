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
            'error': f'Internal error: {str(e)}',
            'extent': None
        }), 500

