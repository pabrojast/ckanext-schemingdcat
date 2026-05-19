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
from contextlib import contextmanager

from sqlalchemy.orm.attributes import flag_modified


log = logging.getLogger(__name__)


def _metadata_extraction_limits():
    """
    Read metadata extraction limits from config.
    - schemingdcat.metadata_extraction.max_field_bytes (default 50000)
    - schemingdcat.metadata_extraction.drop_fields (comma/space separated)
    """
    try:
        from ckan.common import config
        from ckanext.schemingdcat import config as sdct_config
        default_max = getattr(sdct_config, 'metadata_extraction_default_max_field_bytes', 50000)
        default_drop = getattr(sdct_config, 'metadata_extraction_default_drop_fields', [])

        raw_max = config.get('schemingdcat.metadata_extraction.max_field_bytes', default_max)
        max_bytes = int(raw_max) if str(raw_max).strip() != '' else int(default_max)

        raw_drop = config.get('schemingdcat.metadata_extraction.drop_fields', None)
        if raw_drop is None:
            drop_fields = set(default_drop)
        else:
            raw_drop = str(raw_drop).strip()
            if raw_drop.lower() in ('none', 'false', '0'):
                drop_fields = set()
            elif raw_drop == '':
                drop_fields = set(default_drop)
            else:
                drop_fields = {f.strip() for f in raw_drop.replace(',', ' ').split() if f.strip()}
        return max_bytes, drop_fields
    except Exception:
        from ckanext.schemingdcat import config as sdct_config
        return getattr(sdct_config, 'metadata_extraction_default_max_field_bytes', 50000), set(
            getattr(sdct_config, 'metadata_extraction_default_drop_fields', [])
        )


def _prune_metadata_fields(metadata, log_ref=None):
    """
    Drop oversized metadata fields to avoid huge resource extras.
    """
    if not metadata:
        return metadata

    max_bytes, drop_fields = _metadata_extraction_limits()
    if not max_bytes or max_bytes <= 0:
        return metadata

    pruned = {}
    dropped = []
    for key, value in metadata.items():
        if key in drop_fields:
            dropped.append(f"{key}(drop_fields)")
            continue
        try:
            size = len(json.dumps(value, ensure_ascii=True, default=str))
        except Exception:
            size = len(str(value))
        if size > max_bytes:
            dropped.append(f"{key}({size})")
            continue
        pruned[key] = value

    if dropped:
        _job_log('warning', f"Skipping oversized metadata fields: {dropped}", log_ref or log)
    return pruned


def _ensure_valid_geometry(geom, log_ref=None):
    """Return a valid GeoJSON geometry equivalent to ``geom``.

    If shapely confirms the input is already valid, it is returned
    untouched. If it is invalid we try ``shapely.validation.make_valid``
    first, then fall back to ``buffer(0)``. When neither helper produces
    a valid result (or shapely itself is unavailable) the original
    geometry is returned unchanged so we never silently destroy data.

    This protects ckanext-spatial's Solr indexing from self-intersecting
    polygons that arrived from earlier extraction passes or hand-edited
    package extras.
    """
    if not isinstance(geom, dict):
        return geom
    try:
        from shapely.geometry import shape as shapely_shape, mapping as shapely_mapping
    except Exception:
        return geom

    try:
        shp = shapely_shape(geom)
    except Exception as parse_err:
        if log_ref is not None:
            _job_log('warning',
                     f"Could not parse geometry for validation: {parse_err}",
                     log_ref)
        return geom

    if shp.is_valid:
        return geom

    cleaned = None
    try:
        from shapely.validation import make_valid
        cleaned = make_valid(shp)
    except Exception:
        try:
            cleaned = shp.buffer(0)
        except Exception as buf_err:
            if log_ref is not None:
                _job_log('warning',
                         f"Geometry repair failed (buffer(0)): {buf_err}",
                         log_ref)
            return geom

    if cleaned is None or cleaned.is_empty or not cleaned.is_valid:
        if log_ref is not None:
            _job_log('warning',
                     "Geometry repair produced empty/invalid result; "
                     "leaving original geometry untouched",
                     log_ref)
        return geom

    try:
        repaired = shapely_mapping(cleaned)
    except Exception as map_err:
        if log_ref is not None:
            _job_log('warning',
                     f"Could not serialise repaired geometry: {map_err}",
                     log_ref)
        return geom

    if log_ref is not None:
        _job_log('info',
                 f"Repaired invalid geometry (input type={geom.get('type')}, "
                 f"output type={repaired.get('type')})",
                 log_ref)
    return repaired


