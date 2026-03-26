# encoding: utf-8
import ckan.plugins.toolkit as toolkit
from ckan.common import config, request
from flask import Blueprint, redirect
from ckan.views.dataset import search as core_search
from ckanext.schemingdcat.rate_limiter import rate_limiter
from urllib.parse import urlencode

import logging
log = logging.getLogger(__name__)

dataset_rate_limit = Blueprint('dataset_rate_limit', __name__)


def _legacy_type_redirect(package_type='dataset'):
    """
    Redirect legacy /dataset/?type=<custom_type> searches to the dedicated
    package-type route so dataset and document catalogs stay separated.
    """
    if package_type != 'dataset':
        return None

    requested_type = request.args.get('type')
    if not requested_type or requested_type == 'dataset':
        return None

    try:
        target_url = toolkit.h.url_for('{0}.search'.format(requested_type))
    except Exception:
        return None

    params = [(key, value) for key, value in request.args.items(multi=True)
              if key != 'type']
    if params:
        target_url = '{0}?{1}'.format(target_url, urlencode(params, doseq=True))

    return redirect(target_url)


def _search_dataset_only(package_type='dataset'):
    """
    Force /dataset to keep CKAN's dataset-only filtering even if another
    runtime setting enables multi-type searches on the dataset catalog.
    """
    if package_type != 'dataset':
        return core_search(package_type)

    config_key = 'ckan.search.show_all_types'
    had_previous_value = config_key in config
    previous_value = config.get(config_key)

    try:
        config[config_key] = 'false'
        return core_search(package_type)
    finally:
        if had_previous_value:
            config[config_key] = previous_value
        else:
            try:
                del config[config_key]
            except KeyError:
                pass


def search(package_type='dataset'):
    """
    Override CKAN's dataset search to add rate limiting for unauthenticated users.
    """
    legacy_redirect = _legacy_type_redirect(package_type)
    if legacy_redirect is not None:
        return legacy_redirect

    # Check if user is authenticated
    if not toolkit.g.userobj:
        # Track the search request
        tracking = rate_limiter.track_search()
        
        # Check if rate limited
        if rate_limiter.is_rate_limited():
            # Generate captcha if needed
            captcha_question = None
            if rate_limiter.needs_captcha():
                captcha_question = rate_limiter.generate_captcha()
            
            return toolkit.render('schemingdcat/rate_limited.html', extra_vars={
                'needs_captcha': rate_limiter.needs_captcha(),
                'captcha_question': captcha_question,
                'captcha_error': False,
                'search_limit': rate_limiter.search_limit,
                'time_window': rate_limiter.time_window,
                'captcha_after': rate_limiter.captcha_required_after
            })
        
        # Log remaining searches before captcha
        remaining = rate_limiter.get_remaining_searches()
        if remaining <= 3 and remaining > 0:
            toolkit.h.flash_notice(
                toolkit._('You have %(remaining)d searches remaining before verification is required.') % 
                {'remaining': remaining}
            )
    
    return _search_dataset_only(package_type)


# Register the overridden route with higher priority
def get_blueprints():
    return [dataset_rate_limit]


# Add route that overrides core CKAN search
dataset_rate_limit.add_url_rule('/dataset/', view_func=search, strict_slashes=False)
dataset_rate_limit.add_url_rule('/dataset', view_func=search, strict_slashes=False)
