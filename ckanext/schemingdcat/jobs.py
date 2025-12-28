# encoding: utf-8
"""
Background job functions for ckanext-schemingdcat.

This module contains job functions that are executed by the CKAN background worker.
These functions are kept in a separate module to ensure clean imports for RQ.
"""

import sys
import os
import logging
import json
import tempfile
import urllib.request
import urllib.error


log = logging.getLogger(__name__)


def _job_log(level, msg, log_ref=None):
    """Log to both logger and stderr to ensure visibility in workers."""
    if log_ref is None:
        log_ref = log
    try:
        if level == 'info':
            log_ref.info(msg)
        elif level == 'error':
            log_ref.error(msg)
        elif level == 'warning':
            log_ref.warning(msg)
        elif level == 'debug':
            log_ref.debug(msg)
    except:
        pass
    # Always also print to stderr for worker visibility
    print(f"[METADATA JOB] [{level.upper()}] {msg}", file=sys.stderr)
    sys.stderr.flush()


def _add_member_state_to_package(package_id, member_state_uri, context, log_ref):
    """
    Add a member state (country group) to a package based on the detected spatial extent.
    
    Args:
        package_id: The ID of the package to update
        member_state_uri: The URI of the detected member state (e.g., 'http://publications.europa.eu/resource/authority/country/ZWE')
        context: CKAN context for API calls
        log_ref: Logger reference
    """
    from ckan.logic import get_action
    import ckan.model as model
    
    try:
        _job_log('info', f"Looking up group for member state URI: {member_state_uri}", log_ref)
        
        # Use the helper function that knows how to find groups for member state URIs
        from ckanext.schemingdcat import helpers as sd_helpers
        
        # Try to get the group name using the dedicated helper
        member_state_name = None
        try:
            member_state_name = sd_helpers.schemingdcat_find_member_state_group(member_state_uri, context)
            if member_state_name:
                _job_log('info', f"Found group name via helper: {member_state_name}", log_ref)
        except Exception as helper_error:
            _job_log('warning', f"Helper schemingdcat_find_member_state_group failed: {helper_error}", log_ref)
        
        # Fallback: try to get slug from URI and search groups
        if not member_state_name:
            try:
                candidate_slug = sd_helpers.schemingdcat_get_member_state_group_slug(member_state_uri)
                if candidate_slug:
                    _job_log('info', f"Got candidate slug from helper: {candidate_slug}", log_ref)
                    # Verify the group exists
                    try:
                        group_show_action = get_action('group_show')
                        group_data = group_show_action(context, {'id': candidate_slug})
                        member_state_name = group_data.get('name')
                        _job_log('info', f"Verified group exists: {member_state_name}", log_ref)
                    except Exception:
                        _job_log('warning', f"Group with slug '{candidate_slug}' not found", log_ref)
            except Exception as slug_error:
                _job_log('warning', f"Could not get slug from helper: {slug_error}", log_ref)
        
        # Last resort: extract country code from URI and search by name
        if not member_state_name:
            country_code = member_state_uri.rstrip('/').split('/')[-1].lower()
            _job_log('info', f"Trying to find group by country code: {country_code}", log_ref)
            try:
                group_show_action = get_action('group_show')
                group_data = group_show_action(context, {'id': country_code})
                member_state_name = group_data.get('name')
                _job_log('info', f"Found group by country code: {member_state_name}", log_ref)
            except Exception:
                _job_log('warning', f"Group with code '{country_code}' not found", log_ref)
        
        if not member_state_name:
            _job_log('warning', f"No group found for member state URI: {member_state_uri}", log_ref)
            return False
        
        # Get current package to check existing groups
        package_show_action = get_action('package_show')
        package_data = package_show_action(context, {'id': package_id})
        
        existing_groups = package_data.get('groups', [])
        existing_group_names = {g.get('name') for g in existing_groups}
        
        if member_state_name in existing_group_names:
            _job_log('info', f"Package {package_id} already has group {member_state_name}", log_ref)
            return True
        
        # Add the new group while preserving existing ones
        new_groups = list(existing_groups)
        new_groups.append({'name': member_state_name})
        
        # Update the package with the new group
        package_patch_action = get_action('package_patch')
        patch_data = {
            'id': package_id,
            'groups': [{'name': g.get('name')} for g in new_groups]
        }
        
        _job_log('info', f"Adding group {member_state_name} to package {package_id}", log_ref)
        package_patch_action(context, patch_data)
        _job_log('info', f"Successfully added member state {member_state_name} to package {package_id}", log_ref)
        
        return True
        
    except Exception as e:
        _job_log('error', f"Error adding member state to package: {e}", log_ref)
        return False