def _merge_geojson_geometries(existing_geojson, new_geojson):
    """
    Merge two GeoJSON geometries into a single GeometryCollection or MultiPolygon.
    
    This function combines spatial extents from multiple resources to represent
    the full geographic coverage of a dataset. Each resource's bounding box 
    becomes a separate polygon in the resulting MultiPolygon.
    
    Args:
        existing_geojson: Existing GeoJSON geometry (dict or string)
        new_geojson: New GeoJSON geometry to merge (dict or string)
        
    Returns:
        dict: Merged GeoJSON geometry
    """
    # Parse strings to dicts if needed
    if isinstance(existing_geojson, str):
        try:
            existing_geojson = json.loads(existing_geojson)
        except (json.JSONDecodeError, TypeError):
            return new_geojson if isinstance(new_geojson, dict) else None
    
    if isinstance(new_geojson, str):
        try:
            new_geojson = json.loads(new_geojson)
        except (json.JSONDecodeError, TypeError):
            return existing_geojson
    
    if not existing_geojson:
        return new_geojson
    if not new_geojson:
        return existing_geojson
    
    # Extract geometries from both
    def get_geometries(geom):
        """Extract individual geometries from a GeoJSON object."""
        if not geom or not isinstance(geom, dict):
            return []
        
        geom_type = geom.get('type', '')
        
        if geom_type == 'GeometryCollection':
            return list(geom.get('geometries', []))
        elif geom_type == 'MultiPolygon':
            # Extract each polygon from MultiPolygon as separate geometry
            coords = geom.get('coordinates', [])
            return [{'type': 'Polygon', 'coordinates': c} for c in coords]
        elif geom_type in ('Polygon', 'Point', 'MultiPoint', 
                          'LineString', 'MultiLineString'):
            return [geom]
        elif geom_type == 'Feature':
            inner_geom = geom.get('geometry')
            return get_geometries(inner_geom) if inner_geom else []
        elif geom_type == 'FeatureCollection':
            result = []
            for feature in geom.get('features', []):
                result.extend(get_geometries(feature))
            return result
        else:
            return []
    
    def geometry_key(geom):
        """Create a hashable key for a geometry to detect duplicates."""
        if not geom or not isinstance(geom, dict):
            return None
        return json.dumps(geom, sort_keys=True)
    
    existing_geoms = get_geometries(existing_geojson)
    new_geoms = get_geometries(new_geojson)
    
    # Track existing geometries to avoid duplicates
    existing_keys = {geometry_key(g) for g in existing_geoms}
    
    # Add only new geometries that don't already exist
    unique_new_geoms = [g for g in new_geoms if geometry_key(g) not in existing_keys]
    
    if not unique_new_geoms:
        # No new geometries to add — but the existing one may be invalid
        # (e.g. a self-intersecting polygon left by an earlier extraction
        # pass). Repair it so the next reindex stops failing.
        return _ensure_valid_geometry(existing_geojson, log)
    
    # Combine all geometries
    all_geoms = existing_geoms + unique_new_geoms
    
    if not all_geoms:
        return new_geojson or existing_geojson
    
    if len(all_geoms) == 1:
        return _ensure_valid_geometry(all_geoms[0], log)

    # Check if all are Polygons - then create MultiPolygon
    all_polygons = all(g.get('type') == 'Polygon' for g in all_geoms)
    if all_polygons:
        # Combine into MultiPolygon
        coordinates = [g.get('coordinates', []) for g in all_geoms]
        return _ensure_valid_geometry(
            {'type': 'MultiPolygon', 'coordinates': coordinates},
            log,
        )

    # Otherwise create GeometryCollection
    return _ensure_valid_geometry(
        {'type': 'GeometryCollection', 'geometries': all_geoms},
        log,
    )



