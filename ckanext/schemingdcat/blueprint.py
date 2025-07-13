# encoding: utf-8
import ckan.model as model
import ckan.lib.base as base
import ckan.logic as logic
from flask import Blueprint, request, redirect, url_for, jsonify
from ckan.logic import ValidationError
from ckan.plugins.toolkit import render, g, h, _
import tempfile
import os

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

@schemingdcat.route('/api/extract-spatial-extent', methods=['POST'])
def extract_spatial_extent():
    """Extract spatial extent from uploaded geospatial file."""
    try:
        logger.debug("Spatial extent extraction request received")
        
        # Check if file is in request
        if 'file' not in request.files:
            logger.debug("No file provided in request")
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            logger.debug("Empty filename provided")
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        logger.debug(f"Processing file: {file.filename}")
        
        # Check if it's a supported spatial file
        if not extent_extractor.can_extract_extent(file.filename):
            logger.debug(f"Unsupported file type for spatial extent extraction: {file.filename}")
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
                file.save(tmp_file.name)
                logger.debug(f"File saved to temporary location: {tmp_file.name}")
                
                # Extract spatial extent
                extent = extent_extractor.extract_extent(tmp_file.name)
                logger.debug(f"Extraction result: {extent}")
                
                if extent:
                    logger.debug("Spatial extent extraction successful")
                    return jsonify({
                        'success': True,
                        'extent': extent,
                        'message': 'Spatial extent extracted successfully'
                    })
                else:
                    logger.debug("Failed to extract spatial extent from file")
                    return jsonify({
                        'success': False,
                        'error': 'Failed to extract spatial extent from file'
                    }), 400
        finally:
            # Ensure cleanup even if extraction fails
            if tmp_file and os.path.exists(tmp_file.name):
                try:
                    os.unlink(tmp_file.name)
                except OSError:
                    pass  # Silent cleanup failure
                
    except Exception as e:
        logger.debug(f"Error extracting spatial extent: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error during spatial extent extraction'
        }), 500