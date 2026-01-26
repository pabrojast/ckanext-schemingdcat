# encoding: utf-8
import ckan.model as model
import ckan.lib.base as base
import ckan.logic as logic
from flask import Blueprint, request, redirect, jsonify
from ckan.plugins.toolkit import render, g, h, _
import re

import ckanext.schemingdcat.utils as sdct_utils
import ckanext.schemingdcat.helpers as sdct_helpers
from ckanext.schemingdcat.rate_limiter import rate_limiter

from logging import getLogger

logger = getLogger(__name__)
get_action = logic.get_action

schemingdcat = Blueprint(u'schemingdcat', __name__)


def endpoints():
    return render(
        'schemingdcat/endpoints/index.html',
        extra_vars={
            u'endpoints': sdct_helpers.schemingdcat_get_catalog_endpoints(),
        })


def metadata_templates():
    return render(
        'schemingdcat/metadata_templates/index.html',
        extra_vars={
            u'metadata_templates': sdct_helpers.schemingdcat_get_catalog_endpoints(),
        })


schemingdcat.add_url_rule(
    "/endpoints/",
    view_func=endpoints,
    endpoint="endpoint_index",
    strict_slashes=False
)

schemingdcat.add_url_rule(
    "/metadata-templates/",
    view_func=metadata_templates,
    endpoint="metadata_templates",
    strict_slashes=False
)


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
    except (logic.NotFound, logic.NotAuthorized):
        return base.abort(
            404,
            _(u'Dataset {dataset_id} not found').format(dataset_id=id)
        )

    return render(
        'schemingdcat/custom_data/index.html',
        extra_vars={
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
    except (logic.NotFound, logic.NotAuthorized):
        return base.abort(
            404,
            _(u'Dataset {dataset_id} not found').format(dataset_id=id)
        )

    return render(
        'schemingdcat/custom_data/index.html',
        extra_vars={
            u'pkg_dict': pkg_dict,
            u'id': id,
            u'data_list': sdct_utils.get_geospatial_metadata(),
        })


@schemingdcat.route('/verify-captcha', methods=['POST'])
def verify_captcha():
    """Verify captcha answer and redirect back."""
    captcha_answer = request.form.get('captcha_answer', '')
    redirect_url = request.form.get(
        'redirect_url', h.url_for('dataset.search')
    )

    if rate_limiter.verify_captcha(captcha_answer):
        # Captcha verified successfully
        h.flash_success(
            _('Verification successful. You can continue searching.')
        )
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
    """Handle malformed snippet URLs with extra quotes or characters."""
    # Remove any trailing quotes or problematic characters
    clean_path = re.sub(r'["\'\s]+$', '', snippet_path)

    # Extract resource_id if present in query string
    resource_id = request.args.get('resource_id')

    # Check if we're looking for our specific template
    if clean_path == 'scd_api_info.html' or 'scd_api_info.html' in clean_path:
        logger.info(
            f"Handling potentially malformed snippet URL: {snippet_path}"
        )

        # Redirect to the proper URL format or render the template directly
        extra_vars = {'resource_id': resource_id} if resource_id else {}

        try:
            return render('ajax_snippets/scd_api_info.html', extra_vars=extra_vars)
        except Exception as e:
            logger.error(f"Error rendering scd_api_info template: {str(e)}")
            return base.abort(404, _('Template not found'))

    # For other templates, just pass through to the standard CKAN handler
    return base.abort(404, _('Template not found'))


@schemingdcat.route('/api/extract-spatial-extent', methods=['POST'])
def extract_spatial_extent():
    """API endpoint to extract spatial extent from uploaded geospatial files."""
    from ckanext.schemingdcat.upload.api import extract_spatial_extent_endpoint
    return extract_spatial_extent_endpoint()


@schemingdcat.route('/api/extract-spatial-extent-from-resource', methods=['POST'])
def extract_spatial_extent_from_resource():
    """API endpoint to extract spatial extent from uploaded resources."""
    from ckanext.schemingdcat.upload.api import extract_spatial_extent_from_resource_endpoint
    return extract_spatial_extent_from_resource_endpoint()


@schemingdcat.route('/api/get-azure-upload-url', methods=['POST'])
def get_azure_upload_url():
    """API endpoint to get Azure Blob Storage SAS URL for direct upload."""
    from ckanext.schemingdcat.upload.api import get_azure_upload_url_endpoint
    return get_azure_upload_url_endpoint()


@schemingdcat.route('/api/doi/resolve', methods=['POST'])
def resolve_doi_endpoint():
    """
    API endpoint to resolve DOI and fetch metadata.

    Expects JSON body with:
        - doi: The DOI to resolve (required)
        - providers: Optional list of providers to try

    Returns:
        JSON with metadata or error message
    """
    from ckanext.schemingdcat.lib.doi_resolver import resolve_doi, validate_doi, clean_doi

    try:
        data = request.get_json() or {}
        doi = data.get('doi', '').strip()
        providers = data.get('providers')

        if not doi:
            return jsonify({
                'success': False,
                'error': _('DOI is required')
            }), 400

        # Clean the DOI
        doi = clean_doi(doi)

        # Validate DOI format
        if not validate_doi(doi):
            return jsonify({
                'success': False,
                'error': _('Invalid DOI format. Expected format: 10.xxxx/xxxxx')
            }), 400

        # Resolve DOI
        result = resolve_doi(doi, providers=providers)

        if result:
            return jsonify({
                'success': True,
                'data': result
            })
        else:
            return jsonify({
                'success': False,
                'error': _('Could not resolve DOI. The DOI may not exist or the metadata service is unavailable.')
            }), 404

    except Exception as e:
        logger.error(f"Error resolving DOI: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@schemingdcat.route('/api/doi/validate', methods=['POST'])
def validate_doi_endpoint():
    """
    API endpoint to validate DOI format.

    Expects JSON body with:
        - doi: The DOI to validate (required)

    Returns:
        JSON with validation result
    """
    from ckanext.schemingdcat.lib.doi_resolver import validate_doi, clean_doi

    try:
        data = request.get_json() or {}
        doi = data.get('doi', '').strip()

        if not doi:
            return jsonify({
                'success': False,
                'valid': False,
                'error': _('DOI is required')
            }), 400

        cleaned_doi = clean_doi(doi)
        is_valid = validate_doi(cleaned_doi)

        return jsonify({
            'success': True,
            'valid': is_valid,
            'cleaned_doi': cleaned_doi if is_valid else None
        })

    except Exception as e:
        logger.error(f"Error validating DOI: {str(e)}")
        return jsonify({
            'success': False,
            'valid': False,
            'error': str(e)
        }), 500