def _get_authenticated_download_url(resource_id, resource_url, log_ref=None):
    """
    Get an authenticated download URL for a resource.
    
    For cloud storage (Azure/AWS), generates a secure URL with SAS token.
    For local storage or as fallback, returns None (caller should use API token).
    
    Args:
        resource_id: The resource ID
        resource_url: The original resource URL
        log_ref: Logger reference
        
    Returns:
        tuple: (authenticated_url, api_key) - one will be None
    """
    if log_ref is None:
        log_ref = log
        
    try:
        # Try to use cloud storage secure URL
        try:
            from ckanext.cloudstorage.storage import ResourceCloudStorage
            import ckan.model as model
            from ckan.logic import get_action
            
            # Get resource details
            admin_user = model.Session.query(model.User).filter_by(sysadmin=True).first()
            context = {
                'model': model,
                'session': model.Session,
                'user': admin_user.name if admin_user else 'default',
                'ignore_auth': True
            }
            
            resource = get_action('resource_show')(context, {'id': resource_id})
            
            # Check if this is a cloud storage resource (has url pointing to cloud or url_type is upload)
            if resource.get('url_type') == 'upload' or '/download/' in resource.get('url', ''):
                # Get filename from URL
                filename = resource.get('url', '').rsplit('/', 1)[-1] if resource.get('url') else None
                
                if filename:
                    # Create storage instance and get secure URL using get_url_from_filename
                    storage = ResourceCloudStorage({})
                    
                    if storage.can_use_advanced_azure or storage.can_use_advanced_aws:
                        # Use get_url_from_filename which generates SAS token URLs
                        secure_url = storage.get_url_from_filename(resource_id, filename)
                        if secure_url:
                            _job_log('info', f"Got secure cloud storage URL for resource {resource_id}", log_ref)
                            return (secure_url, None)
                            
        except ImportError:
            _job_log('debug', "CloudStorage not available, will use API token fallback", log_ref)
        except Exception as e:
            _job_log('debug', f"Could not get cloud storage URL: {e}", log_ref)
        
        # Fallback: Generate a new API token for authenticated download
        try:
            import ckan.model as model
            from ckan.lib.api_token import encode as encode_api_token
            from ckan.lib.api_token import _get_secret
            
            # Get a sysadmin user for API access
            admin_user = model.Session.query(model.User).filter_by(sysadmin=True).first()
            if admin_user:
                # Generate a proper JWT API token for the sysadmin user
                import jwt
                from datetime import datetime, timedelta
                
                secret = _get_secret(encode=True)
                payload = {
                    'jti': str(admin_user.id) + '_metadata_extraction',
                    'iat': datetime.utcnow(),
                    'exp': datetime.utcnow() + timedelta(hours=1),
                    'sub': admin_user.id
                }
                api_token = jwt.encode(payload, secret, algorithm='HS256')
                _job_log('info', f"Generated JWT API token for authenticated download of resource {resource_id}", log_ref)
                return (None, api_token)
                    
        except Exception as e:
            _job_log('debug', f"Could not generate API token: {e}", log_ref)
            
    except Exception as e:
        _job_log('warning', f"Error getting authenticated download URL: {e}", log_ref)
    
    return (None, None)


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
    except Exception:
        pass
    # Always also print to stderr for worker visibility
    print(f"[METADATA JOB] [{level.upper()}] {msg}", file=sys.stderr)
    sys.stderr.flush()


_RESOURCE_NATIVE_COLUMNS = {
    'url', 'description', 'format', 'hash', 'mimetype', 'mimetype_inner',
    'cache_url', 'size', 'last_modified', 'cache_last_updated',
    'url_type', 'name', 'resource_type',
}


