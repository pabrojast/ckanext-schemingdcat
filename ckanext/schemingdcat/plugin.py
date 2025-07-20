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

    def update_config(self, config_):
        # Call parent update_config first
        super(SchemingDCATDatasetsPlugin, self).update_config(config_)
        
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

    # IResourceController - handle spatial extent extraction for spatial resources
    def after_create(self, context, resource):
        """
        Hook que se ejecuta después de crear un recurso.
        Aquí procesamos la extracción de extensión espacial para recursos geoespaciales.
        """
        try:
            self._process_spatial_extent_extraction_for_resource(context, resource)
        except Exception as e:
            log.warning(f"Error in spatial extent extraction after resource creation: {str(e)}")
        
        return resource

    def after_update(self, context, resource):
        """
        Hook que se ejecuta después de actualizar un recurso.
        También procesamos la extracción de extensión espacial aquí.
        """
        try:
            self._process_spatial_extent_extraction_for_resource(context, resource)
        except Exception as e:
            log.warning(f"Error in spatial extent extraction after resource update: {str(e)}")
        
        return resource

    # Hook para evitar problemas con otros plugins durante actualizaciones espaciales automáticas
    def before_dataset_update(self, context, current, updated):
        """
        Hook que se ejecuta antes de actualizar un dataset.
        Detecta si es una actualización automática de spatial extent para evitar hooks problemáticos.
        """
        # Detectar si esta es una actualización automática de spatial extent
        if (context.get('spatial_extent_update') or 
            context.get('skip_spatial_hooks') or
            (len(updated.keys()) == 2 and 'id' in updated and 'spatial_extent' in updated)):
            
            # Marcar el contexto para que otros plugins sepan que es una actualización espacial
            context['__spatial_extent_auto_update__'] = True
            log.debug(f"Detected automatic spatial extent update for dataset {updated.get('id', 'unknown')}")
        
        return updated
        
    def _is_potential_spatial_resource(self, resource):
        """
        Determina si un recurso puede contener datos geoespaciales.
        
        IMPORTANTE: Los archivos ZIP con shapefiles se suben con formato "SHP", no "ZIP"
        porque CKAN detecta el contenido y asigna el formato basado en los archivos principales.
        
        Args:
            resource: El diccionario del recurso
            
        Returns:
            bool: True si el recurso puede contener datos espaciales
        """
        try:
            # Verificar formato del recurso - CLAVE: Los ZIP se marcan como "SHP"
            resource_format = resource.get('format', '').lower()
            spatial_formats = ['shp', 'shapefile', 'zip', 'tif', 'tiff', 'geotiff', 
                              'kml', 'gpkg', 'geopackage', 'geojson', 'json']
            
            if resource_format in spatial_formats:
                log.debug(f"Resource {resource.get('id', 'unknown')} has spatial format: {resource_format}")
                return True
                
            # Verificar extensión del archivo en la URL como respaldo
            url = resource.get('url', '')
            if url:
                url_lower = url.lower()
                spatial_extensions = ['.shp', '.zip', '.tif', '.tiff', '.kml', '.gpkg', '.geojson']
                for ext in spatial_extensions:
                    if url_lower.endswith(ext):
                        log.debug(f"Resource {resource.get('id', 'unknown')} has spatial extension in URL: {ext}")
                        return True
            
            log.debug(f"Resource {resource.get('id', 'unknown')} is not spatial - format: {resource_format}, url: {url}")
            return False
            
        except Exception as e:
            log.warning(f"Error checking if resource is spatial: {str(e)}")
            # En caso de error, ser conservador y asumir que no es espacial
            return False
        
    def _extract_spatial_extent_from_resource(self, resource):
        """
        Extrae la extensión espacial de un recurso.
        
        Args:
            resource: El diccionario del recurso
            
        Returns:
            dict: La extensión espacial en formato GeoJSON o None
        """
        try:
            # Verificar si el módulo de extensión espacial está disponible
            try:
                from ckanext.schemingdcat.spatial_extent import extent_extractor
            except ImportError:
                log.debug("Spatial extent extraction module not available")
                return None
            
            resource_url = resource.get('url')
            resource_format = resource.get('format', '').upper()
            
            if not resource_url:
                log.debug("No URL found for resource")
                return None
                
            log.info(f"Attempting to extract spatial extent from resource: {resource_url} (format: {resource_format})")
            
            # Usar el método para extraer desde URL de recurso
            extent = extent_extractor.extract_extent_from_resource(resource_url, resource_format)
            
            if extent:
                log.info(f"Successfully extracted extent: {extent}")
                return extent
            else:
                log.debug(f"Could not extract extent from resource: {resource_url}")
                return None
                
        except Exception as e:
            log.warning(f"Error extracting spatial extent from resource: {str(e)}")
            return None
        
    def _should_skip_spatial_extraction(self, context, package_id):
        """
        Determina si se debe omitir la extracción automática de extensión espacial.
        
        Retorna True si:
        - El dataset ya tiene spatial_extent (respeta datos existentes)
        - Hay datos manuales en el contexto del formulario (respeta entrada manual)
        - Se detecta que el usuario ha ingresado datos manualmente
        
        Args:
            context: El contexto de CKAN
            package_id: ID del dataset
            
        Returns:
            bool: True si se debe omitir la extracción automática
        """
        try:
            # 1. Verificar si el dataset actual ya tiene spatial_extent
            try:
                dataset = toolkit.get_action('package_show')(context, {'id': package_id})
                existing_extent = dataset.get('spatial_extent')
                if existing_extent and existing_extent.strip():
                    log.debug(f"Dataset {package_id} already has spatial extent: {existing_extent[:100]}...")
                    return True
            except Exception as e:
                log.debug(f"Could not retrieve dataset {package_id} for extent check: {str(e)}")
                # Si no podemos obtener el dataset, continuamos con otras verificaciones
            
            # 2. Verificar si hay datos manuales en el contexto/request actual
            # Esto captura casos donde el usuario está editando el formulario
            request_data = getattr(context.get('request'), 'form', None) if context.get('request') else None
            if request_data:
                manual_extent = request_data.get('spatial_extent')
                if manual_extent and manual_extent.strip():
                    log.debug(f"Manual spatial extent detected in form data: {manual_extent[:100]}...")
                    return True
            
            # 3. Verificar flags del contexto que indican omitir extracción
            if context.get('skip_spatial_extraction') or context.get('manual_spatial_extent'):
                log.debug(f"Spatial extraction explicitly skipped via context flags")
                return True
            
            # 4. Verificar si hay datos en el diccionario de datos del contexto
            # Esto captura casos donde se está creando/editando un dataset completo
            package_dict = context.get('package_dict', {})
            if isinstance(package_dict, dict):
                manual_extent = package_dict.get('spatial_extent')
                if manual_extent and manual_extent.strip():
                    log.debug(f"Manual spatial extent detected in package dict: {manual_extent[:100]}...")
                    return True
            
            # 5. Verificar en la sesión (para casos de formularios multi-paso)
            session = context.get('session')
            if session and hasattr(session, 'get'):
                session_extent = session.get('spatial_extent')
                if session_extent and session_extent.strip():
                    log.debug(f"Manual spatial extent detected in session: {session_extent[:100]}...")
                    return True
            
            log.debug(f"No existing or manual spatial extent detected for dataset {package_id} - auto-extraction allowed")
            return False
            
        except Exception as e:
            log.warning(f"Error checking if spatial extraction should be skipped: {str(e)}")
            # En caso de error, ser conservador y omitir la extracción automática
            return True
        
    def _process_spatial_extent_extraction_for_resource(self, context, resource):
        """
        Procesa la extracción de extensión espacial para un recurso específico que pueda ser geoespacial.
        Ahora ejecuta en segundo plano para no bloquear al usuario.
        
        Args:
            context: El contexto de CKAN
            resource: El diccionario del recurso
        """
        try:
            # Verificar si es un recurso potencialmente espacial
            if not self._is_potential_spatial_resource(resource):
                log.debug(f"Resource {resource.get('id', 'unknown')} is not a potential spatial resource")
                return
                
            log.info(f"Processing spatial resource {resource.get('id', 'unknown')} with format {resource.get('format', 'unknown')}")
            
            # Obtener el dataset padre
            package_id = resource.get('package_id')
            if not package_id:
                log.warning("No package_id found for resource")
                return
                
            # Verificar si ya existe spatial_extent (manual o previo)
            should_skip = self._should_skip_spatial_extraction(context, package_id)
            if should_skip:
                log.debug(f"Skipping spatial extent extraction for dataset {package_id} - manual or existing extent detected")
                return
            
            # **PROCESAMIENTO ASÍNCRONO**: Usar CKAN Jobs Queue (preferido) o threading como fallback
            try:
                # Método 1: Usar CKAN Jobs Queue (recomendado)
                from ckan.lib import jobs
                
                # Verificar si hay worker activo antes de encolar
                try:
                    # Intentar obtener estadísticas de la cola para verificar workers
                    from ckan.lib.jobs import DEFAULT_QUEUE_NAME
                    import redis
                    
                    # Si redis no está disponible o no hay workers, usar threading
                    redis_url = toolkit.config.get('ckan.redis.url', 'redis://localhost:6379/1')
                    
                    # Verificación simple: Si el job anterior sigue pendiente por mucho tiempo, usar threading
                    if hasattr(jobs, 'get_queue'):
                        queue = jobs.get_queue(DEFAULT_QUEUE_NAME)
                        if queue and hasattr(queue, 'count'):
                            pending_jobs = queue.count
                            if pending_jobs > 5:  # Si hay muchos jobs pendientes, probablemente no hay worker
                                log.warning(f"Too many pending jobs ({pending_jobs}), worker may be inactive. Using threading fallback.")
                                raise ImportError("Worker appears inactive")
                    
                except Exception:
                    # Si no podemos verificar la cola, intentar encolar de todas formas
                    pass
                
                # Preparar datos para el job
                job_data = {
                    'resource_id': resource.get('id'),
                    'resource_url': resource.get('url'),
                    'resource_format': resource.get('format'),
                    'package_id': package_id
                }
                
                # Encolar el job de extracción espacial
                job = jobs.enqueue(
                    extract_spatial_extent_job,
                    [job_data],
                    title=f"Spatial extent extraction for resource {resource.get('id', 'unknown')[:8]}"
                )
                
                log.info(f"Enqueued spatial extent extraction job {job.id} for resource {resource.get('id', 'unknown')}")
                
                # Programar fallback a threading si el job no se procesa en un tiempo razonable
                import threading
                import time
                
                def check_job_progress():
                    """Verificar si el job se procesa y usar threading como fallback si no."""
                    time.sleep(30)  # Esperar 30 segundos
                    try:
                        # Si el job sigue sin procesar, usar threading
                        if hasattr(job, 'get_status') and job.get_status() == 'queued':
                            log.warning(f"Job {job.id} still queued after 30s, starting threading fallback")
                            self._process_spatial_extent_with_threading(resource, package_id)
                    except Exception as e:
                        log.debug(f"Could not check job status: {e}")
                
                # Lanzar verificación en background
                threading.Thread(target=check_job_progress, daemon=True).start()
                
            except ImportError:
                # Fallback: Usar threading si jobs no está disponible
                log.warning("CKAN Jobs not available, falling back to threading")
                self._process_spatial_extent_with_threading(resource, package_id)
            except TypeError as e:
                # Error de parámetros en jobs.enqueue (versión antigua)
                log.warning(f"Jobs.enqueue parameter error: {str(e)}, falling back to threading")
                self._process_spatial_extent_with_threading(resource, package_id)
                
        except Exception as e:
            log.warning(f"Error in spatial extent extraction for resource: {str(e)}")
            # No lanzar excepción para no interrumpir el flujo normal de creación del recurso

    def _process_spatial_extent_with_threading(self, resource, package_id):
        """Fallback method using threading for spatial extent extraction WITHOUT Flask context."""
        import threading
        
        def extract_spatial_extent_async():
            """Función que ejecuta la extracción en segundo plano SIN contexto Flask."""
            try:
                log.info(f"Starting background spatial extent extraction for resource {resource.get('id', 'unknown')} (threading mode)")
                
                # Intentar extraer la extensión espacial del recurso DIRECTAMENTE
                try:
                    from ckanext.schemingdcat.spatial_extent import extent_extractor
                    
                    resource_url = resource.get('url')
                    resource_format = resource.get('format', '').upper()
                    
                    if not resource_url:
                        log.debug("No URL found for resource in threading mode")
                        return
                    
                    # Extraer extensión espacial directamente
                    extent = extent_extractor.extract_extent_from_resource(resource_url, resource_format)
                    
                    if extent:
                        log.info(f"Successfully extracted spatial extent from resource {resource.get('id', 'unknown')} in threading mode")
                        
                        # Usar actualización directa en BD (NO requiere contexto Flask)
                        success = self._update_dataset_spatial_extent_direct_db(package_id, extent)
                        
                        if success:
                            log.info(f"Threading mode update completed successfully for dataset {package_id}")
                        else:
                            log.warning(f"Threading mode update failed for dataset {package_id}")
                    else:
                        log.debug(f"Could not extract spatial extent from resource {resource.get('id', 'unknown')} in threading mode")
                        
                except ImportError:
                    log.warning("Spatial extent extraction module not available in threading mode")
                except Exception as e:
                    log.error(f"Error in spatial extent extraction in threading mode: {str(e)}", exc_info=True)
                        
            except Exception as e:
                log.error(f"General error in background spatial extent extraction for resource {resource.get('id', 'unknown')}: {str(e)}", exc_info=True)
        
        # Lanzar el thread de extracción en segundo plano
        extraction_thread = threading.Thread(
            target=extract_spatial_extent_async,
            name=f"spatial_extent_extraction_{resource.get('id', 'unknown')[:8]}",
            daemon=True  # Thread daemon para que no bloquee el cierre de la aplicación
        )
        extraction_thread.start()
        
        log.info(f"Started background spatial extent extraction for resource {resource.get('id', 'unknown')} (threading mode)")

    def _update_dataset_spatial_extent_direct_db(self, package_id, extent):
        """
        Actualización directa en BD sin contexto Flask - para uso en threads.
        
        Args:
            package_id: ID del dataset
            extent: La extensión espacial en formato GeoJSON
            
        Returns:
            bool: True si la actualización fue exitosa
        """
        try:
            import ckan.model as model
            import json
            
            # Preparar los datos
            extent_json = json.dumps(extent) if isinstance(extent, dict) else extent
            
            log.info(f"Attempting direct DB update for dataset {package_id}")
            
            # Actualizar directamente en la base de datos sin contexto Flask
            package = model.Package.get(package_id)
            if not package:
                log.error(f"Package {package_id} not found in database for direct update")
                return False
            
            # Buscar si ya existe un extra con spatial_extent
            spatial_extra = None
            for extra in package.extras_list:
                if extra.key == 'spatial_extent':
                    spatial_extra = extra
                    break
            
            if spatial_extra:
                # Actualizar extra existente
                spatial_extra.value = extent_json
                log.debug(f"Updated existing spatial_extent extra for dataset {package_id}")
            else:
                # Crear nuevo extra
                from ckan.model.package_extra import PackageExtra
                new_extra = PackageExtra(
                    package_id=package_id,
                    key='spatial_extent',
                    value=extent_json
                )
                model.Session.add(new_extra)
                log.debug(f"Created new spatial_extent extra for dataset {package_id}")
            
            # Commit los cambios
            model.Session.commit()
            
            log.info(f"Successfully updated spatial_extent for dataset {package_id} via direct DB access")
            return True
            
        except Exception as e:
            try:
                model.Session.rollback()
            except:
                pass
            log.error(f"Error in direct DB update for dataset {package_id}: {str(e)}", exc_info=True)
            return False


