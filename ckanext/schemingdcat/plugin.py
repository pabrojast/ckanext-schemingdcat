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
import json

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        log.info("🚀 [PLUGIN INIT] SchemingDCATDatasetsPlugin initialized with IResourceController")
        log.info("🚀 [PLUGIN INIT] Spatial extent extraction will be processed after resource creation/update")

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
        
        return resource

    # IResourceController - handle spatial extent extraction for spatial resources
    def after_create(self, context, resource):
        """
        Hook que se ejecuta después de crear un recurso.

        CRITICAL: This hook MUST RETURN IMMEDIATELY without blocking!
        All background processing is done via job queue.
        """
        resource_id = resource.get('id', 'unknown')
        log.info(f"🔥 [HOOK] after_create called for resource: {resource_id}")

        # Skip if not marked for extraction
        if not resource.get('_needs_metadata_extraction'):
            log.info(f"⏭️ [HOOK] Resource {resource_id} doesn't need metadata extraction")
            return resource

        # Check if job queue is available
        try:
            from ckan.lib import jobs
            job_queue_available = True
        except ImportError:
            job_queue_available = False
            log.warning("Job queue not available, using threading fallback")

        if job_queue_available:
            # Queue metadata extraction job
            try:
                metadata_job_data = {
                    'resource_id': resource.get('id'),
                    'resource_url': resource.get('url'),
                    'resource_format': resource.get('format'),
                    'package_id': resource.get('package_id'),
                }
                jobs.enqueue(
                    extract_comprehensive_metadata_job,
                    [metadata_job_data],
                    title=f"Extract metadata for resource {resource_id[:8]}",
                    queue='default'
                )
                log.info(f"✅ [HOOK] Queued metadata extraction job for resource {resource_id}")

            except Exception as queue_error:
                log.error(f"⚠️ [HOOK] Could not queue job: {queue_error}")
                # Fall back to threading
                self._fallback_metadata_extraction(resource)
        else:
            # Use threading fallback
            self._fallback_metadata_extraction(resource)

        # RETURN IMMEDIATELY - don't wait for jobs
        return resource

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


