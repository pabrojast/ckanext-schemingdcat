# encoding: utf-8
import ckan.model as model
import ckan.lib.base as base
import ckan.logic as logic
from flask import Blueprint, request, redirect, url_for
from ckan.logic import ValidationError
from ckan.plugins.toolkit import render, g, h, _

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