def _apply_resource_metadata_direct(resource_id, fields, log_ref=None):
    """
    Write metadata fields straight to the resource (native columns + extras)
    via SQLAlchemy and reindex the parent package.

    This bypasses CKAN's ``resource_patch`` → ``resource_update`` →
    ``package_update`` chain. That chain validates the *whole* package
    against the dataset schema; under some worker-context conditions the
    fluent fields (e.g. ``title_translated``) are dropped during this
    round-trip and the dataset's title and extras get wiped. The metadata
    extraction job has no business touching package-level fields, so we
    write the resource fields directly and skip the chain entirely.

    Args:
        resource_id: target resource ID
        fields: dict of field_name -> value (already JSON-serialised where needed)
        log_ref: logger to use (defaults to module log)

    Returns:
        True on success, False otherwise.
    """
    if log_ref is None:
        log_ref = log
    if not fields:
        return True

    import ckan.model as model
    from ckan.lib import search as ckan_search

    resource = model.Resource.get(resource_id)
    if resource is None:
        _job_log('warning', f"[direct-update] resource {resource_id} not found", log_ref)
        return False

    extras = dict(resource.extras or {})
    native_changed = False

    for key, value in fields.items():
        if value is None or value == '':
            continue
        if key == 'size':
            try:
                resource.size = int(value)
                native_changed = True
            except (TypeError, ValueError):
                # Not a clean integer — keep as extra so we don't lose info.
                extras[key] = value
            continue
        if key in _RESOURCE_NATIVE_COLUMNS:
            setattr(resource, key, value)
            native_changed = True
            continue
        extras[key] = value

    resource.extras = extras
    flag_modified(resource, 'extras')
    if native_changed:
        # Touch metadata_modified by setting it explicitly on the package
        # so /dataset views reflect the change.
        pass

    try:
        model.Session.commit()
    except Exception as commit_err:
        _job_log('error', f"[direct-update] commit failed for {resource_id}: {commit_err}", log_ref)
        try:
            model.Session.rollback()
        except Exception:
            pass
        return False

    # Reindex parent package so search picks up any new resource extras.
    try:
        package_id = resource.package_id
        if package_id:
            ckan_search.rebuild(package_id)
    except Exception as reindex_err:
        _job_log('warning', f"[direct-update] reindex failed for {resource_id}: {reindex_err}", log_ref)

    return True


@contextmanager
def _maybe_push_flask_request_context(log_ref=None):
    """
    Push a Flask request context if the current execution has none.

    Some CKAN extensions call ``flash_*`` helpers from dataset update hooks.
    Background jobs and worker threads usually run without an active request,
    which raises ``RuntimeError: Working outside of request context``.
    """
    if log_ref is None:
        log_ref = log

    pushed_context = None
    has_request = False

    try:
        from flask import has_request_context  # type: ignore
        has_request = has_request_context()
    except Exception:
        has_request = False

    if not has_request:
        try:
            from ckan.lib.helpers import _get_auto_flask_context
            auto_context = _get_auto_flask_context()
            if auto_context is not None:
                # Reusing a single shared context object is not thread-safe.
                pushed_context = auto_context.copy() if hasattr(auto_context, 'copy') else auto_context
                pushed_context.push()
        except Exception as e:
            try:
                log_ref.debug(f"Could not push Flask request context: {e}")
            except Exception:
                pass

    try:
        yield
    finally:
        if pushed_context is not None:
            try:
                pushed_context.pop()
            except Exception as e:
                try:
                    log_ref.debug(f"Could not pop Flask request context: {e}")
                except Exception:
                    pass


def _add_member_state_to_package(package_id, member_state_uri, context, log_ref, spatial_extent=None):
    """
    Add a member state (country group) to a package based on the detected spatial extent.
    
    Args:
        package_id: The ID of the package to update
        member_state_uri: The URI of the detected member state (e.g., 'http://publications.europa.eu/resource/authority/country/ZWE')
        context: CKAN context for API calls
        log_ref: Logger reference
        spatial_extent: Optional GeoJSON geometry to set as the package's spatial field
    """
    # Delegate to the plural version with a single-item list
    return _add_member_states_to_package(package_id, [member_state_uri], context, log_ref, spatial_extent=spatial_extent)