def extract_comprehensive_metadata_job(job_data):
    """
    Job function para extraer metadata comprensiva en segundo plano usando CKAN Jobs Queue.
    
    Función que extrae toda la información disponible de archivos (espacial y no espacial).
    
    Args:
        job_data: Diccionario con resource_id, resource_url, resource_format, package_id
    """
    import json
    import logging
    import tempfile
    import urllib.request
    import os
    import sys
    
    # Configure logging for the worker with more detail
    log = logging.getLogger(__name__)
    log.info(f"========= STARTING COMPREHENSIVE METADATA JOB =========")
    log.info(f"Job data received: {job_data}")
    log.info(f"Python version: {sys.version}")
    log.info(f"Working directory: {os.getcwd()}")
    
    try:
        # Get job data with validation
        if not isinstance(job_data, dict):
            log.error(f"Invalid job_data type: {type(job_data)}, expected dict")
            return False
            
        resource_id = job_data.get('resource_id')
        resource_url = job_data.get('resource_url')
        resource_format = job_data.get('resource_format')
        package_id = job_data.get('package_id')
        skip_spatial = bool(job_data.get('skip_spatial'))
        
        if not resource_id:
            log.error("No resource_id in job_data")
            return False
            
        log.info(f"Processing comprehensive metadata job for resource {resource_id}")
        log.info(f"Resource URL: {resource_url}")
        log.info(f"Resource format: {resource_format}")
        log.info(f"Package ID: {package_id}")
        
        # CKAN imports inside try block to handle import errors
        try:
            import ckan.model as model
            import ckan.plugins.toolkit as toolkit
            from ckan.logic import get_action
            import traceback
            # Import scheming logic functions to ensure they're registered
            from ckanext.scheming import logic as scheming_logic
            
            # Ensure scheming actions are available in the worker context
            # This is necessary because workers don't automatically load all plugin actions
            import ckan.plugins as p
            scheming_plugins = [
                'scheming_datasets',
                'scheming_groups', 
                'scheming_organizations'
            ]
            
            for plugin_name in scheming_plugins:
                try:
                    plugin = p.get_plugin(plugin_name)
                    if hasattr(plugin, 'get_actions'):
                        actions = plugin.get_actions()
                        for action_name, action_func in actions.items():
                            if action_name not in toolkit._actions:
                                toolkit._actions[action_name] = action_func
                                log.info(f"Registered action {action_name} from {plugin_name}")
                except Exception as plugin_error:
                    log.warning(f"Could not load actions from {plugin_name}: {plugin_error}")
            
            log.info("CKAN modules imported successfully")
        except ImportError as e:
            log.error(f"Could not import CKAN modules: {e}")
            return False
        
        # Import analyzer
        try:
            from ckanext.schemingdcat.spatial_extent import FileAnalyzer
            log.info("FileAnalyzer imported successfully")
        except ImportError as e:
            log.error(f"Could not import FileAnalyzer: {e}")
            return False
        
        # Analyze file comprehensively
        metadata = {}
        
        try:
            analyzer = FileAnalyzer()
            log.info(f"FileAnalyzer created successfully for resource {resource_id}")
            
            # Check if file is local or remote
            if resource_url and (resource_url.startswith('/') or '://' not in resource_url):
                # Local file
                log.info(f"Analyzing local file: {resource_url}")
                
                # Check if file exists
                if os.path.exists(resource_url):
                    log.info(f"Local file exists, analyzing: {resource_url}")
                    metadata = analyzer.analyze_file(resource_url, trust_extension=True)
                    log.info(f"Local file analysis completed, extracted {len(metadata)} metadata fields")
                else:
                    log.warning(f"Local file does not exist: {resource_url}")
                    metadata = {}
                    
            else:
                # Remote file - download temporarily for analysis
                log.info(f"Analyzing remote file: {resource_url}")
                metadata = {}
                
                if resource_url:
                    ext = resource_format.lower() if resource_format else 'unknown'
                    suffix = f".{ext}" if ext and ext != 'unknown' else ""
                    
                    log.info(f"Creating temporary file with suffix: {suffix}")
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                        try:
                            # Download file with proper headers
                            req = urllib.request.Request(resource_url)
                            req.add_header('User-Agent', 'CKAN-SchemingDCAT-FileAnalyzer/1.0')
                            
                            log.info(f"Starting download from: {resource_url}")
                            
                            import time
                            max_attempts = 3
                            backoff = 2
                            last_error = None

                            for attempt in range(1, max_attempts + 1):
                                try:
                                    with urllib.request.urlopen(req, timeout=45) as response:
                                        log.info(f"Download response received, content-type: {response.headers.get('Content-Type', 'unknown')}")
                                        
                                        chunk_size = 8192
                                        total_size = 0
                                        while True:
                                            chunk = response.read(chunk_size)
                                            if not chunk:
                                                break
                                            tmp_file.write(chunk)
                                            total_size += len(chunk)
                                            # Limit file size to 100MB
                                            if total_size > 100 * 1024 * 1024:
                                                log.warning("File too large (>100MB), aborting download")
                                                raise Exception("File too large (>100MB)")
                                        
                                        tmp_file.flush()
                                        
                                        if total_size > 0:
                                            log.info(f"Downloaded {total_size} bytes to {tmp_file.name}, starting analysis...")
                                            # Analyze downloaded file
                                            metadata = analyzer.analyze_file(tmp_file.name, trust_extension=True)
                                            # If spatial is explicitly skipped, post-filter spatial keys
                                            if skip_spatial and isinstance(metadata, dict):
                                                for k in ['spatial_extent','spatial_crs','spatial_resolution','feature_count','geometry_type','geographic_coverage','administrative_boundaries']:
                                                    metadata.pop(k, None)
                                            log.info(f"Remote file analysis completed, extracted {len(metadata)} metadata fields")
                                        else:
                                            log.warning(f"Downloaded file is empty")
                                        last_error = None
                                        break
                                except urllib.error.URLError as e:
                                    last_error = e
                                    log.warning(f"Download attempt {attempt}/{max_attempts} failed: {e}")
                                except Exception as e:
                                    last_error = e
                                    log.warning(f"Download attempt {attempt}/{max_attempts} failed: {e}")
                                
                                if attempt < max_attempts:
                                    time.sleep(backoff)
                                    backoff *= 2

                            if last_error is not None:
                                log.error(f"All download attempts failed: {last_error}")
                            
                        except urllib.error.URLError as e:
                            log.error(f"URL error downloading file: {e}")
                        except Exception as e:
                            log.error(f"Error downloading file for analysis: {e}")
                        finally:
                            # Clean up temporary file
                            try:
                                if os.path.exists(tmp_file.name):
                                    os.unlink(tmp_file.name)
                                    log.debug(f"Cleaned up temporary file: {tmp_file.name}")
                            except Exception as cleanup_error:
                                log.warning(f"Could not clean up temporary file {tmp_file.name}: {cleanup_error}")
                else:
                    log.warning("No resource URL provided for analysis")
                
        except Exception as e:
            log.error(f"Error extracting comprehensive metadata: {e}", exc_info=True)
            return False
        
        if metadata:
            log.info(f"Successfully extracted comprehensive metadata from resource {resource_id} in job")
            log.info(f"Metadata fields extracted: {list(metadata.keys())}")
            
            # Debug: Log raw metadata to understand what's being extracted
            log.debug(f"Raw metadata extracted: {json.dumps(metadata, indent=2, default=str)}")
            
            try:
                # Ensure we have a valid database session and close any existing one
                try:
                    model.Session.close()
                except:
                    pass
                
                # Create fresh system context for updating the resource with proper setup
                # Use a site user to bypass authorization issues with private datasets
                try:
                    site_user = toolkit.get_action('get_site_user')({'ignore_auth': True}, {})
                    user_name = site_user['name']
                    log.info(f"Using site user '{user_name}' for resource update")
                except Exception as e:
                    log.warning(f"Could not get site user: {e}, using default system user")
                    user_name = 'default'
                
                context = {
                    'model': model,
                    'session': model.Session,
                    'ignore_auth': True,
                    'user': user_name,  # Use site user to handle private datasets
                    'auth_user_obj': None,
                    'api_version': 3,
                    'defer_commit': False,
                    'for_view': False,  # This is not for rendering
                    'return_id_only': False,  # We want the full object back
                    'bypass_auth': True,  # Additional flag for some auth checks
                    '__auth_audit': []  # Prevent auth audit logging
                }
                
                log.info(f"Created system context for resource update")
                
                # Prepare data for updating with all extracted metadata
                resource_patch_data = {'id': resource_id}
                
                # Add all fields that have valid values
                metadata_fields = {
                    'spatial_extent': metadata.get('spatial_extent'),
                    'spatial_crs': metadata.get('spatial_crs'),
                    'spatial_resolution': metadata.get('spatial_resolution'),
                    'feature_count': metadata.get('feature_count'),
                    'geometry_type': metadata.get('geometry_type'),
                    'data_fields': metadata.get('data_fields'),
                    'data_statistics': metadata.get('data_statistics'),
                    'data_domains': metadata.get('data_domains'),
                    'geographic_coverage': metadata.get('geographic_coverage'),
                    'administrative_boundaries': metadata.get('administrative_boundaries'),
                    'file_created_date': metadata.get('file_created_date'),
                    'file_modified_date': metadata.get('file_modified_date'),
                    'data_temporal_coverage': metadata.get('data_temporal_coverage'),
                    'file_size_bytes': metadata.get('file_size_bytes'),
                    'compression_info': metadata.get('compression_info'),
                    'format_version': metadata.get('format_version'),
                    'file_integrity': metadata.get('file_integrity'),
                    'content_type_detected': metadata.get('content_type_detected'),
                    'document_pages': metadata.get('document_pages'),
                    'spreadsheet_sheets': metadata.get('spreadsheet_sheets'),
                    'text_content_info': metadata.get('text_content_info')
                }
                
                # Only add fields that have meaningful values
                fields_to_update = []
                for field_name, field_value in metadata_fields.items():
                    # Skip None values completely
                    if field_value is None:
                        continue
                        
                    # Skip empty strings
                    if field_value == '':
                        continue
                        
                    # Handle lists more rigorously - only include lists with meaningful content
                    if isinstance(field_value, list):
                        # Filter empty/meaningless values from the list
                        filtered_list = []
                        for item in field_value:
                            if item is not None:
                                # Convert to string and clean whitespace
                                item_str = str(item).strip()
                                # Only add if not empty and not meaningless values
                                if item_str and item_str not in ['', 'None', 'null', 'undefined', '0', '-', 'N/A', 'n/a']:
                                    filtered_list.append(item_str)
                        
                        # Only add the list if it has at least one meaningful item
                        if filtered_list:
                            # Convert list to JSON string for fields that expect JSON format
                            json_fields = ['data_fields', 'data_statistics', 'data_domains', 
                                         'geographic_coverage', 'administrative_boundaries',
                                         'compression_info', 'format_version', 'file_integrity',
                                         'document_pages', 'spreadsheet_sheets', 'text_content_info']
                            
                            if field_name in json_fields:
                                resource_patch_data[field_name] = json.dumps(filtered_list)
                            else:
                                resource_patch_data[field_name] = filtered_list
                            fields_to_update.append(field_name)
                        # If empty list after filtering, skip this field completely
                        continue
                    
                    # For non-list values, verify they're not just whitespace or meaningless values
                    field_str = str(field_value).strip()
                    if field_str and field_str not in ['', 'None', 'null', 'undefined', '0', '-', 'N/A', 'n/a']:
                        resource_patch_data[field_name] = field_value
                        fields_to_update.append(field_name)
                
                log.info(f"Prepared to update {len(fields_to_update)} metadata fields: {fields_to_update}")
                
                # Use resource_patch to update the fields
                if len(fields_to_update) > 0:
                    log.info(f"Updating resource {resource_id} with {len(fields_to_update)} metadata fields: {fields_to_update}")
                    log.debug(f"Resource patch data: {resource_patch_data}")
                    
                    try:
                        # Use direct action import for better worker compatibility
                        log.info(f"Getting resource_patch action...")
                        resource_patch_action = get_action('resource_patch')
                        log.info(f"Calling resource_patch action with context and data...")
                        # Defensive: ensure strings where fields expect text to avoid TypeErrors in validators
                        safe_patch_data = {}
                        for k, v in resource_patch_data.items():
                            if isinstance(v, (dict, list)):
                                try:
                                    safe_patch_data[k] = json.dumps(v)
                                except Exception:
                                    safe_patch_data[k] = str(v)
                            else:
                                safe_patch_data[k] = v
                        result = resource_patch_action(context, safe_patch_data)
                        log.info(f"Resource_patch call completed successfully!")
                        log.info(f"Successfully updated comprehensive metadata for resource {resource_id} via job queue. Updated {len(fields_to_update)} fields.")
                        log.debug(f"Update result: {result.get('id', 'No ID')} - {result.get('name', 'No name')}")

                        # Verify that all intended fields persisted; if some are missing (likely not in active schema), store them as extras
                        try:
                            resource_show = get_action('resource_show')(context, {'id': resource_id})
                            missing_fields = []
                            for fname in fields_to_update:
                                persisted = False
                                # Check direct field
                                if fname in resource_show and resource_show.get(fname):
                                    persisted = True
                                # Check extras list structure
                                if not persisted and isinstance(resource_show.get('extras'), list):
                                    for ex in resource_show['extras']:
                                        if isinstance(ex, dict) and ex.get('key') == fname and ex.get('value'):
                                            persisted = True
                                            break
                                if not persisted:
                                    missing_fields.append(fname)
                            if missing_fields:
                                log.info(f"Some fields not persisted via action (likely not in schema): {missing_fields}. Writing as extras via fallback.")
                                fallback_map = {k: metadata_fields.get(k) for k in missing_fields}
                                _update_resource_metadata_direct_db(resource_id, fallback_map, model)
                        except Exception as verify_error:
                            log.debug(f"Could not verify persisted fields: {verify_error}")
                        
                        # NOW: Clean up any empty metadata fields AFTER successful update
                        log.info(f"🧹 Cleaning up empty metadata fields after successful update for resource {resource_id}")
                        try:
                            _cleanup_empty_metadata_fields_post_processing(resource_id, model)
                        except Exception as cleanup_error:
                            log.warning(f"Error in post-processing cleanup: {cleanup_error}")
                        
                        return True
                    except Exception as patch_error:
                        log.error(f"Error in resource_patch for resource {resource_id}: {patch_error}", exc_info=True)
                        log.error(f"Context was: {context}")
                        log.error(f"Resource patch data was: {resource_patch_data}")
                        try:
                            model.Session.rollback()
                        except Exception as rollback_error:
                            log.error(f"Error during rollback: {rollback_error}")
                        
                        # FALLBACK: Try direct database update if action fails (only for fields we prepared)
                        log.warning(f"Attempting fallback direct database update for resource {resource_id}")
                        try:
                            # Restrict to fields we attempted to update
                            fallback_field_map = {k: metadata_fields.get(k) for k in fields_to_update}
                            fallback_success = _update_resource_metadata_direct_db(resource_id, fallback_field_map, model)
                            if fallback_success:
                                log.info(f"Successfully updated resource {resource_id} via fallback direct database access")
                                return True
                            else:
                                log.error(f"Fallback database update also failed for resource {resource_id}")
                        except Exception as fallback_error:
                            log.error(f"Fallback database update failed: {fallback_error}", exc_info=True)
                        
                        return False
                else:
                    log.info(f"No meaningful metadata fields to update for resource {resource_id}")
                    return True
                
            except Exception as e:
                log.error(f"Error preparing update for resource {resource_id}: {e}", exc_info=True)
                try:
                    model.Session.rollback()
                except:
                    pass
                return False
                
        else:
            log.info(f"No comprehensive metadata could be extracted from resource {resource_id}")
            return True  # Not an error, just no metadata found
            
    except Exception as e:
        log.error(f"General error in comprehensive metadata extraction job for resource {job_data.get('resource_id', 'unknown')}: {str(e)}", exc_info=True)
        # Don't re-raise to avoid crashing the worker
        import traceback
        log.debug(f"Full traceback: {traceback.format_exc()}")
        return False
    
    finally:
        # Always close the session to prevent connection leaks
        try:
            model.Session.close()
            log.debug("Database session closed")
        except:
            pass
        
        log.info(f"========= COMPLETED COMPREHENSIVE METADATA JOB =========")
    
    return True


# Función legacy para compatibilidad hacia atrás
def extract_spatial_extent_job(job_data):
    """
    Función legacy que redirige al nuevo sistema comprensivo.
    Mantenida para compatibilidad hacia atrás.
    """
    return extract_comprehensive_metadata_job(job_data)