def extract_comprehensive_metadata_job(job_data):
    """
    Job function para extraer metadata comprensiva en segundo plano usando CKAN Jobs Queue.
    
    Función que extrae toda la información disponible de archivos (espacial y no espacial).
    
    Args:
        job_data: Diccionario con resource_id, resource_url, resource_format, package_id
    
    Returns:
        bool: True if successful, False otherwise
    """
    # IMMEDIATE print to stderr - before any imports to ensure we see something
    print(f"\n\n[METADATA JOB] ========= FUNCTION CALLED =========", file=sys.stderr)
    print(f"[METADATA JOB] Job data: {job_data}", file=sys.stderr)
    sys.stderr.flush()
    
    import traceback
    
    # Configure logging for the worker
    job_log = log
    
    # Ensure logging is configured for the worker
    if not log.handlers and not logging.root.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter('[%(name)s] %(levelname)s: %(message)s'))
        log.addHandler(handler)
        log.setLevel(logging.INFO)
    
    # Force flush to ensure logs are written
    try:
        for handler in logging.root.handlers:
            handler.flush()
    except:
        pass
    
    try:
        _job_log('info', "========= STARTING COMPREHENSIVE METADATA JOB =========", log)
        _job_log('info', f"Job data received: {job_data}", log)
        _job_log('info', f"Python version: {sys.version}", log)
        _job_log('info', f"Working directory: {os.getcwd()}", log)
        
        # Force flush again after initial log
        for handler in logging.root.handlers:
            try:
                handler.flush()
            except:
                pass
        
    except Exception as early_log_error:
        print(f"[METADATA JOB] Early logging error: {early_log_error}", file=sys.stderr)
        print(f"[METADATA JOB] Job data: {job_data}", file=sys.stderr)
        sys.stderr.flush()
    
    try:
        # Get job data with validation
        if not isinstance(job_data, dict):
            _job_log('error', f"Invalid job_data type: {type(job_data)}, expected dict", log)
            return False
            
        resource_id = job_data.get('resource_id')
        resource_url = job_data.get('resource_url')
        resource_format = job_data.get('resource_format')
        package_id = job_data.get('package_id')
        skip_spatial = bool(job_data.get('skip_spatial'))
        
        if not resource_id:
            _job_log('error', "No resource_id in job_data", log)
            return False
            
        _job_log('info', f"Processing comprehensive metadata job for resource {resource_id}", log)
        _job_log('info', f"Resource URL: {resource_url}", log)
        _job_log('info', f"Resource format: {resource_format}", log)
        _job_log('info', f"Package ID: {package_id}", log)
        
        # CKAN imports inside try block to handle import errors
        try:
            import ckan.model as model
            import ckan.plugins.toolkit as toolkit
            from ckan.logic import get_action
            from ckanext.scheming import logic as scheming_logic
            import ckan.plugins as p
            
            # Ensure scheming actions are available in the worker context
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
                                _job_log('info', f"Registered action {action_name} from {plugin_name}", log)
                except Exception as plugin_error:
                    _job_log('warning', f"Could not load actions from {plugin_name}: {plugin_error}", log)
            
            _job_log('info', "CKAN modules imported successfully", log)
        except ImportError as e:
            _job_log('error', f"Could not import CKAN modules: {e}", log)
            return False
        
        # Import analyzer
        try:
            from ckanext.schemingdcat.spatial_extent import FileAnalyzer
            _job_log('info', "FileAnalyzer imported successfully", log)
        except ImportError as e:
            _job_log('error', f"Could not import FileAnalyzer: {e}", log)
            return False
            
        # Create analyzer instance
        try:
            analyzer = FileAnalyzer(
                resource_id=resource_id,
                skip_spatial=skip_spatial
            )
            _job_log('info', f"FileAnalyzer created successfully for resource {resource_id}", log)
        except Exception as e:
            _job_log('error', f"Error creating FileAnalyzer: {e}", log)
            return False
        
        # Process the file and extract metadata
        metadata = {}
        
        try:
            if resource_url:
                _job_log('info', f"Analyzing remote file: {resource_url}", log)
                
                # Download file to temporary location for analysis
                suffix = ''
                if resource_format:
                    suffix = f'.{resource_format.lower()}'
                elif '.' in resource_url:
                    suffix = os.path.splitext(resource_url)[-1]
                
                _job_log('info', f"Creating temporary file with suffix: {suffix}", log)
                
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
                    try:
                        _job_log('info', f"Starting download from: {resource_url}", log)
                        
                        # Download with retries
                        max_retries = 3
                        backoff = 2
                        last_error = None
                        
                        for attempt in range(max_retries):
                            try:
                                req = urllib.request.Request(
                                    resource_url,
                                    headers={
                                        'User-Agent': 'CKAN SchemingDCAT Metadata Extractor/1.0',
                                        'Accept': '*/*'
                                    }
                                )
                                with urllib.request.urlopen(req, timeout=300) as response:
                                    chunk_size = 8192
                                    total_size = 0
                                    while True:
                                        chunk = response.read(chunk_size)
                                        if not chunk:
                                            break
                                        tmp_file.write(chunk)
                                        total_size += len(chunk)
                                
                                _job_log('info', f"Downloaded {total_size} bytes to {tmp_file.name}", log)
                                tmp_file.flush()
                                
                                # Analyze the downloaded file
                                metadata = analyzer.analyze_file(tmp_file.name)
                                if metadata:
                                    _job_log('info', f"Extracted metadata: {list(metadata.keys())}", log)
                                else:
                                    _job_log('info', "No metadata extracted from file", log)
                                break
                                
                            except urllib.error.HTTPError as e:
                                last_error = e
                                log.warning(f"Download attempt {attempt + 1}/{max_retries} failed: {e}")
                                if attempt < max_retries - 1:
                                    import time
                                    time.sleep(backoff)
                                    backoff *= 2
                            except urllib.error.URLError as e:
                                last_error = e
                                log.warning(f"Download attempt {attempt + 1}/{max_retries} failed: {e}")
                                if attempt < max_retries - 1:
                                    import time
                                    time.sleep(backoff)
                                    backoff *= 2

                        if last_error is not None:
                            _job_log('error', f"All download attempts failed: {last_error}", log)
                        
                    except urllib.error.URLError as e:
                        _job_log('error', f"URL error downloading file: {e}", log)
                    except Exception as e:
                        _job_log('error', f"Error downloading file for analysis: {e}", log)
                    finally:
                        # Clean up temporary file
                        try:
                            if os.path.exists(tmp_file.name):
                                os.unlink(tmp_file.name)
                                log.debug(f"Cleaned up temporary file: {tmp_file.name}")
                        except Exception as cleanup_error:
                            log.warning(f"Could not clean up temporary file {tmp_file.name}: {cleanup_error}")
            else:
                _job_log('warning', "No resource URL provided for analysis", log)
                
        except Exception as e:
            _job_log('error', f"Error extracting comprehensive metadata: {e}", log)
            log.error(f"Error extracting comprehensive metadata: {e}", exc_info=True)
            return False
        
        if metadata:
            _job_log('info', f"Successfully extracted comprehensive metadata from resource {resource_id} in job", log)
            _job_log('info', f"Metadata fields extracted: {list(metadata.keys())}", log)
            
            log.debug(f"Raw metadata extracted: {json.dumps(metadata, indent=2, default=str)}")

            # Detect member state (country) from spatial extent
            detected_member_uri = None
            try:
                extent_geojson = metadata.get('spatial_extent')
                _job_log('info', f"Attempting member state detection for resource {resource_id}, extent available: {extent_geojson is not None}", log)
                if extent_geojson:
                    if isinstance(extent_geojson, str):
                        try:
                            extent_geojson = json.loads(extent_geojson)
                        except Exception as parse_err:
                            _job_log('warning', f"Could not parse spatial_extent as JSON: {parse_err}", log)
                    
                    _job_log('info', f"Extent GeoJSON type: {extent_geojson.get('type') if isinstance(extent_geojson, dict) else type(extent_geojson)}", log)
                    
                    from ckanext.schemingdcat import helpers as sd_helpers
                    detected_member_uri = sd_helpers.schemingdcat_detect_member_state(extent_geojson)
                    
                    if detected_member_uri:
                        _job_log('info', f"Detected member state for resource {resource_id}: {detected_member_uri}", log)
                    else:
                        _job_log('info', f"No member state detected for resource {resource_id} (detection returned None)", log)
                else:
                    _job_log('info', f"No spatial_extent in metadata for resource {resource_id}, skipping member state detection", log)
            except Exception as e:
                _job_log('warning', f"Could not detect member state from extent for resource {resource_id}: {e}", log)
                log.warning(f"Could not detect member state from extent for resource {resource_id}: {e}", exc_info=True)
            
            try:
                # Ensure we have a valid database session
                try:
                    model.Session.close()
                    model.Session.remove()
                except:
                    pass
                
                # Get fresh context
                admin_user = model.Session.query(model.User).filter_by(sysadmin=True).first()
                context = {
                    'model': model,
                    'session': model.Session,
                    'user': admin_user.name if admin_user else 'default',
                    'ignore_auth': True,
                    'defer_commit': False
                }
                
                resource_patch_action = get_action('resource_patch')
                
                # Build a dict of metadata fields (for resource)
                metadata_fields = {}
                
                # Add spatial extent if available
                if metadata.get('spatial_extent'):
                    extent = metadata['spatial_extent']
                    if isinstance(extent, dict):
                        metadata_fields['spatial_extent'] = json.dumps(extent)
                    else:
                        metadata_fields['spatial_extent'] = extent
                
                # Add projection/CRS info
                if metadata.get('crs'):
                    metadata_fields['projection'] = metadata['crs']
                
                if metadata.get('crs_wkt'):
                    metadata_fields['crs_wkt'] = metadata['crs_wkt']
                
                # Add layer info
                if metadata.get('layer_count'):
                    metadata_fields['layer_count'] = str(metadata['layer_count'])
                    
                if metadata.get('layer_names'):
                    layer_names = metadata['layer_names']
                    if isinstance(layer_names, list):
                        metadata_fields['layer_names'] = json.dumps(layer_names)
                    else:
                        metadata_fields['layer_names'] = str(layer_names)
                
                # Add feature count
                if metadata.get('feature_count'):
                    metadata_fields['feature_count'] = str(metadata['feature_count'])
                
                # Add geometry type
                if metadata.get('geometry_type'):
                    metadata_fields['geometry_type'] = metadata['geometry_type']
                
                # Add attribute info
                if metadata.get('attributes'):
                    attrs = metadata['attributes']
                    if isinstance(attrs, list):
                        metadata_fields['attributes'] = json.dumps(attrs)
                    else:
                        metadata_fields['attributes'] = str(attrs)
                
                # Add raster-specific metadata
                if metadata.get('raster_bands'):
                    metadata_fields['raster_bands'] = str(metadata['raster_bands'])
                    
                if metadata.get('raster_resolution'):
                    res = metadata['raster_resolution']
                    if isinstance(res, (list, tuple)):
                        metadata_fields['raster_resolution'] = f"{res[0]}x{res[1]}"
                    else:
                        metadata_fields['raster_resolution'] = str(res)
                
                if metadata.get('raster_nodata'):
                    metadata_fields['raster_nodata'] = str(metadata['raster_nodata'])
                
                # Add file-level metadata
                if metadata.get('file_size'):
                    metadata_fields['size'] = str(metadata['file_size'])
                
                _job_log('info', f"Prepared metadata fields for resource update: {list(metadata_fields.keys())}", log)
                
                # Filter out None values and prepare patch data
                fields_to_update = [k for k, v in metadata_fields.items() if v is not None and v != '']
                
                if fields_to_update:
                    resource_patch_data = {
                        'id': resource_id,
                    }
                    for field in fields_to_update:
                        resource_patch_data[field] = metadata_fields[field]
                    
                    _job_log('info', f"Updating resource {resource_id} with {len(fields_to_update)} metadata fields", log)
                    
                    try:
                        # Ensure JSON serializable
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
                        _job_log('info', f"Resource_patch call completed successfully!", log)
                        _job_log('info', f"Successfully updated comprehensive metadata for resource {resource_id}. Updated {len(fields_to_update)} fields.", log)
                        log.debug(f"Update result: {result.get('id', 'No ID')} - {result.get('name', 'No name')}")
                        
                        # Now add member state to the package if detected
                        if detected_member_uri and package_id:
                            try:
                                _job_log('info', f"Adding member state {detected_member_uri} to package {package_id}", log)
                                _add_member_state_to_package(package_id, detected_member_uri, context, log)
                            except Exception as group_error:
                                _job_log('warning', f"Could not add member state to package: {group_error}", log)
                        
                        return True
                    except Exception as patch_error:
                        log.error(f"Error in resource_patch for resource {resource_id}: {patch_error}", exc_info=True)
                        return False
                else:
                    _job_log('info', f"No meaningful metadata fields to update for resource {resource_id}", log)
                    # Even if no resource metadata, still add member state if detected
                    if detected_member_uri and package_id:
                        try:
                            _job_log('info', f"Adding member state {detected_member_uri} to package {package_id}", log)
                            _add_member_state_to_package(package_id, detected_member_uri, context, log)
                        except Exception as group_error:
                            _job_log('warning', f"Could not add member state to package: {group_error}", log)
                    return True
                
            except Exception as e:
                log.error(f"Error preparing update for resource {resource_id}: {e}", exc_info=True)
                try:
                    model.Session.rollback()
                except:
                    pass
                return False
                
        else:
            _job_log('info', f"No comprehensive metadata could be extracted from resource {resource_id}", log)
            return True  # Not an error, just no metadata found
            
    except Exception as e:
        error_msg = f"General error in comprehensive metadata extraction job for resource {job_data.get('resource_id', 'unknown')}: {str(e)}"
        log.error(error_msg, exc_info=True)
        print(f"[METADATA JOB ERROR] {error_msg}", file=sys.stderr)
        print(f"[METADATA JOB ERROR] Traceback:\n{traceback.format_exc()}", file=sys.stderr)
        sys.stderr.flush()
        return False
    
    finally:
        # Always close the session to prevent connection leaks
        try:
            import ckan.model as model
            model.Session.close()
            log.debug("Database session closed")
        except:
            pass
        
        # Final completion log
        _job_log('info', "========= COMPLETED COMPREHENSIVE METADATA JOB =========", log)
    
    return True


# Función legacy para compatibilidad hacia atrás
def extract_spatial_extent_job(job_data):
    """
    Función legacy que redirige al nuevo sistema comprensivo.
    Mantenida para compatibilidad hacia atrás.
    """
    return extract_comprehensive_metadata_job(job_data)


# Simple test job to verify RQ worker is functioning
def test_simple_job(data):
    """A minimal test job to verify the worker executes jobs correctly."""
    print(f"[TEST JOB] ========= TEST JOB EXECUTED =========", file=sys.stderr)
    print(f"[TEST JOB] Data received: {data}", file=sys.stderr)
    sys.stderr.flush()
    return True


# Debug confirmation
print(f"[SCHEMINGDCAT JOBS] Module loaded successfully", file=sys.stderr)
print(f"[SCHEMINGDCAT JOBS] extract_comprehensive_metadata_job = {extract_comprehensive_metadata_job}", file=sys.stderr)
sys.stderr.flush()
