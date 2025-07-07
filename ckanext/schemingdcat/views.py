# encoding: utf-8
import ckan.plugins.toolkit as toolkit
from flask import Blueprint
from ckan.views.dataset import search as core_search
from ckanext.schemingdcat.rate_limiter import rate_limiter

import logging
log = logging.getLogger(__name__)

dataset_rate_limit = Blueprint('dataset_rate_limit', __name__)


def search(package_type='dataset'):
    """
    Override CKAN's dataset search to add rate limiting for unauthenticated users.
    """
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
    
    # Call the original search function
    return core_search(package_type)


# Register the overridden route with higher priority
def get_blueprints():
    return [dataset_rate_limit]


# Add route that overrides core CKAN search
dataset_rate_limit.add_url_rule('/dataset/', view_func=search, strict_slashes=False)
dataset_rate_limit.add_url_rule('/dataset', view_func=search, strict_slashes=False)