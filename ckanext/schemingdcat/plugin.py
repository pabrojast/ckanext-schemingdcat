from ckan.lib.plugins import DefaultTranslation
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

from ckanext.scheming.plugins import (
    SchemingDatasetsPlugin,
    SchemingGroupsPlugin,
    SchemingOrganizationsPlugin,
)
from ckanext.scheming import logic as scheming_logic

# Cloudstorage integration imports
from ckanext.cloudstorage import storage
from ckanext.cloudstorage import helpers as cloudstorage_helpers

import ckanext.schemingdcat.cli as cli
import ckanext.schemingdcat.config as sdct_config
from ckanext.schemingdcat.faceted import Faceted
from ckanext.schemingdcat.utils import init_config
from ckanext.schemingdcat.package_controller import PackageController
from ckanext.schemingdcat import helpers, validators, logic, blueprint, views

import logging

log = logging.getLogger(__name__)


class SchemingDCATPlugin(
    plugins.SingletonPlugin, Faceted, PackageController, DefaultTranslation
):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IFacets)
    plugins.implements(plugins.IPackageController)
    plugins.implements(plugins.ITranslation)
    plugins.implements(plugins.IValidators)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IClick)

    # IConfigurer
    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")

        # toolkit.add_resource('fanstatic',
        #                     'schemingdcat')

        toolkit.add_resource("assets", "ckanext-schemingdcat")

        sdct_config.default_locale = config_.get(
            "ckan.locale_default", sdct_config.default_locale
        )

        sdct_config.default_facet_operator = config_.get(
            "schemingdcat.default_facet_operator", sdct_config.default_facet_operator
        )

        sdct_config.icons_dir = config_.get(
            "schemingdcat.icons_dir", sdct_config.icons_dir
        )

        sdct_config.organization_custom_facets = toolkit.asbool(
            config_.get(
                "schemingdcat.organization_custom_facets",
                sdct_config.organization_custom_facets,
            )
        )

        sdct_config.group_custom_facets = toolkit.asbool(
            config_.get(
                "schemingdcat.group_custom_facets", sdct_config.group_custom_facets
            )
        )
        
        sdct_config.default_package_item_icon = config_.get(
                "schemingdcat.default_package_item_icon", sdct_config.default_package_item_icon
            ) or sdct_config.default_package_item_icon

        sdct_config.default_package_item_show_spatial = toolkit.asbool(
            config_.get(
                "schemingdcat.default_package_item_show_spatial", sdct_config.default_package_item_show_spatial
            )
        )

        sdct_config.show_metadata_templates_toolbar = toolkit.asbool(
            config_.get(
                "schemingdcat.show_metadata_templates_toolbar", sdct_config.show_metadata_templates_toolbar
            )
        )
        
        sdct_config.metadata_templates_search_identifier = config_.get(
                "schemingdcat.metadata_templates_search_identifier", sdct_config.metadata_templates_search_identifier
            ) or sdct_config.metadata_templates_search_identifier
        
        sdct_config.endpoints_yaml = config_.get(
            "schemingdcat.endpoints_yaml", sdct_config.endpoints_yaml
            ) or sdct_config.endpoints_yaml

        sdct_config.debug = toolkit.asbool(config_.get("debug", sdct_config.debug))

        # Default value use local ckan instance with /csw
        sdct_config.geometadata_base_uri = config_.get(
            "schemingdcat.geometadata_base_uri", "/csw"
        )

        # Load yamls config files
        init_config()

        # configure Faceted class (parent of this)
        self.facet_load_config(config_.get("schemingdcat.facet_list", "").split())

    def get_helpers(self):
        respuesta = dict(helpers.all_helpers)
        return respuesta

    def get_validators(self):
        return dict(validators.all_validators)

    # IBlueprint
    def get_blueprint(self):
        blueprints = [blueprint.schemingdcat]
        # Add rate limiting blueprint
        blueprints.extend(views.get_blueprints())
        return blueprints

    # IClick
    def get_commands(self):
        return cli.get_commands()

