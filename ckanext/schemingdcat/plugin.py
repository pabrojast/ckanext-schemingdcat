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
import os

import logging
import json
import sys

log = logging.getLogger(__name__)

# Debug: Print when module is imported (to diagnose RQ worker issues)
print(f"[SCHEMINGDCAT PLUGIN] Module imported successfully", file=sys.stderr)
sys.stderr.flush()

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
    plugins.implements(plugins.IPackageController, inherit=True)

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
    plugins.implements(plugins.IPackageController, inherit=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        log.info("🚀 [PLUGIN INIT] SchemingDCATDatasetsPlugin initialized with IResourceController")
        log.info("🚀 [PLUGIN INIT] Spatial extent extraction will be processed after resource creation/update")
        # Debug print to stderr for worker visibility
        import sys
        print(f"[PLUGIN INIT] SchemingDCATDatasetsPlugin.__init__ called", file=sys.stderr)
        sys.stderr.flush()

    def update_config(self, config_):
        # Call parent update_config first
        super().update_config(config_)
        
        # Add custom CSS for cloudstorage integration
        toolkit.add_public_directory(config_, 'public')
        
        # Note: cloudstorage assets are registered by the cloudstorage plugin
        # We don't need to register them here to avoid conflicts
        log.info("SchemingDCAT-CloudStorage integration configured with enhanced UI")

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
        schemingdcat_helpers = super().get_helpers()
        cloudstorage_helper_dict = {
            'cloudstorage_use_secure_urls': cloudstorage_helpers.use_secure_urls,
            'cloudstorage_use_azure_direct_upload': cloudstorage_helpers.use_azure_direct_upload,
            'cloudstorage_get_cloud_storage_type': cloudstorage_helpers.get_cloud_storage_type,
            'cloudstorage_use_enhanced_upload': cloudstorage_helpers.use_enhanced_upload,
            'localised_filesize': helpers.safe_localised_filesize
        }
        schemingdcat_helpers.update(cloudstorage_helper_dict)
        return schemingdcat_helpers

    # IUploader implementation - integrate cloudstorage
    def get_resource_uploader(self, data_dict):
        """Use cloudstorage ResourceCloudStorage for resource uploads"""
        # Pass Azure info to the uploader if present
        uploader = storage.ResourceCloudStorage(data_dict)
        
        # If this is an Azure direct upload, pass the info to the uploader
        if data_dict.get('azure_upload') == 'true' or data_dict.get('_azure_pending'):
            # Set resource dict so uploader knows this is Azure direct upload
            uploader.resource = data_dict
            log.info(f"🔷 [UPLOADER] Configured for Azure direct upload")
        
        return uploader

    # --- Package lifecycle helpers: ensure member-state/initiative groups are captured ---
    def _ensure_memberstate_groups(self, context, data_dict):
        """
        Make sure selected member states (via group multiselect or spatial_uri)
        end up in the dataset's groups list before create/update.
        """
        try:
            from ckanext.schemingdcat import helpers as sd_helpers
        except Exception:
            return data_dict

        # Log all keys to understand what's coming in
        all_keys = [str(k) for k in data_dict.keys()]
        log.debug(f"[_ensure_memberstate_groups] all data_dict keys: {all_keys}")

        group_names = []

        existing_groups = data_dict.get('groups') or []
        log.debug(f"[_ensure_memberstate_groups] existing_groups from data_dict: {existing_groups}")
        log.debug(f"[_ensure_memberstate_groups] existing_groups type: {type(existing_groups)}")
        if isinstance(existing_groups, dict):
            existing_groups = [existing_groups]
        for g in existing_groups:
            log.debug(f"[_ensure_memberstate_groups] processing group: {g} (type: {type(g)})")
            if not isinstance(g, dict):
                continue
            name = g.get('name') or g.get('id')
            log.debug(f"[_ensure_memberstate_groups] extracted name/id: {name}")
            if name:
                group_names.append(name)

        log.debug(f"[_ensure_memberstate_groups] group_names after existing_groups: {group_names}")

        for key, value in list(data_dict.items()):
            key_name = key
            if isinstance(key, tuple) and key:
                key_name = key[-1]
            if isinstance(key_name, str) and key_name.startswith('groups__') and key_name.endswith('__id'):
                log.debug(f"[_ensure_memberstate_groups] found groups__ key: {key_name} = {value}")
                if value:
                    group_names.append(value)

        log.debug(f"[_ensure_memberstate_groups] group_names after groups__X__id: {group_names}")

        spatial_val = data_dict.get('spatial_uri')
        spatial_list = []
        if spatial_val:
            if isinstance(spatial_val, str):
                try:
                    parsed = json.loads(spatial_val)
                    spatial_list = parsed if isinstance(parsed, list) else [parsed]
                except Exception:
                    spatial_list = [spatial_val]
            elif isinstance(spatial_val, list):
                spatial_list = spatial_val
            else:
                spatial_list = [spatial_val]

        for uri in spatial_list:
            if not uri:
                continue
            try:
                group_slug = sd_helpers.schemingdcat_find_member_state_group(uri, context)
                if group_slug:
                    group_names.append(group_slug)
            except Exception as e:
                log.debug(f"Could not resolve member state group for {uri}: {e}")

        seen = set()
        unique_group_names = []
        for name in group_names:
            if not name or name in seen:
                continue
            seen.add(name)
            unique_group_names.append(name)

        log.debug(f"[_ensure_memberstate_groups] unique_group_names final: {unique_group_names}")

        if unique_group_names:
            data_dict['groups'] = [{'name': n} for n in unique_group_names]
            log.debug(f"[_ensure_memberstate_groups] set data_dict['groups'] to: {data_dict['groups']}")

        return data_dict

    def before_dataset_create(self, context, data_dict):
        log.info("[SchemingDCATPlugin.before_dataset_create] CALLED")
        return self._ensure_memberstate_groups(context, data_dict)

    def before_dataset_update(self, context, data_dict):
        log.info("[SchemingDCATPlugin.before_dataset_update] CALLED")
        return self._ensure_memberstate_groups(context, data_dict)

    def get_uploader(self, upload_to, old_filename=None):
        """Fallback to CKAN's default uploader for non-resource uploads.

        CKAN 2.10 calls this method for user/group images or other assets.
        Returning None keeps the core uploader behaviour while our custom
        resource uploader continues to handle dataset resources.
        This is consistent with cloudstorage plugin behavior.
        """
        return None

    def get_actions(self):
        # Only return schemingdcat-specific actions
        # cloudstorage actions are provided by the cloudstorage plugin
        actions = {
            "schemingdcat_dataset_schema_name": logic.schemingdcat_dataset_schema_name,
            "scheming_dataset_schema_list": scheming_logic.scheming_dataset_schema_list,
            "scheming_dataset_schema_show": scheming_logic.scheming_dataset_schema_show,
        }
        # Wrap resource_create/resource_update to ensure metadata extraction is triggered even if IResourceController hooks are skipped
        actions.update({
            "resource_create": self.resource_create,
            "resource_update": self.resource_update,
            "package_patch": self.package_patch,
        })
        return actions

    @toolkit.chained_action
    def resource_create(self, next_action, context, data_dict):
        """
        Chained action to ensure metadata extraction triggers even if IResourceController is skipped.
        """
        result = next_action(context, data_dict)
        # Skip if this is a metadata job update (prevent infinite loop)
        if context.get('_schemingdcat_metadata_job'):
            log.debug(f"⏭️ [ACTION] Skipping extraction trigger - metadata job context")
            return result
        try:
            self._trigger_metadata_extraction(result)
        except Exception as e:
            log.warning(f"⚠️ [ACTION] Could not trigger metadata extraction after resource_create: {e}")
        return result

    @toolkit.chained_action
    def resource_update(self, next_action, context, data_dict):
        """
        Chained action for updates; triggers extraction if a new upload/format warrants it.
        """
        result = next_action(context, data_dict)
        # Skip if this is a metadata job update (prevent infinite loop)
        if context.get('_schemingdcat_metadata_job'):
            log.debug(f"⏭️ [ACTION] Skipping extraction trigger - metadata job context")
            return result
        try:
            self._trigger_metadata_extraction(result)
        except Exception as e:
            log.warning(f"⚠️ [ACTION] Could not trigger metadata extraction after resource_update: {e}")
        return result

    @toolkit.chained_action
    def package_patch(self, next_action, context, data_dict):
        """
        Chained action for package_patch to ensure groups are processed correctly
        in multi-page forms.
        """
        log.info(f"[SchemingDCATPlugin.package_patch] CALLED with keys: {list(data_dict.keys())}")
        
        # Process groups__X__id fields before the patch
        data_dict = self._ensure_memberstate_groups(context, data_dict)
        
        return next_action(context, data_dict)

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

    def _cleanup_empty_metadata_fields(self, context, resource):
        """
        Clean up any metadata fields that contain empty lists or meaningless values.
        This prevents showing ['', '', ''] in the UI for fields that haven't been populated.
        
        Args:
            context: The CKAN context
            resource: The resource dictionary
        """
        try:
            resource_id = resource.get('id')
            if not resource_id:
                return
                
            # List of metadata fields that can get empty lists
            metadata_fields_to_check = [
                'data_fields', 'data_statistics', 'data_domains',
                'geographic_coverage', 'administrative_boundaries',
                'compression_info', 'format_version', 'file_integrity',
                'content_type_detected', 'document_pages', 'spreadsheet_sheets', 'text_content_info'
            ]
            
            # Check if any of these fields have meaningless values
            fields_to_clear = {}
            for field_name in metadata_fields_to_check:
                field_value = resource.get(field_name)
                
                if field_value is not None:
                    # Check for empty lists or lists with only empty strings
                    if isinstance(field_value, list):
                        # Filter out empty/meaningless values
                        filtered_list = []
                        for item in field_value:
                            if item is not None:
                                item_str = str(item).strip()
                                if item_str and item_str not in ['', 'None', 'null', 'undefined', '0', '-', 'N/A', 'n/a']:
                                    filtered_list.append(item_str)
                        
                        # If list is empty after filtering, mark for clearing
                        if not filtered_list:
                            fields_to_clear[field_name] = None
                    
                    # Check for empty strings or meaningless string values
                    elif isinstance(field_value, str):
                        field_str = field_value.strip()
                        if not field_str or field_str in ['', 'None', 'null', 'undefined', '0', '-', 'N/A', 'n/a']:
                            fields_to_clear[field_name] = None
            
            # If we found fields to clear, update the resource
            if fields_to_clear:
                log.debug(f"Cleaning up empty metadata fields for resource {resource_id}: {list(fields_to_clear.keys())}")
                
                # Create system context for the update
                system_context = {
                    'model': context['model'],
                    'session': context['session'],
                    'ignore_auth': True,
                    'user': '',  # System user
                    'api_version': 3,
                    'defer_commit': False
                }
                
                # Prepare patch data
                patch_data = {'id': resource_id}
                patch_data.update(fields_to_clear)
                
                # Update the resource to clear empty fields
                toolkit.get_action('resource_patch')(system_context, patch_data)
                
                log.debug(f"Successfully cleaned up {len(fields_to_clear)} empty metadata fields for resource {resource_id}")
            
        except Exception as e:
            log.warning(f"Error cleaning up empty metadata fields for resource {resource.get('id', 'unknown')}: {str(e)}")
            # Don't raise exception - this is cleanup, not critical

    def before_create(self, context, resource):
        """
        Hook que se ejecuta ANTES de crear un recurso.
        Simplified to avoid conflicts with cloudstorage.
        """
        # Let cloudstorage handle Azure uploads entirely
        # We only need to mark resources for post-processing
        
        # Check if this is an upload (not a link)
        if resource.get('upload') or resource.get('url_type') == 'upload':
            # Mark for metadata extraction after creation
            resource['_needs_metadata_extraction'] = True
            log.info(f"📝 [BEFORE CREATE] Resource marked for metadata extraction")
        else:
            # Also mark if the declared format/URL looks like a spatial or document we can parse
            if self._should_extract_metadata(resource):
                resource['_needs_metadata_extraction'] = True
                log.info(f"📝 [BEFORE CREATE] Resource marked for metadata extraction based on format/URL")
        
        return resource

    # IResourceController - handle spatial extent extraction for spatial resources
    def after_create(self, context, resource):
        """
        Hook que se ejecuta después de crear un recurso.

        CRITICAL: This hook MUST RETURN IMMEDIATELY without blocking!
        All background processing is done via job queue.
        """
        resource_id = resource.get('id', 'unknown')
        
        # Skip if this is a metadata job update (prevent infinite loop)
        if context.get('_schemingdcat_metadata_job'):
            log.debug(f"⏭️ [HOOK] Skipping after_create - metadata job context")
            return resource
            
        log.info(f"🔥 [HOOK] after_create called for resource: {resource_id}")

        self._trigger_metadata_extraction(resource)

        # RETURN IMMEDIATELY - don't wait for jobs
        return resource

    def _trigger_metadata_extraction(self, resource):
        """
        Centralized trigger for metadata extraction that can be called from hooks or chained actions.
        
        Note: RQ background worker in CKAN 2.10 has known issues with job execution.
        We use threading-based extraction directly which is more reliable.
        """
        resource_id = resource.get('id', 'unknown')
        needs_extraction = resource.get('_needs_metadata_extraction') or self._should_extract_metadata(resource)

        if not needs_extraction:
            log.info(f"⏭️ [TRIGGER] Resource {resource_id} doesn't need metadata extraction")
            return

        # Use threading-based extraction directly (more reliable than RQ in CKAN 2.10)
        # RQ worker has known issues where jobs complete without executing the function
        log.info(f"🚀 [TRIGGER] Starting metadata extraction for resource {resource_id}")
        self._fallback_metadata_extraction(resource)

    def _start_job_watchdog(self, job, resource, delay_seconds=60):
        """
        If the job stays queued (no worker), trigger fallback extraction after a delay.
        This avoids uploads appearing stuck when no job workers are running.
        """
        try:
            import threading
            import time
            from ckan.lib import jobs

            def watcher():
                try:
                    time.sleep(delay_seconds)
                    # Re-fetch job state
                    j = jobs.get(job.id) if job else None
                    state = getattr(j, 'state', None) or getattr(j, 'status', None)
                    if state in (None, 'queued', 'failed'):
                        log.warning(f"⏱️ [WATCHDOG] Metadata job {job.id if job else 'unknown'} still {state or 'unknown'} after {delay_seconds}s. Running fallback.")
                        self._fallback_metadata_extraction(resource)
                    else:
                        log.info(f"⏱️ [WATCHDOG] Metadata job {job.id} state={state}, no fallback needed.")
                except Exception as e:
                    log.debug(f"Watchdog could not check job status: {e}")

            t = threading.Thread(target=watcher, name=f"metadata-watchdog-{resource.get('id', 'unknown')[:8]}", daemon=True)
            t.start()
        except Exception as e:
            log.debug(f"Could not start job watchdog: {e}")

    def _should_extract_metadata(self, resource):
        """
        Heuristic to decide if a resource likely needs metadata extraction.
        This avoids relying solely on transient flags that are lost after creation.
        """
        url_type = (resource.get('url_type') or '').lower()
        if url_type == 'upload':
            return True

        fmt = (resource.get('format') or '').lower()
        url = resource.get('url') or ''
        url_ext = ''
        if url:
            clean_url = url.split('?')[0].split('#')[0]
            url_ext = os.path.splitext(clean_url)[1].lower().lstrip('.')

        candidate_formats = {
            'zip', 'shp', 'tif', 'tiff', 'geotiff', 'kml', 'geojson', 'json',
            'gpkg', 'csv', 'xls', 'xlsx', 'pdf'
        }

        if fmt in candidate_formats:
            return True
        if url_ext in candidate_formats:
            return True

        return False

    def _fallback_metadata_extraction(self, resource):
        """Fallback metadata extraction using threading when job queue is not available."""
        import threading
        
        def extract_async():
            try:
                metadata_data = {
                    'resource_id': resource.get('id'),
                    'resource_url': resource.get('url'),
                    'resource_format': resource.get('format'),
                    'package_id': resource.get('package_id'),
                }
                extract_comprehensive_metadata_job(metadata_data)
            except Exception as e:
                log.error(f"Error in fallback metadata extraction: {e}", exc_info=True)
        
        thread = threading.Thread(
            target=extract_async,
            name=f"metadata-{resource.get('id', 'unknown')[:8]}",
            daemon=True
        )
        thread.start()
        log.info(f"Started fallback threading for metadata extraction")

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


# Import job functions from dedicated module for backward compatibility
# These imports allow existing code that imports from plugin.py to continue working
from ckanext.schemingdcat.jobs import (
    extract_comprehensive_metadata_job,
    extract_spatial_extent_job,
    test_simple_job
)
