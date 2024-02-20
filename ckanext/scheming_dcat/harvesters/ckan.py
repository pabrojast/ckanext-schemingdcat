from builtins import str
from past.builtins import basestring
import json
import logging
from functools import lru_cache

import ckan.model as model
import ckan.logic as logic

from ckanext.harvest.harvesters.ckanharvester import CKANHarvester, ContentFetchError, ContentNotFoundError, RemoteResourceError,SearchError

from ckanext.scheming_dcat.harvesters.base import SchemingDCATHarvester

log = logging.getLogger(__name__)


class SchemingDCATCKANHarvester(CKANHarvester, SchemingDCATHarvester):
    """
    A custom CKAN harvester for Scheming DCAT datasets.
    """

    def info(self):
        return {
            'name': 'scheming_dcat_ckan',
            'title': 'Scheming DCAT CKAN endpoint',
            'description': 'Harvester for dataset with custom schema defined in ckanext-scheming_dcat extension.'
        }

    _names_taken = []
    
    def validate_config(self, config):
        """
        Validates the configuration for the SchemingDCATCKANHarvester.

        Args:
            config (str): The configuration JSON string.

        Returns:
            str: The validated configuration JSON string.

        Raises:
            ValueError: If the schema is not specified or is not supported.
            ValueError: If 'allow_harvest_datasets' is not a boolean.
        """
        # Call the parent class's method first
        super(SchemingDCATCKANHarvester, self).validate_config(config)

        # Get local schema
        self._get_local_schemas_supported()

        if self._local_schema_name is not None and not config:
            return json.dumps(self._local_schema)

        config_obj = json.loads(config)

        # Check if the schema is specified
        if 'schema' in config_obj:
            schema = config_obj['schema']
            if not isinstance(schema, basestring):
                raise ValueError('schema must be a string')

            # Check if the specified schema is supported
            if schema.lower() not in self._supported_schemas:
                if len(self._supported_schemas) > 1:
                    raise ValueError(f'schema should be one of: {", ".join(self._supported_schemas)}. Current dataset schema: {self._local_schema_name}')
                else:
                    raise ValueError(f'schema should match the local schema: {self._local_schema_name}')

        # If no schema is specified, use the local schema
        else:
            config = json.dumps({**config_obj, 'schema': self._local_schema_name})

        # Check if 'allow_harvest_datasets' is not in the config_obj or is not a boolean
        if 'allow_harvest_datasets' not in config_obj or not isinstance(config_obj['allow_harvest_datasets'], bool):
            config = json.dumps({**config_obj, 'allow_harvest_datasets': False})

        # Check remote_orgs and remote_groups == only_local, if not, put
        # remote_orgs and remote_groups to only_local
        if 'remote_groups' not in config_obj or config_obj.get('remote_groups') != 'only_local':
            config = json.dumps({**config_obj, 'remote_groups': 'only_local'})

        if 'remote_orgs' not in config_obj or config_obj.get('remote_orgs') != 'only_local':
            config = json.dumps({**config_obj, 'remote_orgs': 'only_local'})

        return config
    
    def modify_package_dict(self, package_dict, harvest_object):
        '''
        Allows custom harvesters to modify the package dict before
        creating or updating the actual package.

        Args:
            package_dict (dict): The package dictionary to be modified.
            harvest_object (HarvestObject): The harvest object associated with the package.

        Returns:
            dict: The modified package dictionary.
        '''
        # Clean up any existing extras already in package_dict
        package_dict = self._remove_duplicate_keys_in_extras(package_dict)

        return package_dict
    
    def import_stage(self, harvest_object):
        """
        Imports the harvested data into CKAN.

        Args:
            harvest_object (HarvestObject): The harvested object to import.

        Returns:
            bool: True if the import is successful, False otherwise.
        """
        log.debug('In SchemingDCATCKANHarvester import_stage')

        base_context = {'model': model, 'session': model.Session,
                        'user': self._get_user_name()}
        if not harvest_object:
            log.error('No harvest object received')
            return False

        if harvest_object.content is None:
            self._save_object_error('Empty content for object %s' %
                                    harvest_object.id,
                                    harvest_object, 'Import')
            return False

        self._set_config(harvest_object.job.source.config)

        try:
            package_dict = json.loads(harvest_object.content)

            # Check if the dataset is a harvest source and we are not allowed to harvest it
            if package_dict.get('type') == 'harvest' and self.config.get('allow_harvest_datasets', False) is False:
                log.warn('Remote dataset is a harvest source and allow_harvest_datasets is False, ignoring...')
                return True

            # Set default tags if needed
            default_tags = self.config.get('default_tags', [])
            if default_tags:
                if 'tags' not in package_dict:
                    package_dict['tags'] = []
                package_dict['tags'].extend(
                    [t for t in default_tags if t not in package_dict['tags']])

            # Set default groups if needed
            remote_groups = self.config.get('remote_groups', None)
            if remote_groups not in ('only_local', 'create'):
                # Ignore remote groups
                package_dict.pop('groups', None)
            else:
                if 'groups' not in package_dict:
                    package_dict['groups'] = []

                # check if remote groups exist locally, otherwise remove
                validated_groups = []

                for group_ in package_dict['groups']:
                    try:
                        try:
                            if 'id' in group_:
                                data_dict = {'id': group_['id']}
                                group = logic.get_action('group_show')(base_context.copy(), data_dict)
                            else:
                                raise logic.NotFound

                        except logic.NotFound:
                            if 'name' in group_:
                                data_dict = {'id': group_['name']}
                                group = logic.get_action('group_show')(base_context.copy(), data_dict)
                            else:
                                raise logic.NotFound
                        # Found local group
                        validated_groups.append({'id': group['id'], 'name': group['name']})

                    except logic.NotFound:
                        log.info('Group %s is not available', group_)
                        if remote_groups == 'create':
                            try:
                                group = self._get_group(harvest_object.source.url, group_)
                            except RemoteResourceError:
                                log.error('Could not get remote group %s', group_)
                                continue

                            for key in ['packages', 'created', 'users', 'groups', 'tags', 'extras', 'display_name']:
                                group.pop(key, None)

                            logic.get_action('group_create')(base_context.copy(), group)
                            log.info('Group %s has been newly created', group_)
                            validated_groups.append({'id': group['id'], 'name': group['name']})

                package_dict['groups'] = validated_groups

            log.debug("Go to source_dataset")

            # Local harvest source organization
            source_dataset = logic.get_action('package_show')(base_context.copy(), {'id': harvest_object.source.id})
            local_org = source_dataset.get('owner_org')

            remote_orgs = self.config.get('remote_orgs', None)

            if remote_orgs not in ('only_local', 'create'):
                # Assign dataset to the source organization
                package_dict['owner_org'] = local_org
            else:
                if 'owner_org' not in package_dict:
                    package_dict['owner_org'] = None

                # check if remote org exist locally, otherwise remove
                validated_org = None
                remote_org = package_dict['owner_org']

                if remote_org:
                    try:
                        data_dict = {'id': remote_org}
                        org = logic.get_action('organization_show')(base_context.copy(), data_dict)
                        validated_org = org['id']
                    except logic.NotFound:
                        log.info('Organization %s is not available', remote_org)
                        if remote_orgs == 'create':
                            try:
                                try:
                                    org = self._get_organization(harvest_object.source.url, remote_org)
                                except RemoteResourceError:
                                    # fallback if remote CKAN exposes organizations as groups
                                    # this especially targets older versions of CKAN
                                    org = self._get_group(harvest_object.source.url, remote_org)

                                for key in ['packages', 'created', 'users', 'groups', 'tags',
                                            'extras', 'display_name', 'type']:
                                    org.pop(key, None)
                                logic.get_action('organization_create')(base_context.copy(), org)
                                log.info('Organization %s has been newly created', remote_org)
                                validated_org = org['id']
                            except (RemoteResourceError, logic.ValidationError):
                                log.error('Could not get remote org %s', remote_org)

                package_dict['owner_org'] = validated_org or local_org

            # Set default groups if needed
            default_groups = self.config.get('default_groups', [])
            if default_groups:
                base_context_copy = base_context.copy()
                package_dict['groups'] = []
                for g in default_groups:
                    try:
                        data_dict = {'id': g}
                        group = logic.get_action('group_show')(base_context_copy, data_dict)
                        package_dict['groups'].append({'id': group['id'], 'name': group['name']})
                    except (SearchError, logic.NotFound):
                        log.error('Could not get local group %s', g)
                        
            log.debug('Package groups: %s', package_dict['groups'])

            # Set default extras if needed
            default_extras = self.config.get('default_extras', {})

            def get_extra(key, package_dict):
                for extra in package_dict.get('extras', []):
                    if extra['key'] == key:
                        return extra
            if default_extras:
                override_extras = self.config.get('override_extras', False)
                if 'extras' not in package_dict:
                    package_dict['extras'] = []
                for key, value in default_extras.items():
                    existing_extra = get_extra(key, package_dict)
                    if existing_extra and not override_extras:
                        continue  # no need for the default
                    if existing_extra:
                        package_dict['extras'].remove(existing_extra)
                    # Look for replacement strings
                    if isinstance(value, str):
                        value = value.format(
                            harvest_source_id=harvest_object.job.source.id,
                            harvest_source_url=harvest_object.job.source.url.strip('/'),
                            harvest_source_title=harvest_object.job.source.title,
                            harvest_job_id=harvest_object.job.id,
                            harvest_object_id=harvest_object.id,
                            dataset_id=package_dict['id'])

                    package_dict['extras'].append({'key': key, 'value': value})

            for resource in package_dict.get('resources', []):
                # Clear remote url_type for resources (eg datastore, upload) as
                # we are only creating normal resources with links to the
                # remote ones
                resource.pop('url_type', None)

                # Clear revision_id as the revision won't exist on this CKAN
                # and saving it will cause an IntegrityError with the foreign
                # key.
                resource.pop('revision_id', None)

            package_dict = self.modify_package_dict(package_dict, harvest_object)
            
            result = self._create_or_update_package(
                package_dict, harvest_object, package_dict_form='package_show')

            # Log package_dict, package dict is a dict
            log.debug('Package create or update: %s', result)

            return result

        except logic.ValidationError as e:
            self._save_object_error('Invalid package with GUID %s: %r' %
                                    (harvest_object.guid, e.error_dict),
                                    harvest_object, 'Import')
        except Exception as e:
            self._save_object_error('%s' % e, harvest_object, 'Import')