class SchemingDCATDatasetsPlugin(SchemingDatasetsPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IDatasetForm, inherit=True)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IValidators)
    # Add cloudstorage support
    plugins.implements(plugins.IUploader)
    plugins.implements(plugins.IResourceController, inherit=True)

    def update_config(self, config_):
        # Call parent update_config first
        super(SchemingDCATDatasetsPlugin, self).update_config(config_)
        
        # Note: cloudstorage assets are registered by the cloudstorage plugin
        # We don't need to register them here to avoid conflicts
        log.info("SchemingDCAT-CloudStorage integration configured")

    def read_template(self):
        return "schemingdcat/package/read.html"

    def resource_template(self):
        return "schemingdcat/package/resource_read.html"

    def package_form(self):
        return "schemingdcat/package/snippets/package_form.html"

    def resource_form(self):
        return "schemingdcat/package/snippets/resource_form.html"

    def get_helpers(self):
        # Merge schemingdcat helpers with cloudstorage helpers
        schemingdcat_helpers = super(SchemingDCATDatasetsPlugin, self).get_helpers()
        cloudstorage_helper_dict = {
            'cloudstorage_use_secure_urls': cloudstorage_helpers.use_secure_urls,
            'cloudstorage_use_azure_direct_upload': cloudstorage_helpers.use_azure_direct_upload,
            'cloudstorage_get_cloud_storage_type': cloudstorage_helpers.get_cloud_storage_type,
            'cloudstorage_use_enhanced_upload': cloudstorage_helpers.use_enhanced_upload
        }
        schemingdcat_helpers.update(cloudstorage_helper_dict)
        return schemingdcat_helpers

    # IUploader implementation - integrate cloudstorage
    def get_resource_uploader(self, data_dict):
        """Use cloudstorage ResourceCloudStorage for resource uploads"""
        return storage.ResourceCloudStorage(data_dict)

    def get_uploader(self, upload_to, old_filename=None):
        """For non-resource uploads, use default uploader"""
        return None

    def get_actions(self):
        # Only return schemingdcat-specific actions
        # cloudstorage actions are provided by the cloudstorage plugin
        return {
            "schemingdcat_dataset_schema_name": logic.schemingdcat_dataset_schema_name,
            "scheming_dataset_schema_list": scheming_logic.scheming_dataset_schema_list,
            "scheming_dataset_schema_show": scheming_logic.scheming_dataset_schema_show,
        }

    # IAuthFunctions - don't register cloudstorage auth functions to avoid conflicts
    def get_auth_functions(self):
        # cloudstorage auth functions are provided by the cloudstorage plugin
        # We don't need to register them here to avoid conflicts
        return {}

    # IResourceController - handle resource deletion
    def before_delete(self, context, resource, resources):
        """Handle cloudstorage file deletion when resource is deleted"""
        import os.path
        
        # Find the resource info in the resources list
        for res in resources:
            if res['id'] == resource['id']:
                break
        else:
            return
        
        # Ignore simple links (not uploaded files)
        if res['url_type'] != 'upload':
            return

        # Create a copy of resource dict and add clear_upload flag
        res_dict = res.copy()
        res_dict.update([('clear_upload', True)])

        uploader = self.get_resource_uploader(res_dict)

        # Check if container exists
        container = getattr(uploader, 'container', None)
        if container is None:
            return

        # Remove the file using uploader
        uploader.upload(resource['id'])

        # Remove all other files linked to this resource if configured
        if not uploader.leave_files:
            upload_path = os.path.dirname(
                uploader.path_from_filename(
                    resource['id'],
                    'fake-name'
                )
            )

            for old_file in uploader.container.iterate_objects():
                if old_file.name.startswith(upload_path):
                    old_file.delete()


class SchemingDCATGroupsPlugin(SchemingGroupsPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IGroupForm, inherit=True)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IValidators)

    def about_template(self):
        return "schemingdcat/group/about.html"


class SchemingDCATOrganizationsPlugin(SchemingOrganizationsPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IGroupForm, inherit=True)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IValidators)

    def about_template(self):
        return "schemingdcat/organization/about.html"