def _add_member_states_to_package(package_id, member_state_uris, context, log_ref, spatial_extent=None):
    """
    Add multiple member states (country groups) to a package based on the detected spatial extent.
    Also updates the package's spatial (bounding box) and spatial_uri fields if they are empty
    and the configuration option schemingdcat.spatial.auto_fill_dataset is enabled (default: True).
    
    Args:
        package_id: The ID of the package to update
        member_state_uris: List of URIs of detected member states
        context: CKAN context for API calls
        log_ref: Logger reference
        spatial_extent: Optional GeoJSON geometry to set as the package's spatial field
    """
    from ckan.logic import get_action
    import ckan.model as model
    import ckan.plugins.toolkit as toolkit
    
    # Check if spatial auto-fill is enabled (default: True)
    auto_fill_spatial = toolkit.asbool(
        toolkit.config.get('schemingdcat.spatial.auto_fill_dataset', True)
    )
    
    if not member_state_uris:
        return False
    
    try:
        from ckanext.schemingdcat import helpers as sd_helpers
        
        # Resolve all URIs to group names
        resolved_groups = []
        for member_state_uri in member_state_uris:
            _job_log('info', f"Looking up group for member state URI: {member_state_uri}", log_ref)
            
            member_state_name = None
            
            # Try to get the group name using the dedicated helper
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
            
            if member_state_name:
                resolved_groups.append(member_state_name)
            else:
                _job_log('warning', f"No group found for member state URI: {member_state_uri}", log_ref)
        
        if not resolved_groups:
            _job_log('warning', f"No groups could be resolved from member state URIs", log_ref)
            return False
        
        # Get current package to check existing groups and spatial fields
        package_show_action = get_action('package_show')
        package_data = package_show_action(context, {'id': package_id})
        
        existing_groups = package_data.get('groups', [])
        existing_group_names = {g.get('name') for g in existing_groups}
        
        # Filter out groups that already exist
        new_group_names = [g for g in resolved_groups if g not in existing_group_names]
        
        # Prepare patch data
        patch_data = {'id': package_id}
        has_updates = False
        
        # Add new groups if any
        if new_group_names:
            all_groups = list(existing_groups)
            for group_name in new_group_names:
                all_groups.append({'name': group_name})
            patch_data['groups'] = [{'name': g.get('name')} for g in all_groups]
            has_updates = True
            _job_log('info', f"Will add {len(new_group_names)} groups to package {package_id}: {new_group_names}", log_ref)
        
        # Update spatial field (bounding box) - merge with existing if present
        current_spatial = package_data.get('spatial', '')
        if auto_fill_spatial and spatial_extent:
            if current_spatial:
                # Merge with existing spatial extent
                _job_log('info', f"Package {package_id} has existing spatial, will merge with new extent", log_ref)
                merged_spatial = _merge_geojson_geometries(current_spatial, spatial_extent)
                if merged_spatial:
                    spatial_str = json.dumps(merged_spatial) if isinstance(merged_spatial, dict) else str(merged_spatial)
                    # Only update if the merged result is different from current
                    current_spatial_normalized = json.dumps(json.loads(current_spatial)) if current_spatial else ''
                    if spatial_str != current_spatial_normalized:
                        patch_data['spatial'] = spatial_str
                        has_updates = True
                        _job_log('info', f"Will merge spatial field for package {package_id}", log_ref)
                    else:
                        _job_log('info', f"Merged spatial is same as existing, no update needed", log_ref)
            else:
                # Set new spatial extent
                if isinstance(spatial_extent, dict):
                    spatial_str = json.dumps(spatial_extent)
                else:
                    spatial_str = str(spatial_extent)
                patch_data['spatial'] = spatial_str
                has_updates = True
                _job_log('info', f"Will set spatial field for package {package_id}", log_ref)
        elif not auto_fill_spatial:
            _job_log('info', f"Spatial auto-fill is disabled (schemingdcat.spatial.auto_fill_dataset=False)", log_ref)
        
        # Update spatial_uri field - add new URIs if not already present
        current_spatial_uri = package_data.get('spatial_uri', '')
        if auto_fill_spatial and member_state_uris:
            # Parse existing spatial_uri (could be a single URI, comma-separated list, or actual list)
            existing_uris = set()
            if current_spatial_uri:
                # Handle list, string with commas, or single string
                if isinstance(current_spatial_uri, list):
                    existing_uris = {uri.strip() if isinstance(uri, str) else str(uri) for uri in current_spatial_uri}
                elif isinstance(current_spatial_uri, str):
                    if ',' in current_spatial_uri:
                        existing_uris = {uri.strip() for uri in current_spatial_uri.split(',')}
                    else:
                        existing_uris = {current_spatial_uri.strip()}
                else:
                    existing_uris = {str(current_spatial_uri)}
            
            # Find new URIs that are not already in the list
            new_uris = [uri for uri in member_state_uris if uri not in existing_uris]
            
            if new_uris:
                # Combine existing and new URIs
                all_uris = list(existing_uris) + new_uris
                # Use the first URI (best match) as the primary value
                # For schemas that expect a single value, use the first one
                # For schemas that support multiple, they can parse the full list
                patch_data['spatial_uri'] = all_uris[0] if len(all_uris) == 1 else all_uris
                has_updates = True
                _job_log('info', f"Will add spatial_uri for package {package_id}: {new_uris}", log_ref)
            else:
                _job_log('info', f"All detected member states already in spatial_uri for package {package_id}", log_ref)
        
        # Only update if there are changes to make
        if not has_updates:
            _job_log('info', f"No updates needed for package {package_id}", log_ref)
            return True

        # Apply the changes WITHOUT going through package_patch. From the rq
        # worker context, package_patch's internal package_update round-trip
        # silently drops the dataset's fluent fields (title_translated,
        # notes_translated, …) and wipes package_extra. Doing direct DB
        # updates for groups + spatial fields keeps the rest of the dataset
        # intact, and we still reindex Solr at the end.
        _apply_member_state_updates_direct(
            package_id, patch_data, context, log_ref
        )
        _job_log('info', f"Successfully updated package {package_id} with member states and spatial info (direct)", log_ref)

        return True

    except Exception as e:
        _job_log('error', f"Error adding member states to package: {e}", log_ref)
        return False


