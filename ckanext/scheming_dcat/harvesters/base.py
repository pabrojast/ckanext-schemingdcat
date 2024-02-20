import logging
import uuid
from functools import lru_cache
import json

from sqlalchemy import exists, and_
from sqlalchemy.sql import update, bindparam
from sqlalchemy.orm import contains_eager

from ckan import plugins as p
import ckan.logic as logic
from ckan.logic.schema import default_create_package_schema
from ckan import model
from ckan.model import Session
from ckantoolkit import config
from ckan.lib.navl.validators import ignore_missing, ignore

from ckanext.harvest.logic.schema import unicode_safe
from ckanext.harvest.harvesters import HarvesterBase

from ckanext.scheming_dcat.helpers import schemingdct_get_schema_names

log = logging.getLogger(__name__)


class SchemingDCATHarvester(HarvesterBase):
    """
    A custom harvester for harvesting metadata using the Scheming DCAT extension.

    It extends the base `HarvesterBase` class provided by CKAN's harvest extension.
    """
    _local_schema = None
    _remote_schema = None
    _local_schema_name = None
    _remote_schema_name = None
    _supported_schemas = []

    @lru_cache(maxsize=None)
    def _get_local_schema(self, schema_type='dataset'):
        """
        Retrieves the schema for the dataset instance and caches it using the LRU cache decorator for efficient retrieval.

        Args:
            schema_type (str, optional): The type of schema to retrieve. Defaults to 'dataset'.

        Returns:
            dict: The schema of the dataset instance.
        """
        return logic.get_action('scheming_dataset_schema_show')({}, {'type': schema_type})

    @lru_cache(maxsize=None)
    def _get_remote_schema(self, base_url, schema_type='dataset'):
        """
        Fetches the remote schema for a given base URL and schema type.

        Args:
            base_url (str): The base URL of the remote server.
            schema_type (str, optional): The type of schema to fetch. Defaults to 'dataset'.

        Returns:
            dict: The remote schema as a dictionary.

        Raises:
            HarvesterBase.ContentFetchError: If there is an error fetching the remote schema content.
            ValueError: If there is an error decoding the remote schema content.
            KeyError: If the remote schema content does not contain the expected result.

        """
        url = base_url + self._get_action_api_offset() + \
            '/scheming_dataset_schema_show?type=' + schema_type
        try:
            content = self._get_content(url)
            content_dict = json.loads(content)
            return content_dict['result']
        except (HarvesterBase.ContentFetchError, ValueError, KeyError):
            log.debug('Could not fetch/decode remote schema')
            raise HarvesterBase.RemoteResourceError(
                'Could not fetch/decode remote schema')

    def _get_local_schemas_supported(self):
        """
        Retrieves the local schema supported by the harvester.

        Returns:
            list: A list of supported local schema names.
        """
        
        if self._local_schema is None:
            self._local_schema = self._get_local_schema()
        
        if self._local_schema_name is None:
            self._local_schema_name = self._local_schema.get('schema_name', None)
        
        # Get the set of available schemas
        #self._supported_schemas = set(schemingdct_get_schema_names())
        self._supported_schemas.append(self._local_schema_name)

    def _get_dict_value(self, _dict, key, default=None):
        '''
        Returns the value for the given key on a CKAN dict

        By default a key on the root level is checked. If not found, extras
        are checked.

        If not found, returns the default value, which defaults to None
        '''

        if key in _dict:
            return _dict[key]

        for extra in _dict.get('extras', []):
            if extra['key'] == key:
                return extra['value']

        return default

    def _get_guid(self, dataset_dict, source_url=None):
        '''
        Try to get a unique identifier for a harvested dataset

        It will be the first found of:
         * URI identifier
         * identifier
         * Source URL + Dataset name
         * Dataset name
         * uuid4

         The last two are obviously not optimal, as depend on title, which
         might change.

         Returns None if no guid could be decided.
        '''
        guid = None

        guid = (
            self._get_dict_value(dataset_dict, 'uri') or
            self._get_dict_value(dataset_dict, 'identifier')
        )
        if guid:
            return guid

        if dataset_dict.get('name'):
            guid = dataset_dict['name']
            if source_url:
                guid = source_url.rstrip('/') + '/' + guid
        
        if not guid:
            guid = str(uuid.uuid4())        
        
        return guid

    def _remove_duplicate_keys_in_extras(self, dataset_dict):
        """
        Remove duplicate keys in the 'extras' list of dictionaries of the given dataset_dict.

        Args:
            dataset_dict (dict): The dataset dictionary.

        Returns:
            dict: The updated dataset dictionary with duplicate keys removed from the 'extras' list of dictionaries.
        """
        common_keys = set(extra['key'] for extra in dataset_dict['extras']).intersection(dataset_dict)
        dataset_dict['extras'] = [extra for extra in dataset_dict['extras'] if extra['key'] not in common_keys]

        return dataset_dict
