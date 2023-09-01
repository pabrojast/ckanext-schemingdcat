import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

import ckanext.scheming_dcat.helpers as helpers
import ckanext.scheming_dcat.validators as validators
import ckanext.scheming_dcat.config as fs_config
from ckanext.scheming.plugins import SchemingDatasetsPlugin, SchemingGroupsPlugin, SchemingOrganizationsPlugin
from ckanext.scheming_dcat.faceted import Faceted
from ckanext.scheming_dcat.utils import init_config
from ckanext.scheming_dcat import blueprint
from ckanext.scheming_dcat.package_controller import PackageController
from ckan.lib.plugins import DefaultTranslation

import logging

log = logging.getLogger(__name__)


class FacetSchemingDcatPlugin(plugins.SingletonPlugin,
                           Faceted, 
                           PackageController, 
                           DefaultTranslation):

    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IFacets)
    plugins.implements(plugins.IPackageController)
    plugins.implements(plugins.ITranslation)
    plugins.implements(plugins.IValidators)
    plugins.implements(plugins.IBlueprint)


    # IConfigurer
    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')

        #toolkit.add_resource('fanstatic',
        #                     'scheming_dcat')

        toolkit.add_resource('assets',
                             'ckanext-scheming_dcat')

        fs_config.default_locale = config_.get('ckan.locale_default',
                                               fs_config.default_locale
                                               )

        fs_config.default_facet_operator = config_.get(
            'scheming_dcat.default_facet_operator',
            fs_config.default_facet_operator
            )

        fs_config.icons_dir = config_.get(
            'scheming_dcat.icons_dir',
            fs_config.icons_dir
            )

        fs_config.organization_custom_facets = toolkit.asbool(
            config_.get('scheming_dcat.organization_custom_facets',
                        fs_config.organization_custom_facets)
            )

        fs_config.group_custom_facets = toolkit.asbool(
            config_.get('scheming_dcat.group_custom_facets',
                        fs_config.group_custom_facets
                        )
            )
        
        fs_config.debug = toolkit.asbool(
            config_.get('debug',
                        fs_config.debug
                        )
            )

        fs_config.geometadata_base_uri = config_.get(
            'scheming_dcat.geometadata_base_uri',
            None
            )

        # Load yamls config files, if not in debug mode
        if not fs_config.debug:
            init_config()

        # configure Faceted class (parent of this)
        self.facet_load_config(config_.get(
            'scheming_dcat.facet_list',
            '').split())
        
        
    def get_helpers(self):
        respuesta = dict(helpers.all_helpers)
        return respuesta
    
    def get_validators(self):
        return dict(validators.all_validators)

    #IBlueprint
    def get_blueprint(self):
        return blueprint.schemingdct


class SchemingDcatDatasetsPlugin(SchemingDatasetsPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IDatasetForm, inherit=True)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IValidators)

    def read_template(self):
        return 'scheming_dcat/package/read.html'
    
    def resource_template(self):
        return 'scheming_dcat/package/resource_read.html'

class SchemingDcatGroupsPlugin(SchemingGroupsPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IGroupForm, inherit=True)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IValidators)

    def about_template(self):
        return 'scheming_dcat/group/about.html'

class SchemingDcatOrganizationsPlugin(SchemingOrganizationsPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IGroupForm, inherit=True)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IValidators)
    
    def about_template(self):
        return 'scheming_dcat/organization/about.html'

    