def _apply_member_state_updates_direct(package_id, patch_data, context, log_ref=None):
    """
    Apply the member-state / spatial updates from
    ``_add_member_states_to_package`` directly via SQLAlchemy.

    Bypasses ``package_patch`` entirely so we never touch the dataset
    schema validation chain that, under worker-context conditions, drops
    fluent fields (title_translated, notes_translated, …) and clears
    other package extras.

    Args:
        package_id: target package
        patch_data: dict with optional 'groups' (list of {'name': ...}),
                    'spatial' (str), 'spatial_uri' (str | list)
        context: CKAN context (used to derive site user for member_create)
        log_ref: logger
    """
    if log_ref is None:
        log_ref = log

    import ckan.model as model
    from ckan.lib import search as ckan_search
    import ckan.plugins.toolkit as toolkit

    pkg = model.Package.get(package_id)
    if pkg is None:
        _job_log('warning', f"[direct-pkg-update] package {package_id} not found", log_ref)
        return False

    # 1) Group memberships — use ``member_create`` so authz / IGroupController
    #    hooks fire, but NOT package_update.
    desired_group_names = [
        g.get('name') for g in patch_data.get('groups', [])
        if isinstance(g, dict) and g.get('name')
    ]
    if desired_group_names:
        try:
            site_user = toolkit.get_action('get_site_user')(
                {'ignore_auth': True}, {}
            )
            member_ctx = {
                'ignore_auth': True,
                'user': site_user['name'],
                'model': model,
                'session': model.Session,
            }
        except Exception as err:
            _job_log('warning', f"[direct-pkg-update] could not resolve site user: {err}", log_ref)
            site_user = None
            member_ctx = {'ignore_auth': True, 'user': '', 'model': model, 'session': model.Session}

        existing = {g.name for g in pkg.get_groups()}
        for name in desired_group_names:
            if name in existing:
                continue
            group = model.Group.get(name)
            if not group:
                _job_log('warning', f"[direct-pkg-update] group not found: {name}", log_ref)
                continue
            try:
                toolkit.get_action('member_create')(
                    member_ctx,
                    {'id': group.id, 'object': package_id,
                     'object_type': 'package', 'capacity': 'public'},
                )
            except Exception as mem_err:
                _job_log('warning', f"[direct-pkg-update] could not add {name}: {mem_err}", log_ref)

    # 2) spatial / spatial_uri — write straight into ``package_extra``.
    extra_writes = {}
    if 'spatial' in patch_data and patch_data['spatial']:
        extra_writes['spatial'] = patch_data['spatial']
    if 'spatial_uri' in patch_data and patch_data['spatial_uri']:
        v = patch_data['spatial_uri']
        if isinstance(v, list):
            v = json.dumps(v)
        extra_writes['spatial_uri'] = v

    if extra_writes:
        for key, value in extra_writes.items():
            existing_extra = (
                model.Session.query(model.PackageExtra)
                .filter_by(package_id=package_id, key=key, state='active')
                .first()
            )
            if existing_extra:
                existing_extra.value = value
            else:
                new_extra = model.PackageExtra(
                    package_id=package_id, key=key, value=value, state='active'
                )
                model.Session.add(new_extra)

    try:
        model.Session.commit()
    except Exception as commit_err:
        _job_log('error', f"[direct-pkg-update] commit failed: {commit_err}", log_ref)
        try:
            model.Session.rollback()
        except Exception:
            pass
        return False

    # 3) If we set ``spatial``, run ckanext-spatial's bbox sync manually so
    #    the spatial geometry index stays in sync (we skipped the hook by
    #    not going through package_update).
    if 'spatial' in extra_writes:
        try:
            from ckanext.spatial.plugin import SpatialMetadata
            SpatialMetadata().check_spatial_extra(
                {'id': package_id, 'spatial': extra_writes['spatial']},
                update=True,
            )
        except Exception as spatial_err:
            _job_log('warning', f"[direct-pkg-update] spatial sync skipped: {spatial_err}", log_ref)

    # 4) Reindex so Solr/the search UI reflects the new groups / extras.
    try:
        ckan_search.rebuild(package_id)
    except Exception as reindex_err:
        _job_log('warning', f"[direct-pkg-update] reindex failed: {reindex_err}", log_ref)

    return True


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
    except Exception:
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
            except Exception:
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
            analyzer = FileAnalyzer()
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
                
                # Get authenticated download URL for private resources
                download_url = resource_url
                auth_header = None
                
                try:
                    secure_url, api_key = _get_authenticated_download_url(resource_id, resource_url, log)
                    if secure_url:
                        download_url = secure_url
                        _job_log('info', f"Using secure cloud storage URL for download", log)
                    elif api_key:
                        auth_header = api_key
                        _job_log('info', f"Using API key authentication for download", log)
                except Exception as auth_error:
                    _job_log('warning', f"Could not get authenticated URL, trying public access: {auth_error}", log)
                
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
                    try:
                        _job_log('info', f"Starting download from: {download_url[:100]}...", log)
                        
                        # Download with retries
                        max_retries = 3
                        backoff = 2
                        last_error = None
                        
                        for attempt in range(max_retries):
                            try:
                                headers = {
                                    'User-Agent': 'CKAN SchemingDCAT Metadata Extractor/1.0',
                                    'Accept': '*/*'
                                }
                                if auth_header:
                                    headers['Authorization'] = auth_header
                                    
                                req = urllib.request.Request(download_url, headers=headers)
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
                                metadata = _prune_metadata_fields(metadata, log)
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

            # Detect member states (countries) from spatial extent
            detected_member_uris = []
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
                    # Use plural detection to get all overlapping countries
                    detected_member_uris = sd_helpers.schemingdcat_detect_member_states(extent_geojson)
                    
                    if detected_member_uris:
                        _job_log('info', f"Detected {len(detected_member_uris)} member states for resource {resource_id}: {detected_member_uris}", log)
                    else:
                        _job_log('info', f"No member states detected for resource {resource_id} (detection returned empty)", log)
                else:
                    _job_log('info', f"No spatial_extent in metadata for resource {resource_id}, skipping member state detection", log)
            except Exception as e:
                _job_log('warning', f"Could not detect member states from extent for resource {resource_id}: {e}", log)
                log.warning(f"Could not detect member states from extent for resource {resource_id}: {e}", exc_info=True)
            
            try:
                # Ensure we have a valid database session
                try:
                    model.Session.close()
                    model.Session.remove()
                except Exception:
                    pass
                
                # Get fresh context
                admin_user = model.Session.query(model.User).filter_by(sysadmin=True).first()
                context = {
                    'model': model,
                    'session': model.Session,
                    'user': admin_user.name if admin_user else 'default',
                    'ignore_auth': True,
                    'defer_commit': False,
                    '_schemingdcat_metadata_job': True,  # Prevent re-triggering extraction
                    '_skip_doi_update': True,  # Prevent DOI network calls on internal metadata patches
                }
                
                # NOTE: we deliberately do NOT call ``resource_patch`` here.
                # That action triggers a full ``package_update`` round-trip
                # against the dataset schema. From the rq worker context that
                # round-trip drops the package's fluent fields
                # (``title_translated`` etc.) and wipes ``package_extra`` —
                # see _apply_resource_metadata_direct for the workaround.

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
                crs_value = metadata.get('spatial_crs') or metadata.get('crs')
                if crs_value:
                    metadata_fields['spatial_crs'] = crs_value
                
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

                # Add spatial resolution (raster)
                if metadata.get('spatial_resolution'):
                    metadata_fields['spatial_resolution'] = metadata['spatial_resolution']
                
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
                file_size_bytes = metadata.get('file_size_bytes') or metadata.get('file_size')
                if file_size_bytes:
                    metadata_fields['file_size_bytes'] = str(file_size_bytes)
                    metadata_fields['size'] = str(file_size_bytes)
                
                _job_log('info', f"Prepared metadata fields for resource update: {list(metadata_fields.keys())}", log)
                
                # Filter out None values and prepare patch data
                fields_to_update = [k for k, v in metadata_fields.items() if v is not None and v != '']
                
                if fields_to_update:
                    # Build a clean dict of resource fields, JSON-serialising
                    # any complex values so they round-trip through the
                    # ``resource.extras`` JSON column unchanged.
                    safe_fields = {}
                    for field in fields_to_update:
                        v = metadata_fields[field]
                        if isinstance(v, (dict, list)):
                            try:
                                safe_fields[field] = json.dumps(v)
                            except Exception:
                                safe_fields[field] = str(v)
                        else:
                            safe_fields[field] = v

                    _job_log('info', f"Updating resource {resource_id} with {len(safe_fields)} metadata fields (direct)", log)

                    success = _apply_resource_metadata_direct(resource_id, safe_fields, log)
                    if not success:
                        return False
                    _job_log('info', f"Successfully updated metadata for resource {resource_id}. Updated {len(safe_fields)} fields.", log)

                    # Now add member states to the package if detected
                    if detected_member_uris and package_id:
                        try:
                            _job_log('info', f"Adding {len(detected_member_uris)} member states to package {package_id}", log)
                            extent_for_package = metadata.get('spatial_extent')
                            if isinstance(extent_for_package, str):
                                try:
                                    extent_for_package = json.loads(extent_for_package)
                                except (json.JSONDecodeError, ValueError, TypeError):
                                    pass
                            _add_member_states_to_package(package_id, detected_member_uris, context, log, spatial_extent=extent_for_package)
                        except Exception as group_error:
                            _job_log('warning', f"Could not add member states to package: {group_error}", log)

                    return True
                else:
                    _job_log('info', f"No meaningful metadata fields to update for resource {resource_id}", log)
                    # Even if no resource metadata, still add member states if detected
                    if detected_member_uris and package_id:
                        try:
                            _job_log('info', f"Adding {len(detected_member_uris)} member states to package {package_id}", log)
                            # Pass the spatial_extent to also update the package's spatial field
                            extent_for_package = metadata.get('spatial_extent')
                            if isinstance(extent_for_package, str):
                                try:
                                    extent_for_package = json.loads(extent_for_package)
                                except (json.JSONDecodeError, ValueError, TypeError):
                                    pass
                            _add_member_states_to_package(package_id, detected_member_uris, context, log, spatial_extent=extent_for_package)
                        except Exception as group_error:
                            _job_log('warning', f"Could not add member states to package: {group_error}", log)
                    return True
                
            except Exception as e:
                log.error(f"Error preparing update for resource {resource_id}: {e}", exc_info=True)
                try:
                    model.Session.rollback()
                except Exception:
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
        except Exception:
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