def extract_spatial_extent_job(job_data):
    """
    Job function para extraer spatial extent en segundo plano usando CKAN Jobs Queue.
    
    Función simplificada que NO requiere load_config para funcionar en workers.
    
    Args:
        job_data: Diccionario con resource_id, resource_url, resource_format, package_id
    """
    try:
        import ckan.model as model
        import json
        import logging
        
        # Configurar logging para el worker
        log = logging.getLogger(__name__)
        
        # Obtener datos del job
        resource_id = job_data.get('resource_id')
        resource_url = job_data.get('resource_url')
        resource_format = job_data.get('resource_format')
        package_id = job_data.get('package_id')
        
        log.info(f"Processing spatial extent job for resource {resource_id}")
        
        # Importar extractor (sin configuración adicional necesaria)
        try:
            from ckanext.schemingdcat.spatial_extent import extent_extractor
        except ImportError as e:
            log.error(f"Could not import spatial extent extractor: {e}")
            return
        
        # Extraer extensión espacial directamente
        try:
            extent = extent_extractor.extract_extent_from_resource(resource_url, resource_format)
        except Exception as e:
            log.error(f"Error extracting spatial extent: {e}")
            return
        
        if extent:
            log.info(f"Successfully extracted spatial extent from resource {resource_id} in job")
            
            try:
                # Actualizar directamente en la base de datos (método simple)
                package = model.Package.get(package_id)
                if not package:
                    log.error(f"Package {package_id} not found for spatial extent update")
                    return
                
                extent_json = json.dumps(extent)
                
                # Buscar extra existente
                spatial_extra = None
                for extra in package.extras_list:
                    if extra.key == 'spatial_extent':
                        spatial_extra = extra
                        break
                
                if spatial_extra:
                    # Actualizar extra existente
                    spatial_extra.value = extent_json
                    log.debug(f"Updated existing spatial_extent extra for dataset {package_id}")
                else:
                    # Crear nuevo extra
                    from ckan.model.package_extra import PackageExtra
                    new_extra = PackageExtra(
                        package_id=package_id,
                        key='spatial_extent',
                        value=extent_json
                    )
                    model.Session.add(new_extra)
                    log.debug(f"Created new spatial_extent extra for dataset {package_id}")
                
                # Commit los cambios
                model.Session.commit()
                log.info(f"Successfully updated spatial_extent for dataset {package_id} via job queue")
                
            except Exception as e:
                log.error(f"Error updating database: {e}")
                try:
                    model.Session.rollback()
                except:
                    pass
                return
                
        else:
            log.info(f"No spatial extent could be extracted from resource {resource_id}")
            
    except Exception as e:
        log.error(f"General error in spatial extent extraction job: {str(e)}")
        # No re-raise para evitar que el worker se cierre abruptamente
    
    def _update_dataset_spatial_extent_with_app_context(self, dataset_id, extent):
        """
        Actualiza el campo spatial_extent de un dataset en contexto de thread asíncrono.
        
        Este método evita problemas de contexto Flask y hooks de otros plugins
        que pueden fallar cuando se ejecutan fuera del contexto de request HTTP.
        
        Args:
            dataset_id: El ID del dataset
            extent: La extensión espacial en formato GeoJSON
        """
        try:
            # Preparar los datos para la actualización
            extent_json = json.dumps(extent) if isinstance(extent, dict) else extent
            
            # Crear un contexto de sistema limpio con permisos de administrador
            import ckan.model as model
            system_context = {
                'model': model,
                'session': model.Session,
                'ignore_auth': True,  # Usar permisos de sistema
                'user': '',  # Usuario del sistema
                'api_version': 3,
                'for_update': True,  # Evitar conflictos de concurrencia
                'defer_commit': False,  # Commit inmediato
                'skip_spatial_hooks': True  # Flag para evitar re-procesamiento
            }
            
            # Obtener el dataset actual para verificar que existe
            try:
                current_dataset = toolkit.get_action('package_show')(system_context, {'id': dataset_id})
                log.debug(f"Found dataset {dataset_id} for spatial extent update")
            except Exception as e:
                log.error(f"Could not retrieve dataset {dataset_id} for spatial extent update: {str(e)}")
                return False
            
            # **MÉTODO DIRECTO**: Actualizar directamente en la base de datos para evitar hooks
            try:
                # Obtener el objeto del modelo
                package = model.Package.get(dataset_id)
                if not package:
                    log.error(f"Package {dataset_id} not found in database")
                    return False
                
                # Buscar si ya existe un extra con spatial_extent
                spatial_extra = None
                for extra in package.extras_list:
                    if extra.key == 'spatial_extent':
                        spatial_extra = extra
                        break
                
                if spatial_extra:
                    # Actualizar extra existente
                    spatial_extra.value = extent_json
                    log.debug(f"Updated existing spatial_extent extra for dataset {dataset_id}")
                else:
                    # Crear nuevo extra
                    from ckan.model.package_extra import PackageExtra
                    new_extra = PackageExtra(
                        package_id=dataset_id,
                        key='spatial_extent',
                        value=extent_json
                    )
                    model.Session.add(new_extra)
                    log.debug(f"Created new spatial_extent extra for dataset {dataset_id}")
                
                # Commit los cambios
                model.Session.commit()
                
                log.info(f"Successfully updated spatial_extent for dataset {dataset_id} via direct database update")
                return True
                
            except Exception as e:
                model.Session.rollback()
                log.error(f"Error in direct database update for dataset {dataset_id}: {str(e)}", exc_info=True)
                
                # Fallback: Usar package_patch con contexto especial
                try:
                    # Agregar flag para identificar que es una actualización espacial automática
                    system_context['skip_hooks'] = True
                    system_context['spatial_extent_update'] = True
                    
                    update_data = {
                        'id': dataset_id,
                        'spatial_extent': extent_json
                    }
                    
                    # Usar package_patch como fallback
                    result = toolkit.get_action('package_patch')(system_context, update_data)
                    
                    log.info(f"Successfully updated spatial_extent for dataset {dataset_id} via package_patch fallback")
                    return True
                    
                except Exception as e2:
                    log.error(f"Fallback package_patch also failed for dataset {dataset_id}: {str(e2)}", exc_info=True)
                    return False
            
        except Exception as e:
            log.error(f"General error updating spatial extent for dataset {dataset_id}: {str(e)}", exc_info=True)
            return False

    def _update_dataset_spatial_extent(self, context, dataset_id, extent):
        """
        Actualiza el campo spatial_extent de un dataset (método original para uso síncrono).
        
        Args:
            context: El contexto de CKAN
            dataset_id: El ID del dataset
            extent: La extensión espacial en formato GeoJSON
        """
        try:
            # Preparar los datos para la actualización
            extent_json = json.dumps(extent) if isinstance(extent, dict) else extent
            
            # Crear un contexto de sistema limpio con permisos de administrador
            import ckan.model as model
            system_context = {
                'model': model,
                'session': model.Session,
                'ignore_auth': True,  # Usar permisos de sistema
                'user': '',  # Usuario del sistema
                'api_version': 3,
                'for_update': True,  # Evitar conflictos de concurrencia
                'return_type': 'dict'
            }
            
            # Obtener el dataset actual para verificar que existe
            try:
                current_dataset = toolkit.get_action('package_show')(system_context, {'id': dataset_id})
                log.debug(f"Found dataset {dataset_id} for spatial extent update")
            except Exception as e:
                log.error(f"Could not retrieve dataset {dataset_id} for spatial extent update: {str(e)}")
                return False
            
            # Actualizar solo el campo spatial_extent del dataset
            update_data = {
                'id': dataset_id,
                'spatial_extent': extent_json
            }
            
            # Usar package_patch para actualizar solo el campo específico
            result = toolkit.get_action('package_patch')(system_context, update_data)
            
            log.info(f"Successfully updated spatial_extent for dataset {dataset_id}")
            log.debug(f"Updated dataset: {result.get('name', 'unknown')}")
            
            return True
            
        except Exception as e:
            log.error(f"Error updating spatial extent for dataset {dataset_id}: {str(e)}", exc_info=True)
            return False


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
