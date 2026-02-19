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
from urllib.parse import parse_qs, urlparse

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
    plugins.implements(plugins.ITranslation)
    plugins.implements(plugins.IValidators)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IClick)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.IMiddleware, inherit=True)

    # IMiddleware
    def make_middleware(self, app, config):
        """
        Register after_request handler to save Beaker sessions.
        
        This fixes CSRF token issues in multi-pod Kubernetes deployments.
        The handler runs inside Flask, where Beaker session is available.
        """
        from flask import request, session as flask_session
        from flask_wtf.csrf import CSRFError
        from flask_login import current_user
        from ckan.common import config
        import hashlib
        
        # Log beaker session params for debugging
        beaker_params = {k: v for k, v in config.items() if k.startswith('beaker.session')}
        log.info(f"[CSRF FIX] Beaker session params: {beaker_params}")
        
        # Fix WTF_CSRF_FIELD_NAME - ConfigParser converts to lowercase but Flask-WTF needs uppercase
        csrf_field = (
            app.config.get('WTF_CSRF_FIELD_NAME') or
            config.get('WTF_CSRF_FIELD_NAME') or
            config.get('wtf_csrf_field_name') or
            os.environ.get('WTF_CSRF_FIELD_NAME') or
            os.environ.get('CKAN___WTF_CSRF_FIELD_NAME') or
            os.environ.get('CKAN__WTF_CSRF_FIELD_NAME') or
            '_csrf_token'
        )
        app.config['WTF_CSRF_FIELD_NAME'] = csrf_field
        log.info(f"[CSRF FIX] Set WTF_CSRF_FIELD_NAME={csrf_field}")

        # Log CSRF failures with useful request/session context
        if not getattr(app, '_schemingdcat_csrf_error_handler', False):
            @app.errorhandler(CSRFError)
            def _schemingdcat_csrf_error(err):
                try:
                    beaker_session = request.environ.get('beaker.session')
                    session_id = getattr(beaker_session, 'id', None)
                    field_name = app.config.get('WTF_CSRF_FIELD_NAME', '_csrf_token')
                    session_token = None
                    session_token_default = None
                    if beaker_session is not None:
                        session_token = beaker_session.get(field_name)
                        session_token_default = beaker_session.get('_csrf_token')

                    header_token = (request.headers.get('X-CSRFToken') or
                                    request.headers.get('X-CSRF-Token'))
                    form_token = request.form.get(field_name)

                    def _sig(val):
                        if not val:
                            return None
                        return hashlib.sha1(val.encode('utf-8')).hexdigest()[:8]

                    cookie_key = config.get('beaker.session.key', 'ckan')
                    cookie_val = request.cookies.get(cookie_key)
                    raw_cookie = request.headers.get('Cookie', '')
                    cookie_hashes = []
                    if raw_cookie:
                        parts = [p.strip() for p in raw_cookie.split(';') if p.strip()]
                        for p in parts:
                            if p.startswith(cookie_key + '='):
                                val = p.split('=', 1)[1]
                                cookie_hashes.append(_sig(val))

                    log.warning(
                        "[CSRF ERROR] %s %s status=400 "
                        "user=%s session_id=%s field_name=%s "
                        "session_has_token=%s session_has__csrf_token=%s "
                        "header_token=%s form_token=%s session_token=%s "
                        "cookie_present=%s cookie_len=%s cookie_hashes=%s "
                        "referer=%s host=%s xff=%s remote=%s err=%s",
                        request.method,
                        request.path,
                        getattr(current_user, 'name', None) if current_user else None,
                        session_id,
                        field_name,
                        bool(session_token),
                        bool(session_token_default),
                        _sig(header_token),
                        _sig(form_token),
                        _sig(session_token),
                        bool(cookie_val),
                        len(cookie_val) if cookie_val else 0,
                        cookie_hashes,
                        request.headers.get('Referer'),
                        request.host,
                        request.headers.get('X-Forwarded-For'),
                        request.remote_addr,
                        str(err)
                    )
                except Exception as e:
                    log.warning(f"[CSRF ERROR] Failed to log CSRF details: {e}")
                
                # Return a user-friendly error page
                from flask import render_template_string
                return render_template_string('''
                    <!DOCTYPE html>
                    <html><head><title>Session Error</title></head>
                    <body>
                        <h1>Session Error</h1>
                        <p>Your session has expired or is invalid. Please refresh the page and try again.</p>
                        <p><a href="{{ request.path }}">Refresh and try again</a></p>
                    </body></html>
                '''), 400

            app._schemingdcat_csrf_error_handler = True
        
        # Fix CSRF token BEFORE Flask-WTF validates
        @app.before_request
        def fix_csrf_token_before_validation():
            """
            If this is a POST request and the session doesn't have a CSRF token,
            but the form has one, extract the token from the form and put it in
            the session so Flask-WTF validation will pass.
            """
            if request.method != 'POST':
                return
            
            # Only apply to dataset forms and other POST endpoints
            if '/dataset' not in request.path:
                return
            
            beaker_session = request.environ.get('beaker.session')
            if beaker_session is None:
                return
            
            field_name = app.config.get('WTF_CSRF_FIELD_NAME', '_csrf_token')
            session_token = beaker_session.get(field_name)
            form_token = request.form.get(field_name)
            
            # If session already has token, nothing to fix
            if session_token:
                return
            
            # If no form token, can't fix
            if not form_token:
                log.warning("[CSRF FIX] No form token found in POST request")
                return
            
            log.warning(
                "[CSRF FIX] Attempting to restore token. session_id=%s form_token_len=%s",
                getattr(beaker_session, 'id', None), len(form_token) if form_token else 0
            )
            
            # Extract the real token from the signed form token and put it in session
            try:
                from itsdangerous import URLSafeTimedSerializer, BadSignature
                
                # Get the secret key used by Flask-WTF
                secret_key = app.config.get('WTF_CSRF_SECRET_KEY', app.secret_key)
                
                # Deserialize the form token to get the actual token value
                s = URLSafeTimedSerializer(secret_key, salt='wtf-csrf-token')
                try:
                    # Try to load the token (with a generous time limit)
                    real_token = s.loads(form_token, max_age=86400)  # 24 hours
                    
                    # Put the real token in the session
                    beaker_session[field_name] = real_token
                    
                    # Force save the session immediately
                    internal_session = beaker_session._session()
                    if hasattr(internal_session, 'save'):
                        internal_session.save()
                    
                    log.warning(
                        "[CSRF FIX] Restored token from form to session. "
                        "session_id=%s token_hash=%s",
                        getattr(beaker_session, 'id', None),
                        hashlib.sha1(real_token.encode('utf-8')).hexdigest()[:8]
                    )
                except BadSignature as bs_err:
                    log.warning(
                        "[CSRF FIX] Could not deserialize form token - invalid signature. "
                        "session_id=%s error=%s",
                        getattr(beaker_session, 'id', None), str(bs_err)
                    )
            except Exception as e:
                import traceback
                log.warning(f"[CSRF FIX] Error restoring token: {e}\n{traceback.format_exc()}")
        
        @app.after_request
        def save_beaker_session(response):
            try:
                beaker_session = request.environ.get('beaker.session')
                if beaker_session is not None:
                    field_name = app.config.get('WTF_CSRF_FIELD_NAME', '_csrf_token')
                    session_id = getattr(beaker_session, 'id', None)
                    has_token = field_name in beaker_session
                    token_hash = None
                    if has_token:
                        token = beaker_session.get(field_name)
                        if token:
                            token_hash = hashlib.sha1(token.encode('utf-8')).hexdigest()[:8]
                    
                    # Log session state for /dataset/new requests (both GET and POST)
                    if '/dataset/new' in request.path:
                        # Get session params to check auto mode
                        session_params = beaker_session.__dict__.get('_params', {})
                        auto_mode = session_params.get('auto', False)
                        is_dirty = beaker_session.dirty()
                        internal = beaker_session._session() if beaker_session.__dict__.get('_sess') else None
                        is_new = getattr(internal, 'is_new', 'N/A')
                        
                        # Get cookie value to compare
                        cookie_key = session_params.get('key', 'ckan')
                        cookie_val = request.cookies.get(cookie_key)
                        cookie_session_id = cookie_val[-32:] if cookie_val and len(cookie_val) >= 32 else None
                        
                        log.warning(
                            "[CSRF DEBUG] %s %s session_id=%s cookie_sid=%s has_token=%s token_hash=%s status=%s "
                            "auto=%s dirty=%s is_new=%s",
                            request.method, request.path, session_id, cookie_session_id,
                            has_token, token_hash, response.status_code,
                            auto_mode, is_dirty, is_new
                        )
                    
                    # Only force save if session has CSRF token (to avoid race conditions)
                    # Other requests should let Beaker's persist() handle saving normally
                    if has_token:
                        # SessionObject.save() only marks _dirty=True but doesn't persist
                        # We need to call the internal Session's save() to write to Redis
                        beaker_session._dirty = True
                        
                        # Get the internal Session object and force immediate save
                        internal_session = beaker_session._session()
                        if internal_session is not None:
                            internal_session.save()
                            if '/dataset/new' in request.path:
                                log.warning("[CSRF DEBUG] Session saved to Redis: session_id=%s token_hash=%s", session_id, token_hash)
            except Exception as e:
                log.warning(f"[CSRF FIX] Error saving session: {e}")
            return response
        
        return app

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
    _RESOURCE_UPDATE_BACKFILL_FIELDS = frozenset({
        'contact_email',
        'dcat_type',
        'identifier',
        'language',
        'topic',
    })
    _DEFAULT_DCAT_TYPE = 'http://inspire.ec.europa.eu/metadata-codelist/ResourceType/dataset'
    _DEFAULT_LANGUAGE = 'http://publications.europa.eu/resource/authority/language/ENG'
    _DEFAULT_TOPIC = 'http://inspire.ec.europa.eu/metadata-codelist/TopicCategory/environment'
    _DEFAULT_CONTACT_EMAIL = 'noreply@ihp-wins.unesco.org'

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
        log.info("[_ensure_memberstate_groups] ENTRY")
        
        # Import helpers - if this fails, log and continue without spatial_uri resolution
        sd_helpers = None
        try:
            from ckanext.schemingdcat import helpers as sd_helpers
        except Exception as e:
            log.warning(f"[_ensure_memberstate_groups] Could not import helpers: {e}")

        # Log all keys to understand what's coming in
        all_keys = [str(k) for k in data_dict.keys()]
        log.info(f"[_ensure_memberstate_groups] all data_dict keys: {all_keys}")

        group_names = []

        existing_groups = data_dict.get('groups') or []
        log.info(f"[_ensure_memberstate_groups] existing_groups from data_dict: {existing_groups}")
        log.info(f"[_ensure_memberstate_groups] existing_groups type: {type(existing_groups)}")
        if isinstance(existing_groups, dict):
            existing_groups = [existing_groups]
        for g in existing_groups:
            log.info(f"[_ensure_memberstate_groups] processing group: {g} (type: {type(g)})")
            # Handle both dict format {'id': 'xxx', 'name': 'xxx'} and string format 'xxx'
            if isinstance(g, dict):
                name = g.get('name') or g.get('id')
            elif isinstance(g, str):
                name = g
            else:
                log.warning(f"[_ensure_memberstate_groups] Unexpected group format: {g}")
                continue
            log.info(f"[_ensure_memberstate_groups] extracted name/id: {name}")
            if name:
                group_names.append(name)

        log.info(f"[_ensure_memberstate_groups] group_names after existing_groups: {group_names}")

        for key, value in list(data_dict.items()):
            key_name = key
            if isinstance(key, tuple) and key:
                key_name = key[-1]
            if isinstance(key_name, str) and key_name.startswith('groups__') and key_name.endswith('__id'):
                log.info(f"[_ensure_memberstate_groups] found groups__ key: {key_name} = {value}")
                if value:
                    group_names.append(value)

        log.info(f"[_ensure_memberstate_groups] group_names after groups__X__id: {group_names}")

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
            if not uri or not sd_helpers:
                continue
            try:
                group_slug = sd_helpers.schemingdcat_find_member_state_group(uri, context)
                if group_slug:
                    group_names.append(group_slug)
            except Exception as e:
                log.info(f"Could not resolve member state group for {uri}: {e}")

        seen = set()
        unique_group_names = []
        for name in group_names:
            if not name or name in seen:
                continue
            seen.add(name)
            unique_group_names.append(name)

        log.info(f"[_ensure_memberstate_groups] unique_group_names final: {unique_group_names}")

        if unique_group_names:
            data_dict['groups'] = [{'name': n} for n in unique_group_names]
            log.info(f"[_ensure_memberstate_groups] set data_dict['groups'] to: {data_dict['groups']}")

        return data_dict

    def before_dataset_create(self, context, data_dict):
        log.info("[SchemingDCATPlugin.before_dataset_create] CALLED")
        return self._ensure_memberstate_groups(context, data_dict)

    def before_dataset_update(self, context, data_dict):
        log.info("[SchemingDCATPlugin.before_dataset_update] CALLED")
        return self._ensure_memberstate_groups(context, data_dict)

    @staticmethod
    def _is_missing_value(value):
        if value is None:
            return True
        if isinstance(value, str):
            return value.strip() == ''
        if isinstance(value, (list, tuple, dict, set)):
            return len(value) == 0
        return False

    def _missing_required_fields_from_validation_error(self, err):
        error_dict = getattr(err, 'error_dict', None) or {}
        missing_fields = set()
        for field in self._RESOURCE_UPDATE_BACKFILL_FIELDS:
            messages = error_dict.get(field)
            if not messages:
                continue
            if not isinstance(messages, (list, tuple, set)):
                messages = [messages]
            combined = ' '.join(str(m) for m in messages).lower()
            if 'missing value' in combined or 'required' in combined:
                missing_fields.add(field)
        return missing_fields

    def _read_package_for_resource_update(self, context, data_dict):
        resource_id = data_dict.get('id')
        if not resource_id:
            return None

        read_context = dict(context or {})
        read_context.pop('schema', None)

        resource_dict = toolkit.get_action('resource_show')(read_context, {'id': resource_id})
        package_id = (
            data_dict.get('package_id')
            or resource_dict.get('package_id')
        )
        if not package_id:
            return None

        return toolkit.get_action('package_show')(read_context, {'id': package_id})

    def _pick_dataset_value(self, package_dict, key):
        value = package_dict.get(key)
        if not self._is_missing_value(value):
            return value

        for extra in package_dict.get('extras', []):
            if extra.get('key') == key and not self._is_missing_value(extra.get('value')):
                return extra.get('value')
        return None

    def _build_missing_fields_patch(self, package_dict, missing_fields):
        package_id = package_dict.get('id')
        if not package_id:
            return None

        patch_data = {'id': package_id}

        if 'identifier' in missing_fields:
            patch_data['identifier'] = (
                self._pick_dataset_value(package_dict, 'identifier')
                or package_id
            )

        if 'dcat_type' in missing_fields:
            patch_data['dcat_type'] = (
                self._pick_dataset_value(package_dict, 'dcat_type')
                or toolkit.config.get('schemingdcat.default_dcat_type')
                or self._DEFAULT_DCAT_TYPE
            )

        if 'language' in missing_fields:
            patch_data['language'] = (
                self._pick_dataset_value(package_dict, 'language')
                or toolkit.config.get('schemingdcat.default_language')
                or self._DEFAULT_LANGUAGE
            )

        if 'topic' in missing_fields:
            patch_data['topic'] = (
                self._pick_dataset_value(package_dict, 'topic')
                or toolkit.config.get('schemingdcat.default_topic')
                or self._DEFAULT_TOPIC
            )

        if 'contact_email' in missing_fields:
            patch_data['contact_email'] = (
                self._pick_dataset_value(package_dict, 'contact_email')
                or package_dict.get('maintainer_email')
                or package_dict.get('author_email')
                or toolkit.config.get('schemingdcat.default_contact_email')
                or toolkit.config.get('ckanext.doi.email')
                or self._DEFAULT_CONTACT_EMAIL
            )

        return patch_data if len(patch_data) > 1 else None

    def _backfill_missing_dataset_fields_for_resource_update(self, context, data_dict, missing_fields):
        package_dict = self._read_package_for_resource_update(context, data_dict)
        if not package_dict:
            log.warning('[RESOURCE UPDATE] Could not resolve package for missing-field backfill')
            return False

        patch_data = self._build_missing_fields_patch(package_dict, missing_fields)
        if not patch_data:
            log.warning('[RESOURCE UPDATE] Could not build patch data for missing-field backfill')
            return False

        patch_context = dict(context or {})
        patch_context.pop('schema', None)
        patch_context['_skip_doi_update'] = True
        patch_context['_schemingdcat_metadata_job'] = True

        toolkit.get_action('package_patch')(patch_context, patch_data)
        log.warning(
            '[RESOURCE UPDATE] Auto-filled missing required dataset fields %s for package %s',
            sorted(missing_fields),
            patch_data['id'],
        )
        return True

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
            "package_search": self.package_search,
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
            self._normalize_pdf_resource_format(context, result)
        except Exception as e:
            log.warning(f"⚠️ [ACTION] Could not normalize PDF format after resource_create: {e}")
        try:
            self._disable_external_pdf_views(context, result)
        except Exception as e:
            log.warning(f"⚠️ [ACTION] Could not disable external PDF views after resource_create: {e}")
        try:
            self._prune_oversized_metadata_fields(context, result)
        except Exception as e:
            log.warning(f"⚠️ [ACTION] Could not prune oversized metadata fields after resource_create: {e}")
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
        try:
            result = next_action(context, data_dict)
        except toolkit.ValidationError as e:
            missing_fields = self._missing_required_fields_from_validation_error(e)
            if not missing_fields or (context or {}).get('_schemingdcat_backfill_attempted'):
                raise

            if not self._backfill_missing_dataset_fields_for_resource_update(context, data_dict, missing_fields):
                raise

            retry_context = dict(context or {})
            retry_context['_schemingdcat_backfill_attempted'] = True
            result = next_action(retry_context, data_dict)

        # Skip if this is a metadata job update (prevent infinite loop)
        if (context or {}).get('_schemingdcat_metadata_job'):
            log.debug(f"⏭️ [ACTION] Skipping extraction trigger - metadata job context")
            return result
        try:
            self._normalize_pdf_resource_format(context, result)
        except Exception as e:
            log.warning(f"⚠️ [ACTION] Could not normalize PDF format after resource_update: {e}")
        try:
            self._disable_external_pdf_views(context, result)
        except Exception as e:
            log.warning(f"⚠️ [ACTION] Could not disable external PDF views after resource_update: {e}")
        try:
            self._prune_oversized_metadata_fields(context, result)
        except Exception as e:
            log.warning(f"⚠️ [ACTION] Could not prune oversized metadata fields after resource_update: {e}")
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
        
        # Log the incoming groups data for debugging
        groups_before = data_dict.get('groups', 'NOT_PRESENT')
        log.info(f"[SchemingDCATPlugin.package_patch] groups BEFORE processing: {groups_before}")
        
        # Log any groups__X__id fields
        groups_fields = {k: v for k, v in data_dict.items() 
                        if isinstance(k, str) and k.startswith('groups__') and k.endswith('__id')}
        log.info(f"[SchemingDCATPlugin.package_patch] groups__X__id fields: {groups_fields}")
        
        # Process groups__X__id fields before the patch
        data_dict = self._ensure_memberstate_groups(context, data_dict)
        
        groups_after = data_dict.get('groups', 'NOT_PRESENT')
        log.info(f"[SchemingDCATPlugin.package_patch] groups AFTER processing: {groups_after}")
        
        return next_action(context, data_dict)

    @toolkit.chained_action
    def package_search(self, next_action, context, data_dict):
        """
        Chained action for package_search to prevent huge resource extras
        from bloating /dataset responses.
        """
        result = next_action(context, data_dict)
        try:
            if not self._metadata_prune_search_results_enabled():
                return result

            results = result.get('results') or []
            if not results:
                return result

            max_bytes = self._metadata_max_field_bytes()
            drop_fields = self._metadata_drop_fields()
            for pkg in results:
                resources = pkg.get('resources') or []
                for res in resources:
                    self._prune_resource_metadata_dict(res, max_bytes, drop_fields)
        except Exception as e:
            log.warning(f"⚠️ [SEARCH] Could not prune resource metadata in package_search: {e}")

        return result

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

    def _metadata_extraction_enabled(self):
        from ckan.common import config
        try:
            return toolkit.asbool(config.get('schemingdcat.metadata_extraction.enabled', True))
        except Exception:
            return True

    def _metadata_use_jobs_queue(self):
        from ckan.common import config
        try:
            return toolkit.asbool(config.get('schemingdcat.metadata_extraction.use_jobs_queue', True))
        except Exception:
            return True

    def _metadata_thread_fallback_enabled(self):
        from ckan.common import config
        try:
            return toolkit.asbool(config.get('schemingdcat.metadata_extraction.thread_fallback', False))
        except Exception:
            return False

    def _metadata_job_timeout(self):
        from ckan.common import config
        raw_timeout = config.get('schemingdcat.metadata_extraction.job_timeout', 600)
        try:
            timeout = int(raw_timeout)
            return timeout if timeout > 0 else 600
        except Exception:
            return 600

    def _metadata_max_field_bytes(self):
        from ckan.common import config
        try:
            default_max = getattr(sdct_config, 'metadata_extraction_default_max_field_bytes', 50000)
            raw_value = config.get('schemingdcat.metadata_extraction.max_field_bytes', default_max)
            return int(raw_value) if str(raw_value).strip() != '' else int(default_max)
        except Exception:
            return getattr(sdct_config, 'metadata_extraction_default_max_field_bytes', 50000)

    def _metadata_drop_fields(self):
        from ckan.common import config
        default_fields = getattr(sdct_config, 'metadata_extraction_default_drop_fields', [])
        try:
            raw_value = config.get('schemingdcat.metadata_extraction.drop_fields', None)
        except Exception:
            raw_value = None

        if raw_value is None:
            return set(default_fields)

        raw_value = str(raw_value).strip()
        if raw_value.lower() in ('none', 'false', '0'):
            return set()
        if raw_value == '':
            return set(default_fields)

        return {f.strip() for f in raw_value.replace(',', ' ').split() if f.strip()}

    def _metadata_prune_search_results_enabled(self):
        from ckan.common import config
        try:
            return toolkit.asbool(config.get('schemingdcat.metadata_extraction.prune_search_results', True))
        except Exception:
            return True

    def _prune_resource_metadata_dict(self, resource, max_bytes=None, drop_fields=None):
        if not resource:
            return resource

        if max_bytes is None:
            max_bytes = self._metadata_max_field_bytes()
        if drop_fields is None:
            drop_fields = self._metadata_drop_fields()

        for key in list(resource.keys()):
            if key in drop_fields:
                resource.pop(key, None)
                continue

            value = resource.get(key)
            if value is None:
                continue

            try:
                size = len(json.dumps(value, ensure_ascii=True, default=str))
            except Exception:
                size = len(str(value))

            if max_bytes and max_bytes > 0 and size > max_bytes:
                resource.pop(key, None)

        return resource

    def _prune_oversized_metadata_fields(self, context, resource):
        """
        Clear auto-generated metadata fields that exceed the configured size limit.
        This prevents huge blobs from bloating resource extras and slowing /dataset.
        """
        try:
            resource_id = resource.get('id')
            if not resource_id:
                return

            max_bytes = self._metadata_max_field_bytes()
            drop_fields = self._metadata_drop_fields()
            if (not max_bytes or max_bytes <= 0) and not drop_fields:
                return

            metadata_fields_to_check = set(drop_fields) | {
                'data_fields', 'data_statistics', 'data_domains',
                'geographic_coverage', 'administrative_boundaries',
                'compression_info', 'format_version', 'file_integrity',
                'content_type_detected', 'document_pages', 'spreadsheet_sheets',
                'text_content_info', 'file_size_bytes'
            }

            fields_to_clear = {}
            for field_name in metadata_fields_to_check:
                field_value = resource.get(field_name)
                if field_value is None:
                    continue
                if field_name in drop_fields:
                    fields_to_clear[field_name] = None
                    continue
                try:
                    size = len(json.dumps(field_value, ensure_ascii=True, default=str))
                except Exception:
                    size = len(str(field_value))
                if max_bytes and max_bytes > 0 and size > max_bytes:
                    fields_to_clear[field_name] = None

            if fields_to_clear:
                system_context = {
                    'model': context['model'],
                    'session': context['session'],
                    'ignore_auth': True,
                    'user': '',
                    'api_version': 3,
                    'defer_commit': False,
                    '_schemingdcat_metadata_job': True,
                    '_skip_doi_update': True,
                }

                patch_data = {'id': resource_id}
                patch_data.update(fields_to_clear)
                toolkit.get_action('resource_patch')(system_context, patch_data)

                log.warning(
                    f"[METADATA] Cleared oversized metadata fields for resource {resource_id}: "
                    f"{list(fields_to_clear.keys())}"
                )
        except Exception as e:
            log.warning(
                f"Error pruning oversized metadata fields for resource {resource.get('id', 'unknown')}: {e}"
            )

    def _trigger_metadata_extraction(self, resource):
        """
        Centralized trigger for metadata extraction that can be called from hooks or chained actions.
        """
        resource_id = resource.get('id', 'unknown')
        if not self._metadata_extraction_enabled():
            log.info(f"⏭️ [TRIGGER] Metadata extraction disabled by config for resource {resource_id}")
            return
        needs_extraction = resource.get('_needs_metadata_extraction') or self._should_extract_metadata(resource)

        if not needs_extraction:
            log.info(f"⏭️ [TRIGGER] Resource {resource_id} doesn't need metadata extraction")
            return

        metadata_data = {
            'resource_id': resource.get('id'),
            'resource_url': resource.get('url'),
            'resource_format': resource.get('format'),
            'package_id': resource.get('package_id'),
        }

        if self._metadata_use_jobs_queue():
            try:
                from ckan.lib import jobs
                job = jobs.enqueue(
                    extract_comprehensive_metadata_job,
                    [metadata_data],
                    title=f"schemingdcat metadata extraction {resource_id}",
                    queue='default',
                    rq_kwargs={'timeout': self._metadata_job_timeout()},
                )
                log.info(
                    f"🚀 [TRIGGER] Enqueued metadata extraction job {job.id} for resource {resource_id}"
                )
                if self._metadata_thread_fallback_enabled():
                    self._start_job_watchdog(job, resource, delay_seconds=60)
                return
            except Exception as e:
                log.error(
                    f"❌ [TRIGGER] Could not enqueue metadata extraction job for resource {resource_id}: {e}",
                    exc_info=True,
                )
                if not self._metadata_thread_fallback_enabled():
                    return

        if self._metadata_thread_fallback_enabled():
            log.warning(
                f"⚠️ [TRIGGER] Running thread fallback metadata extraction for resource {resource_id}"
            )
            self._fallback_metadata_extraction(resource)
        else:
            log.warning(
                f"⚠️ [TRIGGER] Metadata extraction skipped for resource {resource_id} "
                "because queue enqueue failed and thread fallback is disabled"
            )

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

    def _external_pdf_as_url_enabled(self):
        from ckan.common import config
        try:
            return toolkit.asbool(config.get('schemingdcat.external_pdf_as_url', True))
        except Exception:
            return True

    def _normalize_pdf_resource_format(self, context, resource):
        if not resource or not resource.get('id'):
            return resource

        looks_pdf = self._resource_looks_pdf(resource)
        if not looks_pdf:
            return resource

        # For external links, prefer treating PDF URLs as plain links to avoid
        # broken previews. Allow uploads to keep PDF normalization.
        url_type = (resource.get('url_type') or '').lower()
        if url_type != 'upload' and self._external_pdf_as_url_enabled():
            return resource

        fmt = (resource.get('format') or '').strip()
        fmt_is_pdf = self._value_looks_pdf(fmt)
        if fmt_is_pdf and fmt.upper() == 'PDF':
            return resource

        patch_data = {'id': resource['id']}
        if not fmt_is_pdf or fmt.upper() != 'PDF':
            patch_data['format'] = 'PDF'

        if not (resource.get('mimetype') or '').strip():
            pdf_mimetype = sdct_config.OGC2CKAN_MD_FORMATS.get('pdf', (None, None))[1]
            if pdf_mimetype:
                patch_data['mimetype'] = pdf_mimetype

        if len(patch_data) == 1:
            return resource

        try:
            system_context = dict(context)
            system_context.update({
                'ignore_auth': True,
                'api_version': 3,
                'defer_commit': False,
                '_schemingdcat_metadata_job': True,
                '_skip_doi_update': True,
            })
            toolkit.get_action('resource_patch')(system_context, patch_data)
            for key, value in patch_data.items():
                if key != 'id':
                    resource[key] = value
        except Exception as e:
            log.warning(f"⚠️ [FORMAT] Could not normalize PDF format for resource {resource.get('id')}: {e}")

        return resource

    def _disable_external_pdf_views(self, context, resource):
        if not resource or not resource.get('id'):
            return
        if not self._external_pdf_as_url_enabled():
            return

        url_type = (resource.get('url_type') or '').lower()
        if url_type == 'upload':
            return

        if not self._resource_looks_pdf(resource):
            return

        try:
            system_context = dict(context)
            system_context.update({
                'ignore_auth': True,
                'api_version': 3,
                'defer_commit': False,
            })
            views = toolkit.get_action('resource_view_list')(system_context, {'id': resource['id']}) or []
            removed = 0
            for view in views:
                view_type = (view.get('view_type') or '').lower()
                if 'pdf' in view_type:
                    toolkit.get_action('resource_view_delete')(system_context, {'id': view['id']})
                    removed += 1
            if removed:
                log.info(f"🧹 [VIEWS] Removed {removed} PDF view(s) for external resource {resource.get('id')}")
        except Exception as e:
            log.warning(f"⚠️ [VIEWS] Could not remove PDF views for resource {resource.get('id')}: {e}")

    def _resource_looks_pdf(self, resource):
        fmt = resource.get('format') or ''
        mimetype = resource.get('mimetype') or ''
        url = resource.get('url') or ''

        if self._value_looks_pdf(fmt) or self._value_looks_pdf(mimetype):
            return True

        return self._url_looks_pdf(url)

    def _value_looks_pdf(self, value):
        value = (value or '').strip().lower()
        if not value:
            return False
        if value == 'pdf':
            return True
        if 'application/pdf' in value or value.endswith('/pdf'):
            return True
        if value.startswith('http') and 'pdf' in value:
            return True
        return False

    def _url_looks_pdf(self, url):
        if not url:
            return False
        try:
            parsed = urlparse(url)
        except Exception:
            return False

        path = (parsed.path or '').lower()
        if path.endswith('.pdf'):
            return True

        fragment = (parsed.fragment or '').lower()
        if fragment.endswith('.pdf') or fragment == 'pdf':
            return True

        query = parse_qs(parsed.query or '')
        for key in ('file', 'filename', 'download', 'name', 'attachment', 'path'):
            for value in query.get(key, []):
                if value.lower().endswith('.pdf'):
                    return True
        for key in ('format', 'type', 'mime', 'mimetype'):
            for value in query.get(key, []):
                low = value.lower()
                if low == 'pdf' or 'application/pdf' in low:
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
