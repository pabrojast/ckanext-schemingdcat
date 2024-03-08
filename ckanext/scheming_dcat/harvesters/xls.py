from builtins import str
from past.builtins import basestring
import json
import logging
import re
import uuid
import base64
import traceback
import six
import dateutil

import gspread
import pandas as pd

from ckan.logic import NotFound, get_action
from ckan import logic
import ckan.plugins as p
import ckan.model as model

from ckanext.harvest.model import HarvestObject, HarvestObjectExtra
from ckanext.scheming_dcat.harvesters.base import SchemingDCATHarvester, RemoteResourceError, ReadError, RemoteSchemaError
from ckanext.scheming_dcat.interfaces import ISchemingDCATHarvester

log = logging.getLogger(__name__)


class SchemingDCATXLSHarvester(SchemingDCATHarvester):
    """
    """

    def info(self):
        return {
            'name': 'scheming_dcat_xls',
            'title': 'Remote XLS/XLSX Metadata Batch Harvester',
            'description': 'A harvester for remote Excel files with Metadata records.',
            'about_url': 'https://github.com/mjanez/ckanext-scheming_dcat?tab=readme-ov-file#remote-xlsxlsx-metadata-batch-harvester'
        }

    _storage_types_supported = [
        {
            'name': 'gspread',
            'title': 'Google Sheets',
            'active': True
        },
        {
            'name': 'onedrive',
            'title': 'OneDrive',
            'active': True
        },
        {
            'name': 'gdrive',
            'title': 'Google Drive',
            'active': False
        }
    ]
    
    _storage_type = None
    _auth = False
    _credentials = None
    _names_taken = []

    #TODO: Implement the get_harvester_basic_info method
    def _set_config_credentials(self, storage_type, config_obj):
        """
        Set the credentials based on the storage type and configuration object.

        Args:
            storage_type (str): The type of storage (e.g., 'onedrive', 'gspread', 'gdrive').
            config_obj (dict): The configuration object containing the credentials.

        Returns:
            dict: The credentials dictionary.

        Raises:
            ValueError: If the credentials are not provided or are in an invalid format.

        """
        credentials = {}

        #TODO: Improve the credentials validation for Onedrive
        if storage_type == 'onedrive':
            if 'credentials' in config_obj:
                credentials = config_obj['credentials']
                if not isinstance(config_obj, dict):
                    raise ValueError('credentials must be a dictionary')
                if 'credentials' not in config_obj or not isinstance(config_obj['credentials'], dict):
                    raise ValueError('credentials must be a dictionary')
                if 'username' not in config_obj['credentials'] or not isinstance(config_obj['credentials']['username'], str):
                    raise ValueError('username must be a string')
                if 'password' not in config_obj['credentials'] or not isinstance(config_obj['credentials']['password'], str):
                    raise ValueError('password must be a string')

                credentials = {'username': credentials['username'].strip(), 'password': credentials['password'].strip()}

            else:
                raise ValueError('Credentials for Onedrive: eg. "credentials": {"username": "john", "password": "password"}')

        elif storage_type == 'gspread' or storage_type == 'gdrive':
            if 'credentials' in config_obj:
                credentials = config_obj['credentials']
                if not isinstance(credentials, dict):
                    raise ValueError('credentials must be a dictionary')

            else:
                raise ValueError('Need credentials for Gspread/Gdrive. See: https://docs.gspread.org/en/latest/oauth2.html#for-bots-using-service-account')

        return credentials
    
    def _get_storage_base_url(self, url, storage_type="gspread"):
        """
        Get the base URL for the given storage type.

        Args:
            url (str): The URL to extract the base URL from.
            storage_type (str, optional): The type of storage. Defaults to "gspread".

        Returns:
            str: The base URL.

        """        
        if storage_type == 'gspread':
            base_url = url[:url.find('/', url.rfind('d/') + 2)]

        elif storage_type == 'onedrive':
            base_url = url
            
        else:
            return url

        return base_url
    
    def _get_storage_url(self, url, storage_type='gspread'):
        """
        Get the remote source URL based on the given URL and storage type.

        Args:
            url (str): The input URL.
            storage_type (str, optional): The type of storage. Defaults to 'gspread'.

        Returns:
            str: The remote source URL.

        Raises:
            ValueError: If an invalid storage_type is provided.
        """
        try:
            if storage_type == 'onedrive':
                data_bytes64 = base64.urlsafe_b64encode(url.encode('utf-8')).rstrip(b'=')
                data_bytes64_str = data_bytes64.decode('utf-8')
                remote_source_url = f'https://api.onedrive.com/v1.0/shares/u!{data_bytes64_str}/root/content'

            elif storage_type == 'gspread':
                remote_source_url = url

            else:
                raise ValueError(f'Invalid storage_type: {storage_type}')

            return remote_source_url

        except Exception as e:
            raise ValueError('Invalid storage_type') from e
 
    def _read_excel_sheet(self, url, sheet_name, storage_type, engine='openpyxl'):
        """
        Reads an Excel sheet from a given URL and returns the data as a pandas DataFrame.

        Args:
            url (str): The URL of the Excel file.
            sheet_name (str): The name of the sheet to read.
            storage_type (str): The type of storage where the Excel file is located. Supported types are 'onedrive', 'gspread', and 'gdrive'.
            engine (str, optional): The engine to use for reading the Excel file. Defaults to 'openpyxl'.

        Returns:
            pandas.DataFrame: The data from the specified sheet as a DataFrame.

        Raises:
            ReadError: If there is an error reading the sheet.

        """
        try:
            if storage_type == 'onedrive':
                if self.auth and self._credentials:
                    # TODO: Implement the read_excel_sheet method for Onedrive Auth
                    pass
                else:
                    try:
                        data = pd.read_excel(url, sheet_name=sheet_name, dtype=str, engine=engine)
                    except pd.errors.ParserError as e:
                        raise ReadError(f'Error reading sheet {sheet_name} using URL {url}. Error: {str(e)}')

            elif storage_type in ['gspread', 'gdrive']:
                if self._auth and self._credentials:
                    try:
                        gc = gspread.service_account_from_dict(self._credentials)
                        sh = gc.open_by_url(url)
                        worksheet = sh.worksheet(sheet_name)
                        data = pd.DataFrame(worksheet.get_all_records(), dtype=str)
                    except gspread.exceptions.APIError as e:
                        raise ReadError(f'Error reading sheet {sheet_name} using URL {url}. Error: {str(e)}')
                else:
                    raise ValueError('Need credentials for Gspread/Gdrive. See: https://docs.gspread.org/en/latest/oauth2.html#for-bots-using-service-account')

            else:
                raise ValueError(f'Unsupported storage type: {storage_type}')

            return data.fillna('')

        except Exception as e:
            raise ReadError(f'Error reading sheet {sheet_name} using URL {url}. Error: {str(e)}')

    def _clean_table_datasets(self, data):
        """
        Clean the table datasets by removing leading/trailing whitespaces, newlines, and tabs.

        Args:
            data (pandas.DataFrame): The input table dataset.

        Returns:
            list: A list of dictionaries representing the cleaned table datasets.
        """
        # Clean column names by removing leading/trailing whitespaces, newlines, and tabs
        data.columns = data.columns.str.strip().str.replace('\n', '').str.replace('\t', '')

        # Remove all fields that are a nan float and trim all spaces of the values
        data = data.apply(lambda x: x.str.strip() if x.dtype == 'object' else x)
        data = data.fillna(value='')

        # Convert table to list of dicts
        return data.to_dict('records')

    def _clean_table_distributions(self, data, prefix_colnames='resource_', dataset_id_colname='dataset_id'):
        """
        Clean the table distributions data.

        Args:
            data (pandas.DataFrame): The table distributions data.
            prefix_colnames (str, optional): The prefix used in column names that need to be removed. Defaults to 'resource_'.
            dataset_id_colname (str, optional): The column name representing the dataset ID. Defaults to 'dataset_id'.

        Returns:
            dict or None: A dictionary containing the cleaned distributions data grouped by dataset_id,
            or None if no distributions are loaded.
        """
        # Select only the columns of type 'object' and apply the strip() method to them
        data.loc[:, data.dtypes == object] = data.select_dtypes(include=['object']).apply(lambda x: x.str.strip())

        # Remove prefixes from column names in the distributions dataframe
        data = data.rename(columns=lambda x: x.replace(prefix_colnames, ''))

        # Remove rows where dataset_id_colname is None or an empty string
        data = data[data[dataset_id_colname].notna() & (data[dataset_id_colname] != '')]

        if not data.empty:
            # Group distributions by dataset_id and convert to list of dicts
            return data.groupby(dataset_id_colname).apply(lambda x: x.to_dict('records')).to_dict()
        else:
            log.debug('No distributions loaded. Check "distribution.%s" fields', dataset_id_colname)
            return None

    def _clean_table_datadictionaries(self, data, resource_id_colname='resource_id'):
        """
        Clean and process the table of data dictionaries.

        Args:
            data (pandas.DataFrame): The table of data dictionaries.
            resource_id_colname (str, optional): The column name for the resource ID. Defaults to 'resource_id'.

        Returns:
            dict or None: A dictionary containing the cleaned and processed data dictionaries grouped by resource ID,
                          or None if no data dictionaries were loaded.
        """
        # Select only the columns of type 'object' and apply the strip() method to them
        data.loc[:, data.dtypes == object] = data.select_dtypes(include=['object']).apply(lambda x: x.str.strip())

        # Remove prefixes from column names in the datadictionaries dataframe
        data = data.rename(columns=lambda x: re.sub(re.compile(r'datadictionary(_info)?_'), '', x).replace('info.', ''))

        # Filter datadictionaries where resource_id is not empty or None
        if resource_id_colname in data.columns:
            data = data[data[resource_id_colname].notna() & (data[resource_id_colname] != '')]

            # Group datadictionaries by resource_id and convert to list of dicts
            return data.groupby(resource_id_colname).apply(lambda x: x.to_dict('records')).to_dict()
        else:
            log.debug('No datadictionaries loaded. Check "datadictionary.%s" fields', resource_id_colname)
            return None

    def _add_distributions_and_datadictionaries_to_datasets(self, table_datasets, table_distributions_grouped, table_datadictionaries_grouped, identifier_field='identifier', alternate_identifier_field='alternate_identifier', inspire_id_field='inspire_id'):
        """
        Add distributions (CKAN resources) and datadictionaries to each dataset object.

        Args:
            table_datasets (list): List of dataset objects.
            table_distributions_grouped (dict): Dictionary of distributions grouped by dataset identifier.
            table_datadictionaries_grouped (dict): Dictionary of datadictionaries grouped by dataset identifier.
            identifier_field (str, optional): Field name for the identifier. Defaults to 'identifier'.
            alternate_identifier_field (str, optional): Field name for the alternate identifier. Defaults to 'alternate_identifier'.
            inspire_id_field (str, optional): Field name for the inspire id. Defaults to 'inspire_id'.

        Returns:
            list: List of dataset objects with distributions (CKAN resources) and datadictionaries added.
        """
        return [
            {
                **d,
                'resources': [
                    {**dr, 'datadictionaries': table_datadictionaries_grouped.get(dr['id'], []) if table_datadictionaries_grouped else []}
                    for dr in table_distributions_grouped.get(
                        d.get(identifier_field) or d.get(alternate_identifier_field) or d.get(inspire_id_field), []
                    )
                ]
            }
            for d in table_datasets
        ]

    def _process_content(self, content_dict, source_url):
        """
        Process the content of the harvested dataset.

        Args:
            content_dict (dict): A dictionary containing the content of the harvested dataset.
            source_url (str): The URL of the harvested dataset.

        Returns:
            dict: A dictionary containing the processed content of the harvested dataset.
        """
        log.debug('In SchemingDCATXLSHarvester process_content: %s', source_url)

        table_datasets = self._clean_table_datasets(content_dict['datasets'])

        if content_dict.get('distributions') is not None and not content_dict['distributions'].empty:
            table_distributions_grouped = self._clean_table_distributions(content_dict['distributions'])
        else:
            table_distributions_grouped = None

        if content_dict.get('datadictionaries') is not None and not content_dict['datadictionaries'].empty:
            table_datadictionaries_grouped = self._clean_table_datadictionaries(content_dict['datadictionaries'])
        else:
            table_datadictionaries_grouped = None

        return self._add_distributions_and_datadictionaries_to_datasets(table_datasets, table_distributions_grouped, table_datadictionaries_grouped)

    def get_package_dict(self, harvest_object, context, package_dict=None):
        """
        Returns a dictionary representing the CKAN package to be created or updated.

        Args:
            harvest_object (HarvestObject): The harvest object being processed.
            context (dict): The context of the harvest process.
            package_dict (dict, optional): The initial package dictionary (dataset). Defaults to None.

        Returns:
            dict: The package dictionary with translated fields and default values set.
        """
        # Add default values: tags, groups, etc.
        package_dict = self._set_package_dict_default_values(package_dict, harvest_object, context)

        # Update unique ids
        for resource in package_dict['resources']:
            resource['alternate_identifier'] = resource['id']
            resource['id'] = str(uuid.uuid4())
            resource.pop('dataset_id', None)

        return package_dict

    @staticmethod
    def _set_value_to_list(value):
        """
        Determines whether a value should be converted to a list.

        Args:
            value (str): The value to check.

        Returns:
            bool: True if the value should be converted to a list, False otherwise.
        """
        # Check if the value is a string containing commas but not common sentence punctuation
        return isinstance(value, str) and ',' in value and not any(char in value for char in '.!?')

    @staticmethod
    def _set_string_to_list(value):
        """
        Converts a comma-separated string into a list of items.

        Args:
            value (str): The comma-separated string to convert.

        Returns:
            list: A list of items, with leading and trailing whitespace removed from each item.

        Example:
            >>> _set_string_to_list('apple, banana, orange')
            ['apple', 'banana', 'orange']
        """
        return [x.strip().lstrip('-').strip() for x in value.split(',') if x.strip()]

    def _update_dict_lists(self, data):
        """
        Update the dictionary lists in the given data.

        Args:
            data (list): The data to be updated.

        Returns:
            list: The updated data.
        """
        if self._local_schema is None:
            self._local_schema = self._get_local_schema()

        # Get the list of fields that should be converted to lists
        list_fields = ['groups'] + [
            field['field_name']
            for field in self._local_schema['dataset_fields']
            if any(keyword in field.get(field_type, '').lower() for keyword in ['list', 'multiple', 'tag_string', 'tag', 'group'] for field_type in ['validators', 'output_validators', 'preset']) or 'groups' in field['field_name'].lower()
        ]

        for element in data:
            for key, value in element.items():
                if key in list_fields and isinstance(value, str):
                    element[key] = self._set_string_to_list(value)
                elif key == 'distributions':
                    for distribution in value:
                        for key_dist, value_dist in distribution.items():
                            if key_dist in list_fields and isinstance(value_dist, str):
                                distribution[key_dist] = self._set_string_to_list(value_dist)

        # Return the updated data
        return data

    def validate_config(self, config):
        """
        Validates the configuration for the harvester.

        Args:
            config (dict): The configuration dictionary.

        Returns:
            str: The validated configuration as a JSON string.

        Raises:
            ValueError: If the configuration is invalid.

        """
        config_obj = self.get_harvester_basic_info(config)
        auth = False

        supported_types = ', '.join([st['name'] for st in self._storage_types_supported if st['active']])

        # Check basic validation config
        self._set_basic_validate_config(config)

        # Check the storage type of the remote file
        if 'storage_type' in config:
            storage_type = config_obj['storage_type']
            if not isinstance(storage_type, basestring):
                raise ValueError('storage_type must be a string')

            if storage_type not in supported_types:
                raise ValueError(f'storage_type should be one of: {supported_types}')

            config = json.dumps({**config_obj, 'storage_type': storage_type})

        else:
            raise ValueError(f'storage_type should be one of: {supported_types}')

        # Check the name of the dataset sheet in the XLS/XLSX file
        if 'dataset_sheet' in config:
            dataset_sheet = config_obj['dataset_sheet']
            if not isinstance(dataset_sheet, basestring):
                raise ValueError('dataset_sheet must be a string')
    
            config = json.dumps({**config_obj, 'dataset_sheet': dataset_sheet.strip()})

        else:
            raise ValueError('The name of the datasets sheet is required. eg. "dataset_sheet": "Dataset"')

        # Check the name of the distribution and data dictionary (resourcedictionary) sheets in the XLS/XLSX file
        if 'distribution_sheet' in config:
            distribution_sheet = config_obj['distribution_sheet']
            if not isinstance(distribution_sheet, basestring):
                raise ValueError('distribution_sheet must be a string')

            config = json.dumps({**config_obj, 'distribution_sheet': distribution_sheet.strip()})
    
        if 'datadictionary_sheet' in config:
            datadictionary_sheet = config_obj['datadictionary_sheet']
            if not isinstance(datadictionary_sheet, basestring):
                raise ValueError('datadictionary_sheet must be a string')

            config = json.dumps({**config_obj, 'datadictionary_sheet': datadictionary_sheet.strip()})

        # Check auth and retrieve credentials for the storage type
        if 'auth' in config:
            auth = config_obj['auth']
            if not isinstance(auth, bool):
                raise ValueError('Authentication must be a boolean. eg. "auth": True or "auth": False')
        else:
            config = json.dumps({**config_obj, 'auth': False})
    
        if auth is True:
            credentials = self._set_config_credentials(storage_type, config_obj)
            config = json.dumps({**config_obj, 'credentials': credentials})

        if 'default_tags' in config_obj:
            if not isinstance(config_obj['default_tags'], list):
                raise ValueError('default_tags must be a list')
            if config_obj['default_tags'] and \
                    not isinstance(config_obj['default_tags'][0], dict):
                raise ValueError('default_tags must be a list of '
                                    'dictionaries')

        if 'default_groups' in config_obj:
            if not isinstance(config_obj['default_groups'], list):
                raise ValueError('default_groups must be a *list* of group'
                                    ' names/ids')
            if config_obj['default_groups'] and \
                    not isinstance(config_obj['default_groups'][0], str):
                raise ValueError('default_groups must be a list of group '
                                    'names/ids (i.e. strings)')

            # Check if default groups exist
            context = {'model': model, 'user': p.toolkit.c.user}
            config_obj['default_group_dicts'] = []
            for group_name_or_id in config_obj['default_groups']:
                try:
                    group = get_action('group_show')(
                        context, {'id': group_name_or_id})
                    # save the id and name to the config object, as we'll need it
                    # in the import_stage of every dataset
                    config_obj['default_group_dicts'].append({'id': group['id'], 'name': group['name']})
                except NotFound:
                    raise ValueError('Default group not found')
            config = json.dumps(config_obj)

        if 'default_extras' in config_obj:
            if not isinstance(config_obj['default_extras'], dict):
                raise ValueError('default_extras must be a dictionary')

        if 'user' in config_obj:
            # Check if user exists
            context = {'model': model, 'user': p.toolkit.c.user}
            try:
                get_action('user_show')(
                    context, {'id': config_obj.get('user')})
            except NotFound:
                raise ValueError('User not found')

        # Check if 'allow_harvest_datasets' is not in the config_obj or is not a boolean
        if 'allow_harvest_datasets' not in config_obj or not isinstance(config_obj['allow_harvest_datasets'], bool):
            config = json.dumps({**config_obj, 'allow_harvest_datasets': False})

        # Validate if exists a JSON contained the mapping field_names between the remote schema and the local schema        
        for mapping_name in ['dataset_field_mapping', 'distribution_field_mapping']:
            if mapping_name in config:
                field_mapping = config_obj[mapping_name]
                if not isinstance(field_mapping, dict):
                    raise ValueError(f'{mapping_name} must be a dictionary')

                # Check if the config is a valid mapping
                for local_field, remote_field in field_mapping.items():
                    if not isinstance(local_field, basestring):
                        raise ValueError('"local_field_name" must be a string')
                    if not isinstance(remote_field, (basestring, dict)):
                        raise ValueError('"remote_field_name" must be a string or a dictionary')
                    if isinstance(remote_field, dict):
                        for lang, remote_field_name in remote_field.items():
                            if not isinstance(lang, basestring) or not isinstance(remote_field_name, basestring):
                                raise ValueError('In translated fields, both language and remote_field_name must be strings. eg. "notes_translated": {"es": "notes-es"}')
                            if not re.match("^[a-z]{2}$", lang):
                                raise ValueError('Language code must be a 2-letter ISO 639-1 code')

                config = json.dumps({**config_obj, mapping_name: field_mapping})

        return config     

    def modify_package_dict(self, package_dict, harvest_object):
        '''
            Allows custom harvesters to modify the package dict before
            creating or updating the actual package.
        '''              
        return package_dict

    def gather_stage(self, harvest_job):
        """
        Performs the gather stage of the SchemingDCATXLSHarvester. This method is responsible for downloading the remote XLS/XLSX file and reading its contents. The contents are then processed, cleaned, and added to the database.

        Args:
            harvest_job (HarvestJob): The harvest job object.

        Returns:
            list: A list of object IDs for the harvested datasets.
        """
        # Get file contents of source url
        source_url = harvest_job.source.url
        
        log.debug('In SchemingDCATXLSHarvester gather_stage with XLS remote file: %s', source_url)
        
        content_dict = {}
        self._names_taken = []
        
        # Get config options
        if harvest_job.source.config:
            self._set_config(harvest_job.source.config)
            dataset_sheetname = self.config.get("dataset_sheet")
            distribution_sheetname = self.config.get("distribution_sheet")
            datadictionary_sheetname = self.config.get("datadictionary_sheet")
            self.get_harvester_basic_info(harvest_job.source.config)
        
        log.debug('Using config: %r', self.config)
        
        if self.config:
            self._storage_type = self.config.get("storage_type")
            self._auth = self.config.get("auth")
            self._credentials = self.config.get("credentials")

            # Get URLs for remote file
            remote_xls_base_url = self._get_storage_base_url(source_url, self._storage_type)
            remote_xls_download_url = self._get_storage_url(source_url, self._storage_type)
        
        # Check if the remote file is valid
        is_valid = self._check_url(remote_xls_download_url, harvest_job)
        log.debug('URL is accessible: %s', remote_xls_download_url)

        # Get the previous guids for this source
        query = \
            model.Session.query(HarvestObject.guid, HarvestObject.package_id) \
            .filter(HarvestObject.current == True) \
            .filter(HarvestObject.harvest_source_id == harvest_job.source.id)
        guid_to_package_id = {}

        for guid, package_id in query:
            guid_to_package_id[guid] = package_id

        guids_in_db = set(guid_to_package_id.keys())
        guids_in_harvest = set()

        # before_download interface
        for harvester in p.PluginImplementations(ISchemingDCATHarvester):
            remote_xls_download_url, before_download_errors = harvester.before_download(remote_xls_download_url, harvest_job)
        
            for error_msg in before_download_errors:
                self._save_gather_error(error_msg, harvest_job)
            
            if not source_url:
                return []
        
        # Read sheets
        if is_valid:
            try:
                try:
                    content_dict['datasets'] = self._read_excel_sheet(remote_xls_download_url, dataset_sheetname, self._storage_type )
                except RemoteResourceError as e:
                    self._save_gather_error('Error reading the remote Excel datasets sheet: {0}'.format(e), harvest_job)
                    return False
                
                if distribution_sheetname:
                    content_dict['distributions'] = self._read_excel_sheet(remote_xls_download_url, distribution_sheetname, self._storage_type )
                    
                #TODO: Implement self._load_datadictionaries() method.
                # if datadictionary_sheetname:
                #     content_dict['datadictionaries'] = self._read_excel_sheet(remote_xls_download_url, datadictionary_sheetname, self._storage_type )

                # after_download interface
                for harvester in p.PluginImplementations(ISchemingDCATHarvester):
                    content_dict, after_download_errors = harvester.after_download(content_dict, harvest_job)

                    for error_msg in after_download_errors:
                        self._save_gather_error(error_msg, harvest_job)

                if not content_dict:
                    return []

            except Exception as e:
                self._save_gather_error('Could not read Excel file: %s' % str(e), harvest_job)
                return False
    
        # Check if the content_dict colnames correspond to the local schema
        try:
            remote_dataset_field_mapping = self.config.get("dataset_field_mapping")
            remote_dataset_field_names = set(content_dict['datasets'].columns)
            remote_resource_field_mapping = self.config.get("distribution_field_mapping")
            remote_resource_field_names = set(content_dict['distributions'].columns)
            self._validate_remote_schema(remote_dataset_field_names=remote_dataset_field_names, remote_ckan_base_url=None, remote_resource_field_names=remote_resource_field_names, remote_dataset_field_mapping=remote_dataset_field_mapping, remote_resource_field_mapping=remote_resource_field_mapping)
        except RemoteSchemaError as e:
            self._save_gather_error('Error validating remote schema: {0}'.format(e), harvest_job)
            return []

        # Clean tables
        try:
            clean_datasets = self._process_content(content_dict, remote_xls_base_url)
            log.debug('XLS file cleaned successfully.')
            clean_datasets = self._update_dict_lists(clean_datasets)
            log.debug('Update dict string lists.')
            
        except Exception as e:
            self._save_gather_error('Error cleaning the XLSX file: {0}'.format(e), harvest_job)
            return []
    
        for harvester in p.PluginImplementations(ISchemingDCATHarvester):
            clean_datasets, after_cleaning_errors = harvester.after_cleaning(clean_datasets, harvest_job)

            for error_msg in after_cleaning_errors:
                self._save_gather_error(error_msg, harvest_job)
    
        # Add datasets to the database
        try:
            log.debug('Add datasets to DB')
            datasets_to_harvest = {}
            source_dataset = model.Package.get(harvest_job.source.id)
            for dataset in clean_datasets:
                # Using name as identifier. XLS datasets doesnt have identifier
                try:
                    if not dataset.get('name'):
                        dataset['name'] = self._gen_new_name(dataset['title'])
                    while dataset['name'] in self._names_taken:
                        suffix = sum(name.startswith(dataset['name'] + '-') for name in self._names_taken) + 1
                        dataset['name'] = '{}-{}'.format(dataset['name'], suffix)
                    self._names_taken.append(dataset['name'])

                    # If the dataset has no identifier, use the name
                    if not dataset.get('identifier'):
                        dataset['identifier'] = self._generate_identifier(dataset)
                except Exception as e:
                    self._save_gather_error('Error for the dataset identifier %s [%r]' % (dataset['identifier'], e), harvest_job)
                    continue

                # Set translated fields
                dataset = self._set_translated_fields(dataset)
                
                # Check if a dataset with the same identifier exists can be overridden if necessary
                #existing_dataset = self._check_existing_package_by_ids(dataset)
                #log.debug('existing_dataset: %s', existing_dataset)
                            
                # Unless already set by the dateutil.parser.parser, get the owner organization (if any)
                # from the harvest source dataset
                if not dataset.get('owner_org'):
                    if source_dataset.owner_org:
                        dataset['owner_org'] = source_dataset.owner_org

                if 'extras' not in dataset:
                    dataset['extras'] = []

                # if existing_dataset:
                #     dataset['identifier'] = existing_dataset['identifier']
                #     guids_in_db.add(dataset['identifier'])
                    
                guids_in_harvest.add(dataset['identifier'])
                datasets_to_harvest[dataset['identifier']] = dataset

        except Exception as e:
            self._save_gather_error('Error when processsing dataset: %r / %s' % (e, traceback.format_exc()),
                                    harvest_job)
            return []

        # Check guids to create/update/delete
        new = guids_in_harvest - guids_in_db
        # Get objects/datasets to delete (ie in the DB but not in the source)
        delete = set(guids_in_db) - set(guids_in_harvest)
        change = guids_in_db & guids_in_harvest

        log.debug('new: %s, delete: %s and change: %s', new, delete, change)
        
        ids = []
        for guid in new:
            obj = HarvestObject(guid=guid, job=harvest_job, content=json.dumps(datasets_to_harvest.get(guid)),
                                extras=[HarvestObjectExtra(key='status', value='new')])
            obj.save()
            ids.append(obj.id)
        for guid in change:
            obj = HarvestObject(guid=guid, job=harvest_job, content=json.dumps(datasets_to_harvest.get(guid)),
                                package_id=guid_to_package_id[guid],
                                extras=[HarvestObjectExtra(key='status', value='change')])
            obj.save()
            ids.append(obj.id)
        for guid in delete:
            obj = HarvestObject(guid=guid, job=harvest_job, content=json.dumps(datasets_to_harvest.get(guid)),
                                package_id=guid_to_package_id[guid],
                                extras=[HarvestObjectExtra(key='status', value='delete')])
            model.Session.query(HarvestObject).\
                  filter_by(guid=guid).\
                  update({'current': False}, False)
            obj.save()
            ids.append(obj.id)

        log.debug('Number of elements in clean_datasets: %s and object_ids: %s', len(clean_datasets), len(ids))

        return ids
    
    def fetch_stage(self, harvest_object):
        # Nothing to do here - we got the package dict in the search in the gather stage
        return True
    
    def import_stage(self, harvest_object):
        """
        Performs the import stage of the SchemingDCATXLSHarvester.

        Args:
            harvest_object (HarvestObject): The harvest object to import.

        Returns:
            bool or str: Returns True if the import is successful, 'unchanged' if the package is unchanged,
                        or False if there is an error during the import.

        Raises:
            None
        """
        log.debug('In SchemingDCATXLSHarvester import_stage')

        context = {
            'model': model,
            'session': model.Session,
            'user': self._get_user_name(),
        }
        
        if not harvest_object:
            log.error('No harvest object received')
            return False   
        
        self._set_config(harvest_object.source.config)
        
        if self.force_import:
            status = 'change'
        else:
            status = self._get_object_extra(harvest_object, 'status')

        # Get the last harvested object (if any)
        previous_object = model.Session.query(HarvestObject) \
                          .filter(HarvestObject.guid==harvest_object.guid) \
                          .filter(HarvestObject.current==True) \
                          .first()

        if status == 'delete':
            override_local_datasets = self.config.get("override_local_datasets", False)
            if override_local_datasets is True:
                # Delete package
                context.update({
                    'ignore_auth': True,
                })
                p.toolkit.get_action('package_delete')(context, {'id': harvest_object.package_id})
                log.info('The override_local_datasets configuration is %s. Package %s deleted with GUID: %s' % (override_local_datasets, harvest_object.package_id, harvest_object.guid))

                return True
            
            else:
                log.info('The override_local_datasets configuration is %s. Package %s not deleted with GUID: %s' % (override_local_datasets, harvest_object.package_id, harvest_object.guid))

                return 'unchanged'

        # Check if harvest object has a non-empty content
        if harvest_object.content is None:
            self._save_object_error('Empty content for object {0}'.format(harvest_object.id),
                                    harvest_object, 'Import')
            return False

        try:
            dataset = json.loads(harvest_object.content)
        except ValueError:
            self._save_object_error('Could not ateutil.parser.parse content for object {0}'.format(harvest_object.id),
                                    harvest_object, 'Import')
            return False

        # Check if the dataset is a harvest source and we are not allowed to harvest it
        if dataset.get('type') == 'harvest' and self.config.get('allow_harvest_datasets', False) is False:
            log.warn('Remote dataset is a harvest source and allow_harvest_datasets is False, ignoring...')
            return True

        dataset = self.modify_package_dict(dataset, harvest_object)

        # Flag previous object as not current anymore
        if previous_object and not self.force_import:
            previous_object.current = False
            previous_object.add()

        # Dataset dict::Update GUID with the identifier from the dataset
        xls_guid = dataset['identifier']
        if xls_guid and harvest_object.guid != xls_guid:
            # First make sure there already aren't current objects
            # with the same guid
            existing_object = model.Session.query(HarvestObject.id) \
                            .filter(HarvestObject.guid==xls_guid) \
                            .filter(HarvestObject.current==True) \
                            .first()
            if existing_object:
                self._save_object_error('Object {0} already has this guid {1}'.format(existing_object.id, xls_guid),
                        harvest_object, 'Import')
                return False

            harvest_object.guid = xls_guid
            harvest_object.add()

        # Assign GUID if not present (i.e. it's a manual import)
        if not harvest_object.guid:
            harvest_object.guid = xls_guid
            harvest_object.add()

        # Update dates
        self._set_basic_dates(dataset)

        harvest_object.metadata_modified_date = dataset['modified']
        harvest_object.add()

        # Build the package dict
        package_dict = self.get_package_dict(harvest_object, context, dataset)
        if not package_dict:
            log.error('No package dict returned, aborting import for object %s' % harvest_object.id)
            return False

        # Create / update the package
        context.update({
           'extras_as_string': True,
           'api_version': '2',
           'return_id_only': True})

        if self._site_user and context['user'] == self._site_user['name']:
            context['ignore_auth'] = True

        # Flag this object as the current one
        harvest_object.current = True
        harvest_object.add()

        if status == 'new':       
            # We need to explicitly provide a package ID based on uuid4 identifier created in gather_stage
            # won't be be able to link the extent to the package.
            package_dict['id'] = package_dict['identifier']

            harvester_tmp_dict = {}
            
            for harvester in p.PluginImplementations(ISchemingDCATHarvester):
                harvester.before_create(harvest_object, package_dict, harvester_tmp_dict)
            
            try:
                result = self._create_or_update_package(
                    package_dict, harvest_object, 
                    package_dict_form='package_show')

                for harvester in p.PluginImplementations(ISchemingDCATHarvester):
                    err = harvester.after_create(harvest_object, package_dict, harvester_tmp_dict)

            except p.toolkit.ValidationError as e:
                error_message = ', '.join(f'{k}: {v}' for k, v in e.error_dict.items())
                self._save_object_error(f'Validation Error: {error_message}', harvest_object, 'Import')
                return False

        elif status == 'change':

            # Check if the modified date is more recent
            if not self.force_import and previous_object and dateutil.parser.parse(harvest_object.metadata_modified_date) <= previous_object.metadata_modified_date:

                log.info('Package with GUID: %s unchanged, skipping...' % harvest_object.guid)
                return 'unchanged'
            else:
                package_schema = logic.schema.default_update_package_schema()
                for harvester in p.PluginImplementations(ISchemingDCATHarvester):
                    package_schema = harvester.update_package_schema_for_update(package_schema)
                context['schema'] = package_schema

                package_dict['id'] = harvest_object.package_id
                try:
                    result = self._create_or_update_package(
                        package_dict, harvest_object, 
                        package_dict_form='package_show')
                    
                    for harvester in p.PluginImplementations(ISchemingDCATHarvester):
                        err = harvester.after_update(harvest_object, package_dict, harvester_tmp_dict)

                        if err:
                            self._save_object_error(f'XLSHarvester plugin error: {err}', harvest_object, 'Import')
                            return False

                    log.info('Updated package %s with GUID: %s' % (package_dict["id"], harvest_object.guid))
                    
                except p.toolkit.ValidationError as e:
                    error_message = ', '.join(f'{k}: {v}' for k, v in e.error_dict.items())
                    self._save_object_error(f'Validation Error: {error_message}', harvest_object, 'Import')
                    return False

        return result
