import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

import ckanext.facet_scheming.helpers as helpers
import ckanext.facet_scheming.config as fs_config
from ckanext.facet_scheming.faceted import Faceted


import logging

logger = logging.getLogger(__name__)


class FacetSchemingPlugin(plugins.SingletonPlugin, Faceted):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IFacets)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic',
            'facet_scheming')
        toolkit.add_resource('assets','ckanext-facet_scheming')
        
        fs_config.default_facet_operator=config_.get('facet_scheming.default_facet_operator', fs_config.default_facet_operator)
        fs_config.icons_dir=config_.get('facet_scheming.icons_dir', fs_config.icons_dir)
        fs_config.default_locale=config_.get('ckan.locale_default', fs_config.default_locale)
        
        
        self.facet_load_config(config_.get('facet_scheming.facet_list', '').split())

    def get_helpers(self):
        respuesta=dict(helpers.all_helpers)
        return respuesta
