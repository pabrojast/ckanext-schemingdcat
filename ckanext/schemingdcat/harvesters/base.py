import logging
import uuid
from functools import lru_cache
import json
import os
import re
from datetime import datetime
from dateutil.parser import parse
import six
import hashlib

import urllib.request
from urllib.error import URLError, HTTPError

import ckan.logic as logic
from ckan.model import Session
from ckan.logic.schema import default_create_package_schema
from ckan.lib.navl.validators import ignore_missing, ignore
from ckan import plugins as p
from ckan import model
from ckantoolkit import config

from ckanext.harvest.harvesters import HarvesterBase
from ckanext.harvest.logic.schema import unicode_safe
from ckanext.harvest.model import HarvestObject, HarvestObjectExtra

from ckanext.schemingdcat.config import (
    OGC2CKAN_HARVESTER_MD_CONFIG,
    OGC2CKAN_MD_FORMATS,
    DATE_FIELDS,
    DATASET_DEFAULT_FIELDS,
    RESOURCE_DEFAULT_FIELDS,
    CUSTOM_FORMAT_RULES,
    DATADICTIONARY_DEFAULT_SCHEMA
)

log = logging.getLogger(__name__)


class SchemingDCATHarvester(HarvesterBase):
    """
    A custom harvester for harvesting metadata using the Scheming DCAT extension.

    It extends the base `HarvesterBase` class provided by CKAN's harvest extension.
    """

    _mapped_schema = {}
    _local_schema = None
    _local_required_lang = None
    _remote_schema = None
    _local_schema_name = None
    _remote_schema_name = None
    _supported_schemas = []
    _readme = "https://github.com/mjanez/ckanext-schemingdcat?tab=readme-ov-file"
    config = None
    api_version = 2
    action_api_version = 3
    force_import = False
    _site_user = None

    def get_harvester_basic_info(self, config):
        """
        Retrieves basic information about the harvester.

        Args:
            config (str): The configuration in JSON format.

        Returns:
            dict: The configuration object parsed from the JSON.

        Raises:
            ValueError: If the configuration is empty or not in valid JSON format.
        """
        if not config:
            readme_doc = self.info().get("about_url", self._readme)
            raise ValueError(
                f"Configuration must be a JSON. Check README: {readme_doc}"
            )

        # Get local schema
        self._get_local_schemas_supported()

        if self._local_schema_name is not None and not config:
            return json.dumps(self._local_schema)

        # Load the configuration
        try:
            config_obj = json.loads(config)

        except ValueError as e:
            raise ValueError(f"Unable to load configuration: {e}")

        return config_obj

    def _set_config(self, config_str):
        """
        Sets the configuration for the harvester.

        Args:
            config_str (str): A JSON string representing the configuration.

        Returns:
            None
        """
        if config_str:
            self.config = json.loads(config_str)
            self.api_version = int(self.config.get("api_version", self.api_version))
        else:
            self.config = {}

    def _set_basic_validate_config(self, config):
        """
        Validates and sets the basic configuration for the harvester.

        Args:
            config (str): The configuration string in JSON format.

        Returns:
            str: The validated and updated configuration string.

        Raises:
            ValueError: If the configuration is invalid.

        """
        if not config:
            return config

        try:
            config_obj = json.loads(config)
            if "api_version" in config_obj:
                try:
                    int(config_obj["api_version"])
                except ValueError:
                    raise ValueError("api_version must be an integer")

            if "default_tags" in config_obj:
                if not isinstance(config_obj["default_tags"], list):
                    raise ValueError("default_tags must be a list")
                if config_obj["default_tags"] and not isinstance(
                    config_obj["default_tags"][0], dict
                ):
                    raise ValueError("default_tags must be a list of dictionaries")

            if "default_groups" in config_obj:
                if not isinstance(config_obj["default_groups"], list):
                    raise ValueError(
                        "default_groups must be a *list* of group names/ids"
                    )
                if config_obj["default_groups"] and not isinstance(
                    config_obj["default_groups"][0], str
                ):
                    raise ValueError(
                        "default_groups must be a list of group names/ids (i.e. strings)"
                    )

                # Check if default groups exist
                context = {"model": model, "user": p.toolkit.c.user}
                config_obj["default_group_dicts"] = []
                for group_name_or_id in config_obj["default_groups"]:
                    try:
                        group = logic.get_action("group_show")(
                            context, {"id": group_name_or_id}
                        )
                        # save the dict to the config object, as we'll need it
                        # in the import_stage of every dataset
                        config_obj["default_group_dicts"].append(
                            {"id": group["id"], "name": group["name"]}
                        )
                    except logic.NotFound:
                        raise ValueError("Default group not found")
                config = json.dumps(config_obj)

            if "default_extras" in config_obj:
                if not isinstance(config_obj["default_extras"], dict):
                    raise ValueError("default_extras must be a dictionary")

            if "user" in config_obj:
                # Check if user exists
                context = {"model": model, "user": p.toolkit.c.user}
                try:
                    logic.get_action("user_show")(
                        context, {"id": config_obj.get("user")}
                    )
                except logic.NotFound:
                    raise ValueError("User not found")

            for key in ("read_only", "force_all", "override_local_datasets"):
                if key in config_obj:
                    if not isinstance(config_obj[key], bool):
                        raise ValueError("%s must be boolean" % key)

        except ValueError as e:
            raise e

        return config

    @lru_cache(maxsize=None)
    def _get_local_schema(self, schema_type="dataset"):
        """
        Retrieves the schema for the dataset instance and caches it using the LRU cache decorator for efficient retrieval.

        Args:
            schema_type (str, optional): The type of schema to retrieve. Defaults to 'dataset'.

        Returns:
            dict: The schema of the dataset instance.
        """
        return logic.get_action("scheming_dataset_schema_show")(
            {}, {"type": schema_type}
        )

    @lru_cache(maxsize=None)
    def _get_remote_schema(self, base_url, schema_type="dataset"):
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
        url = (
            base_url
            + self._get_action_api_offset()
            + "/scheming_dataset_schema_show?type="
            + schema_type
        )
        try:
            content = self._get_content(url)
            content_dict = json.loads(content)
            return content_dict["result"]
        except (HarvesterBase.ContentFetchError, ValueError, KeyError):
            log.debug("Could not fetch/decode remote schema")
            raise HarvesterBase.RemoteResourceError(
                "Could not fetch/decode remote schema"
            )

    def _get_local_required_lang(self):
        """
        Retrieves the required language for the local schema.

        Returns:
            str: The required language for the local schema.
        """
        if self._local_schema is None:
            self._local_schema = self._get_local_schema()

        if self._local_required_lang is None:
            self._local_required_lang = self._local_schema.get(
                "required_language", None
            )

        return self._local_required_lang

    def _get_local_schemas_supported(self):
        """
        Retrieves the local schema supported by the harvester.

        Returns:
            list: A list of supported local schema names.
        """

        if self._local_schema is None:
            self._local_schema = self._get_local_schema()

        if self._local_schema_name is None:
            self._local_schema_name = self._local_schema.get("schema_name", None)

        if self._local_required_lang is None:
            self._local_required_lang = self._get_local_required_lang()

        # Get the set of available schemas
        # self._supported_schemas = set(schemingdcat_get_schema_names())
        self._supported_schemas.append(self._local_schema_name)

    def _get_object_extra(self, harvest_object, key):
        """
        Helper function for retrieving the value from a harvest object extra,
        given the key
        """
        for extra in harvest_object.extras:
            if extra.key == key:
                return extra.value
        return None

    def _get_dict_value(self, _dict, key, default=None):
        """
        Returns the value for the given key on a CKAN dict

        By default a key on the root level is checked. If not found, extras
        are checked.

        If not found, returns the default value, which defaults to None
        """

        if key in _dict:
            return _dict[key]

        for extra in _dict.get("extras", []):
            if extra["key"] == key:
                return extra["value"]

        return default

    def _generate_identifier(self, dataset_dict):
        """
        Generate a unique identifier for a dataset based on its attributes. First checks if the 'identifier' attribute exists in the dataset_dict. If not, it generates a unique identifier based on the 'inspire_id' or 'title' attributes.

        Args:
            dataset_dict (dict): The dataset object containing attributes like 'identifier', 'inspire_id', and 'title'.

        Returns:
            str: The generated unique identifier for the dataset_dict.

        Raises:
            ValueError: If neither 'inspire_id' nor 'title' is a string or does not exist in the dataset_dict.
        """
        identifier_source = self._get_dict_value(dataset_dict, "identifier") or None

        if identifier_source:
            return identifier_source
        elif dataset_dict.get("inspire_id") and isinstance(
            dataset_dict["inspire_id"], str
        ):
            identifier_source = dataset_dict["inspire_id"]
        elif dataset_dict.get("title") and isinstance(dataset_dict["title"], str):
            identifier_source = dataset_dict["title"]

        if identifier_source:
            # Convert to lowercase, replace all spaces with '-'
            joined_words = "-".join(identifier_source.lower().split())
            # Generate a SHA256 hash of the joined words
            hash_value = hashlib.sha256(joined_words.encode("utf-8")).hexdigest()
            # Generate a UUID based on the SHA256 hash
            return str(uuid.uuid5(uuid.NAMESPACE_DNS, hash_value))
        else:
            raise ValueError(
                "Dataset identifier could not be generated. Need at least: inspire_id or title"
            )

    def _get_guid(self, dataset_dict, source_url=None):
        """
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
        """
        guid = None

        guid = self._get_dict_value(dataset_dict, "uri") or self._get_dict_value(
            dataset_dict, "identifier"
        )
        if guid:
            return guid

        if dataset_dict.get("name"):
            guid = dataset_dict["name"]
            if source_url:
                guid = source_url.rstrip("/") + "/" + guid

        if not guid:
            guid = str(uuid.uuid4())

        return guid

    def _validate_remote_schema(
        self,
        remote_ckan_base_url=None,
        remote_dataset_field_names=None,
        remote_resource_field_names=None,
        remote_dataset_field_mapping=None,
        remote_resource_field_mapping=None,
    ):
        """
        Validates the remote schema by comparing it with the local schema.

        Args:
            remote_ckan_base_url (str, optional): The base URL of the remote CKAN instance. If provided, the remote schema will be fetched from this URL.
            remote_dataset_field_names (set, optional): The field names of the remote dataset schema. If provided, the remote schema will be validated using these field names.
            remote_resource_field_names (set, optional): The field names of the remote resource schema. If provided, the remote schema will be validated using these field names.
            remote_dataset_field_mapping (dict, optional): A mapping of local dataset field names to remote dataset field names. If provided, the local dataset fields will be mapped to the corresponding remote dataset fields.
            remote_resource_field_mapping (dict, optional): A mapping of local resource field names to remote resource field names. If provided, the local resource fields will be mapped to the corresponding remote resource fields.

        Returns:
            bool: True if the remote schema is valid, False otherwise.

        Raises:
            RemoteSchemaError: If there is an error validating the remote schema.

        """
        try:
            if self._local_schema is None:
                self._local_schema = self._get_local_schema()

            if self._local_required_lang is None:
                self._local_required_lang = self._get_local_required_lang()

            local_datasets_colnames = set(
                field["field_name"] for field in self._local_schema["dataset_fields"]
            )
            local_distributions_colnames = set(
                field["field_name"] for field in self._local_schema["resource_fields"]
            )

            if remote_ckan_base_url is not None:
                log.debug("Validating remote schema from: %s", remote_ckan_base_url)
                if self._remote_schema is None:
                    self._remote_schema = self._get_remote_schema(remote_ckan_base_url)

                remote_datasets_colnames = set(
                    field["field_name"]
                    for field in self._remote_schema["dataset_fields"]
                )
                remote_distributions_colnames = set(
                    field["field_name"]
                    for field in self._remote_schema["resource_fields"]
                )

            elif remote_dataset_field_names is not None:
                log.debug(
                    "Validating remote schema using field names from package dict"
                )
                remote_datasets_colnames = remote_dataset_field_names
                remote_distributions_colnames = remote_resource_field_names

            datasets_diff = local_datasets_colnames - remote_datasets_colnames
            distributions_diff = (
                local_distributions_colnames - remote_distributions_colnames
            )

            def get_mapped_fields(fields, field_mapping):
                return [
                    {
                        "local_field_name": field["field_name"],
                        "remote_field_name": field_mapping.get(
                            field["field_name"], field["field_name"]
                        )
                        if field_mapping
                        else field["field_name"],
                        "modified": field["field_name"]
                        != (
                            field_mapping.get(field["field_name"], field["field_name"])
                            if field_mapping
                            else field["field_name"]
                        ),
                        **(
                            {"form_languages": field["form_languages"]}
                            if field.get("form_languages")
                            else {}
                        ),
                        **(
                            {"required_language": field["required_language"]}
                            if field.get("required_language")
                            else {}
                        ),
                    }
                    for field in fields
                ]

            self._mapped_schema = {
                "dataset_fields": get_mapped_fields(
                    self._local_schema.get("dataset_fields", []),
                    remote_dataset_field_mapping,
                ),
                "resource_fields": get_mapped_fields(
                    self._local_schema.get("resource_fields", []),
                    remote_resource_field_mapping,
                ),
            }

            log.info("Local required language: %s", self._local_required_lang)
            log.info(
                "Field names differences in dataset: %s and resource: %s",
                datasets_diff,
                distributions_diff,
            )
            log.info("Mapped schema: %s", self._mapped_schema)

        except SearchError as e:
            raise RemoteSchemaError("Error validating remote schema: %s" % str(e))

        return True

    def _remove_duplicate_keys_in_extras(self, dataset_dict):
        """
        Remove duplicate keys in the 'extras' list of dictionaries of the given dataset_dict.

        Args:
            dataset_dict (dict): The dataset dictionary.

        Returns:
            dict: The updated dataset dictionary with duplicate keys removed from the 'extras' list of dictionaries.
        """
        common_keys = set(
            extra["key"] for extra in dataset_dict["extras"]
        ).intersection(dataset_dict)
        dataset_dict["extras"] = [
            extra for extra in dataset_dict["extras"] if extra["key"] not in common_keys
        ]

        return dataset_dict

    def _check_url(self, url, harvest_job):
        """
        Check if the given URL is valid and accessible.

        Args:
            url (str): The URL to check.
            harvest_job (HarvestJob): The harvest job associated with the URL.

        Returns:
            bool: True if the URL is valid and accessible, False otherwise.
        """
        if not url.lower().startswith("http"):
            # Check local file
            if os.path.exists(url):
                return True
            else:
                self._save_gather_error(
                    "Could not get content for this url", harvest_job
                )
                return False

        try:
            # Open the URL without downloading the content
            urllib.request.urlopen(url)

            # If no exception was thrown, the URL is valid
            return True

        except HTTPError as e:
            msg = f"Could not get content from {url} because the connection timed out. {e}"
            self._save_gather_error(msg, harvest_job)
            return False
        except URLError as e:
            msg = """Could not get content from %s because a
                                connection error occurred. %s""" % (url, e)
            self._save_gather_error(msg, harvest_job)
            return False
        except FileNotFoundError:
            msg = "File %s not found." % url
            self._save_gather_error(msg, harvest_job)
            return False

    def _get_content_and_type(self, url, harvest_job, content_type=None):
        """
        Retrieves the content and content type from a given URL.

        Args:
            url (str): The URL to retrieve the content from.
            harvest_job (HarvestJob): The harvest job associated with the URL.
            content_type (str, optional): The expected content type. Defaults to None.

        Returns:
            tuple: A tuple containing the content and content type.
                   If an error occurs, returns None, None.
        """
        if not url.lower().startswith("http"):
            # Check local file
            if os.path.exists(url):
                with open(url, "r") as f:
                    content = f.read()
                content_type = content_type or "xlsx"
                return content, content_type
            else:
                self._save_gather_error(
                    "Could not get content for this url", harvest_job
                )
                return None, None

        try:
            log.debug("Getting file %s", url)

            # Retrieve the file and the response headers
            content, headers = urllib.request.urlretrieve(url)

            # Get the content type from the headers
            content_type = headers.get_content_type()

        except HTTPError as e:
            msg = f"Could not get content from {url} because the connection timed out. {e}"
            self._save_gather_error(msg, harvest_job)
            return None, None
        except URLError as e:
            msg = """Could not get content from %s because a
                                connection error occurred. %s""" % (url, e)
            self._save_gather_error(msg, harvest_job)
            return None, None
        except FileNotFoundError:
            msg = "File %s not found." % url
            self._save_gather_error(msg, harvest_job)
            return None, None

        return True

    # TODO: Implement this method
    def _load_datadictionaries(self, harvest_job, datadictionaries):
        return True

    def _find_existing_package_by_field_name(
        self, package_dict, field_name, return_fields=None
    ):
        """
        Find an existing package by a specific field name.

        Args:
            package_dict (dict): The package dictionary containing the field name.
            field_name (str): The name of the field to search for.
            return_fields (list, optional): List of fields to return. Defaults to None.

        Returns:
            dict: The existing package dictionary matching the field name.

        This method searches for an existing package in the CKAN instance based on its specific id. It takes a package dictionary and a field name as input parameters. The package dictionary should contain the field name to search for. The method returns the existing package dictionary that matches the field name. https://docs.ckan.org/en/2.9/api/#ckan.logic.action.get.package_search
        """
        data_dict = {
            "fq": f"{field_name}:{package_dict[field_name]}",
            "include_private": True,
        }

        if return_fields and isinstance(return_fields, list):
            data_dict["fl"] = ",".join(
                field
                if isinstance(field, str) and field == field.strip()
                else str(field).strip()
                for field in return_fields
            )

        package_search_context = {
            "model": model,
            "session": Session,
            "ignore_auth": True,
        }

        try:
            return logic.get_action("package_search")(package_search_context, data_dict)
        except p.toolkit.ObjectNotFound:
            pass

    def _check_existing_package_by_ids(self, package_dict):
        """
        Check if a package with the given identifiers already exists in the CKAN instance.

        Args:
            package_dict (dict): A dictionary containing the package information.

        Returns:
            package (dict or None): The existing package dictionary if found, None otherwise.
        """
        basic_id_fields = [
            "name",
            "id",
            "identifier",
            "alternate_identifier",
            "inspire_id",
        ]
        for field_name in basic_id_fields:
            if package_dict.get(field_name):
                package = self._find_existing_package_by_field_name(
                    package_dict, field_name
                )
                if package["results"] and package["results"][0]:
                    return package["results"][0]

        # If no existing package was found after checking all fields, return None
        return None

    def _set_translated_fields(self, package_dict):
        """
        Sets translated fields in the package dictionary based on the mapped schema.

        Args:
            package_dict (dict): The package dictionary to update with translated fields.

        Returns:
            dict: The updated package dictionary.

        Raises:
            ReadError: If there is an error translating the dataset.

        """
        basic_fields = [
            "id",
            "name",
            "title",
            "title_translated",
            "notes_translated",
            "provenance",
            "notes",
            "provenance",
            "private",
            "groups",
            "tags",
            "tag_string",
            "owner_org",
        ]
        if (
            not hasattr(self, "_mapped_schema")
            or "dataset_fields" not in self._mapped_schema
            or "resource_fields" not in self._mapped_schema
        ):
            return package_dict
        try:
            translated_fields = {"dataset_fields": [], "resource_fields": []}
            for field in self._mapped_schema["dataset_fields"]:
                if field.get("modified", True):
                    local_field_name = field["local_field_name"]
                    remote_field_name = field["remote_field_name"]

                    translated_fields["dataset_fields"].append(local_field_name)

                    if isinstance(remote_field_name, dict):
                        package_dict[local_field_name] = {
                            lang: package_dict.get(name, None)
                            for lang, name in remote_field_name.items()
                        }
                    else:
                        package_dict[local_field_name] = package_dict.get(
                            remote_field_name, None
                        )

            if package_dict["resources"]:
                for resource in package_dict["resources"]:
                    for field in self._mapped_schema["resource_fields"]:
                        if field.get("modified", True):
                            local_field_name = field["local_field_name"]
                            remote_field_name = field["remote_field_name"]

                            translated_fields["resource_fields"].append(
                                local_field_name
                            )

                            if isinstance(remote_field_name, dict):
                                package_dict[local_field_name] = {
                                    lang: resource.get(name, None)
                                    for lang, name in remote_field_name.items()
                                }
                            else:
                                package_dict[local_field_name] = resource.get(
                                    remote_field_name, None
                                )

            # log.debug('Translated fields: %s', translated_fields)

        except Exception as e:
            raise ReadError(
                "Error translating dataset: %s. Error: %s"
                % (package_dict["title"], str(e))
            )

        return package_dict

    # TODO: Fix this method
    def _get_allowed_values(self, field_name, field_type="dataset_fields"):
        """
        Get the allowed values for a given field name.

        Args:
            field_name (str): The name of the field.
            field_type (str, optional): The type of the field. Defaults to 'dataset_fields'.

        Returns:
            list: A list of allowed values for the field.
        """
        # Check if field_type is valid
        if field_type not in ["dataset_fields", "resource_fields"]:
            field_type = "dataset_fields"

        # Get the allowed values from the local schema
        allowed_values = [
            choice["value"]
            for field in self._local_schema[field_type]
            if field["field_name"] == field_name
            for choice in field.get("choices", [])
        ]
        return allowed_values

    def _set_basic_dates(self, package_dict):
        """
        Sets the basic dates for the package.

        Args:
            package_dict (dict): The package dictionary.

        Returns:
            None
        """
        issued_date = self._normalize_date(
            package_dict["issued"], self._source_date_format
        ) or datetime.now().strftime("%Y-%m-%d")

        for date_field in DATE_FIELDS:
            if date_field["override"]:
                field_name = date_field["field_name"]
                fallback = date_field["fallback"] or date_field["default_value"]

                fallback_date = (
                    issued_date
                    if fallback and fallback == "issued"
                    else self._normalize_date(package_dict.get(fallback), self._source_date_format)
                )
                log.debug(['%s: %s', field_name, package_dict[field_name]])
                package_dict[field_name] = (
                    self._normalize_date(package_dict.get(field_name), self._source_date_format) or fallback_date
                )

                if field_name == "issued":
                    package_dict["extras"].append(
                        {"key": "issued", "value": package_dict[field_name]}
                    )

    @staticmethod
    def _normalize_date(date, source_date_format=None):
        """
        Normalize the given date to the format 'YYYY-MM-DD'.

        Args:
            date (str or datetime): The date to be normalized.
            source_date_format (str): The format of the source date.

        Returns:
            str: The normalized date in the format 'YYYY-MM-DD', or None if the date cannot be normalized.

        """
        if date is None:
            return None

        if isinstance(date, str):
            try:
                #log.debug('normalize_date STR: %s', date)
                if source_date_format:
                    date = datetime.strptime(date, source_date_format).strftime("%Y-%m-%d")
                else:
                    date = parse(date).strftime("%Y-%m-%d")
            except ValueError:
                log.error('normalize_date failed for: %s', date)
                return None
        elif isinstance(date, datetime):
            date = date.strftime("%Y-%m-%d")
        
        #log.debug('normalize_date: %s', date)
        return date

    def _set_package_dict_default_values(self, package_dict, harvest_object, context):
        """
        Sets default values for the given package_dict based on the configuration.

        Args:
            package_dict (dict): The package_dict to set default values for.
            harvest_object (object): The harvest object associated with the package_dict.
            context (dict): The context for the action.

        Returns:
            dict: The package_dict with default values set.
        """
        package_dict, existing_tags_ids = self._set_ckan_tags(package_dict)

        # Check if 'default_tags' exists
        default_tags = self.config.get("default_tags", [])
        if default_tags:
            for tag in default_tags:
                if tag["name"] not in existing_tags_ids:
                    package_dict["tags"].append(tag)
                    existing_tags_ids.add(tag["name"])

        # Local harvest source organization
        source_package_dict = p.toolkit.get_action("package_show")(
            context.copy(), {"id": harvest_object.source.id}
        )
        local_org = source_package_dict.get("owner_org")
        package_dict["owner_org"] = local_org

        # TODO: Better using DATASET_DEFAULT_FIELDS
        # Default license https://creativecommons.org/licenses/by/4.0/
        package_dict["license_id"] = OGC2CKAN_HARVESTER_MD_CONFIG["license_id"]
        package_dict["license"] = OGC2CKAN_HARVESTER_MD_CONFIG["license"]

        # Rights and status
        if "access_rights" not in package_dict or not package_dict["access_rights"]:
            package_dict["access_rights"] = OGC2CKAN_HARVESTER_MD_CONFIG[
                "access_rights"
            ]
        if "status" not in package_dict or not package_dict["status"]:
            package_dict["status"] = OGC2CKAN_HARVESTER_MD_CONFIG["status"]

        # Default topic and themes
        if "topic" not in package_dict or not package_dict["topic"]:
            package_dict["topic"] = OGC2CKAN_HARVESTER_MD_CONFIG["topic"]
        if "theme" not in package_dict or not package_dict["theme"]:
            package_dict["theme"] = OGC2CKAN_HARVESTER_MD_CONFIG["theme"]
        if "theme_eu" not in package_dict or not package_dict["theme_eu"]:
            package_dict["theme_eu"] = OGC2CKAN_HARVESTER_MD_CONFIG["theme_eu"]

        # Prepare groups
        cleaned_groups = self._set_ckan_groups(package_dict.get("groups", []))
        default_groups = self.config.get("default_groups", [])
        if default_groups:
            cleaned_default_groups = self._set_ckan_groups(default_groups)
            #log.debug("cleaned_default_groups: %s", cleaned_default_groups)
            existing_group_ids = set(g["name"] for g in cleaned_groups)
            for group in cleaned_default_groups:
                if group["name"] not in existing_group_ids:
                    cleaned_groups.append(group)

        package_dict["groups"] = cleaned_groups

        # Set default extras if needed
        default_extras = self.config.get("default_extras", {})

        def get_extra(key, package_dict):
            for extra in package_dict.get("extras", []):
                if extra["key"] == key:
                    return extra

        if default_extras:
            override_extras = self.config.get("override_extras", False)
            if "extras" not in package_dict:
                package_dict["extras"] = []
            for key, value in default_extras.items():
                existing_extra = get_extra(key, package_dict)
                if existing_extra and not override_extras:
                    continue  # no need for the default
                if existing_extra:
                    package_dict["extras"].remove(existing_extra)
                # Look for replacement strings
                if isinstance(value, str):
                    value = value.format(
                        harvest_source_id=harvest_object.job.source.id,
                        harvest_source_url=harvest_object.job.source.url.strip("/"),
                        harvest_source_title=harvest_object.job.source.title,
                        harvest_job_id=harvest_object.job.id,
                        harvest_object_id=harvest_object.id,
                        dataset_id=package_dict["id"],
                    )

                package_dict["extras"].append({"key": key, "value": value})

        # Resources defaults
        if package_dict["resources"]:
            package_dict["resources"] = [
                self._update_resource_dict(resource)
                for resource in package_dict["resources"]
            ]

        # log.debug('package_dict default values: %s', package_dict)
        return package_dict

    def _update_resource_dict(self, resource):
        """
        Update the given resource dictionary with default values and normalize date fields.

        Args:
            resource (dict): The resource dictionary to be updated.

        Returns:
            dict: The updated resource dictionary in CKAN format.
        """
        for field in RESOURCE_DEFAULT_FIELDS:
            field_name = field["field_name"]
            fallback = field["fallback"] or field["default_value"]

            if field_name == "size" and field_name is not None:
                if "size" in resource and isinstance(resource["size"], str):
                    resource["size"] = resource["size"].replace(".", "")
                    resource["size"] = (
                        int(resource["size"]) if resource["size"].isdigit() else 0
                    )

            if field_name not in resource or resource[field_name] is None:
                resource[field_name] = fallback

        for field in DATE_FIELDS:
            if field["override"]:
                field_name = field["field_name"]
                if field_name in resource and resource[field_name]:
                    resource[field_name] = self._normalize_date(resource[field_name], self._source_date_format)

        return self._get_ckan_format(resource)

    def _set_ckan_tags(self, package_dict, tag_fields=["tag_string", "keywords"]):
        """
        Process the tags from the provided sources.

        Args:
            package_dict (dict): The package dictionary containing the information.
            tag_fields (list): The list of sources to check for tags. Default: ['tag_string', 'keywords']

        Returns:
            list: A list of processed tags.
        """
        if "tags" not in package_dict:
            package_dict["tags"] = []

        existing_tags_ids = set(t["name"] for t in package_dict["tags"])

        for source in tag_fields:
            if source in package_dict:
                tags = package_dict.get(source, [])
                if isinstance(tags, dict):
                    tags = tags
                elif isinstance(tags, list):
                    tags = [{"name": tag} for tag in tags]
                elif isinstance(tags, str):
                    tags = [{"name": tags}]
                else:
                    raise ValueError("Unsupported type for tags")
                cleaned_tags = self._clean_tags(tags)

                for tag in cleaned_tags:
                    if tag["name"] not in existing_tags_ids:
                        package_dict["tags"].append(tag)
                        existing_tags_ids.add(tag["name"])

        # Remove tag_fields from package_dict
        for field in tag_fields:
            package_dict.pop(field, None)

        return package_dict, existing_tags_ids

    @staticmethod
    def _set_ckan_groups(groups):
        """
        Sets the CKAN groups based on the provided package dictionary.

        Args:
            groups (list): The package dictionary containing the information.

        Returns:
            list: A list of CKAN groups.

        """
        # Normalize groups for CKAN
        if isinstance(groups, str):
            # If groups is a string, split it into a list
            groups = groups.split(",")
        elif isinstance(groups, list):
            # If groups is a list of dictionaries, extract 'name' from each dictionary
            if all(isinstance(item, dict) for item in groups):
                groups = [group.get('name', '') for group in groups]
            # If groups is a list but not of dictionaries, keep it as it is
        else:
            # If groups is neither a list nor a string, return an empty list
            return []

        # Create ckan_groups
        ckan_groups = [{"name": g.lower().replace(" ", "-").strip()} for g in groups]

        return ckan_groups

    @staticmethod
    def _update_custom_format(res_format, url=None, **args):
        """Update the custom format based on custom rules.

        The function checks the format and URL against a set of custom rules (CUSTOM_FORMAT_RULES). If a rule matches,
        the format is updated according to that rule. This function is designed to be easily
        extendable with new rules.

        Args:
            res_format (str): The custom format to update.
            url (str, optional): The URL to check. Defaults to None.
            **args: Additional arguments that are ignored.

        Returns:
            str: The updated custom format.
        """
        for rule in CUSTOM_FORMAT_RULES:
            if (
                any(string in res_format for string in rule["format_strings"])
                or rule["url_string"] in url
            ):
                res_format = rule["new_format"]
                break

        return res_format.upper()

    def _get_ckan_format(self, resource):
        """Get the CKAN format information for a distribution.

        Args:
            resource (dict): A dictionary containing information about the distribution.

        Returns:
            dict: The updated distribution information.
        """

        if isinstance(resource["format"], str):
            informat = resource["format"].lower()
        else:
            informat = "".join(
                str(value)
                for key, value in resource.items()
                if key in ["title", "url", "description"] and isinstance(value, str)
            ).lower()
            informat = next(
                (key for key in OGC2CKAN_MD_FORMATS if key.lower() in informat),
                resource.get("url", "").lower(),
            )

        # Check if _update_custom_format
        informat = self._update_custom_format(informat.lower(), resource.get("url", ""))

        if informat is not None:
            resource["format"] = informat

        return resource

    def _clean_tags(self, tags):
        """
        Cleans the names of tags.

        Each keyword is cleaned by removing non-alphanumeric characters,
        allowing only: a-z, ñ, 0-9, _, -, ., and spaces, and truncating to a
        maximum length of 100 characters.

        Args:
            tags (list): The tags to be cleaned. Each keyword is a
            dictionary with a 'name' key.

        Returns:
            list: A list of dictionaries with cleaned keyword names.
        """
        cleaned_tags = [
            {"name": self._clean_name(k["name"]), "display_name": k["name"]}
            for k in tags
            if k and "name" in k
        ]

        return cleaned_tags

    @staticmethod
    def _clean_name(name):
        """
        Cleans a name by removing accents, special characters, and spaces.

        Args:
            name (str): The name to clean.

        Returns:
            str: The cleaned name.
        """
        # Define a dictionary to map accented characters to their unaccented equivalents except ñ
        accent_map = {
            "á": "a",
            "é": "e",
            "í": "i",
            "ó": "o",
            "ú": "u",
            "ü": "u",
            "ñ": "ñ",
        }

        # Replace accented and special characters with their unaccented equivalents or -
        name = "".join(accent_map.get(c, c) for c in name)
        name = re.sub(r"[^a-zñ0-9_.-]", "-", name.lower().strip())

        # Truncate the name to 40 characters
        name = name[:40]

        return name

    def _create_or_update_package(
        self, package_dict, harvest_object, package_dict_form="rest"
    ):
        """
        Creates a new package or updates an existing one according to the
        package dictionary provided.

        The package dictionary can be in one of two forms:

        1. 'rest' - as seen on the RESTful API:

                http://datahub.io/api/rest/dataset/1996_population_census_data_canada

           This is the legacy form. It is the default to provide backward
           compatibility.

           * 'extras' is a dict e.g. {'theme': 'health', 'sub-theme': 'cancer'}
           * 'tags' is a list of strings e.g. ['large-river', 'flood']

        2. 'package_show' form, as provided by the Action API (CKAN v2.0+):

               http://datahub.io/api/action/package_show?id=1996_population_census_data_canada

           * 'extras' is a list of dicts
                e.g. [{'key': 'theme', 'value': 'health'},
                        {'key': 'sub-theme', 'value': 'cancer'}]
           * 'tags' is a list of dicts
                e.g. [{'name': 'large-river'}, {'name': 'flood'}]

        Note that the package_dict must contain an id, which will be used to
        check if the package needs to be created or updated (use the remote
        dataset id).

        If the remote server provides the modification date of the remote
        package, add it to package_dict['metadata_modified'].

        :returns: The same as what import_stage should return. i.e. True if the
                  create or update occurred ok, 'unchanged' if it didn't need
                  updating or False if there were errors.


        TODO: Not sure it is worth keeping this function. If useful it should
        use the output of package_show logic function (maybe keeping support
        for rest api based dicts
        """
        assert package_dict_form in ("rest", "package_show")
        try:
            if package_dict is None:
                pass

            # Change default schema
            schema = default_create_package_schema()
            schema["id"] = [ignore_missing, unicode_safe]
            schema["__junk"] = [ignore]

            # Check API version
            if self.config:
                try:
                    api_version = int(self.config.get("api_version", 2))
                except ValueError:
                    raise ValueError("api_version must be an integer")
            else:
                api_version = 2

            user_name = self._get_user_name()
            context = {
                "model": model,
                "session": Session,
                "user": user_name,
                "api_version": api_version,
                "schema": schema,
                "ignore_auth": True,
            }

            if self.config and self.config.get("clean_tags", True):
                tags = package_dict.get("tags", [])
                package_dict["tags"] = self._clean_tags(tags)

            # Check if package exists. Can be overridden if necessary
            existing_package_dict = self._check_existing_package_by_ids(package_dict)

            # Flag this object as the current one
            harvest_object.current = True
            harvest_object.add()

            if existing_package_dict is not None:
                package_dict["id"] = existing_package_dict["id"]
                log.debug(
                    "existing_package_dict title: %s and ID: %s",
                    existing_package_dict["title"],
                    existing_package_dict["id"],
                )

                # In case name has been modified when first importing. See issue #101.
                package_dict["name"] = existing_package_dict["name"]

                # Check modified date
                if "metadata_modified" not in package_dict or package_dict[
                    "metadata_modified"
                ] > existing_package_dict.get("metadata_modified"):
                    log.info(
                        "Package ID: %s with GUID: %s exists and needs to be updated",
                        package_dict["id"],
                        harvest_object.guid,
                    )
                    # Update package
                    context.update({"id": package_dict["id"]})

                    # Map existing resource URLs to their resources
                    existing_resources = {
                        resource["url"]: resource["modified"]
                        for resource in existing_package_dict.get("resources", [])
                        if "modified" in resource
                    }

                    new_resources = existing_package_dict.get("resources", []).copy()
                    for resource in package_dict.get("resources", []):
                        # If the resource URL is in existing_resources and the resource's
                        # modification date is more recent, update the resource in new_resources
                        if (
                            "url" in resource
                            and resource["url"] in existing_resources
                            and "modified" in resource
                            and parse(resource["modified"]) > parse(existing_resources[resource["modified"]])
                        ):
                            # Find the index of the existing resource in new_resources
                            index = next(i for i, r in enumerate(new_resources) if r["url"] == resource["url"])
                            # Replace the existing resource with the new resource
                            new_resources[index] = resource
                        # If the resource URL is not in existing_resources, add the resource to new_resources
                        elif "url" in resource and resource["url"] not in existing_resources:
                            new_resources.append(resource)

                    package_dict["resources"] = new_resources

                    for field in p.toolkit.aslist(
                        config.get("ckan.harvest.not_overwrite_fields")
                    ):
                        if field in existing_package_dict:
                            package_dict[field] = existing_package_dict[field]
                    try:
                        package_id = p.toolkit.get_action("package_update")(
                            context, package_dict
                        )
                        log.info(
                            "Updated package: %s with GUID: %s",
                            package_id,
                            harvest_object.guid,
                        )
                    except p.toolkit.ValidationError as e:
                        error_message = ", ".join(
                            f"{k}: {v}" for k, v in e.error_dict.items()
                        )
                        self._save_object_error(
                            f"Validation Error: {error_message}",
                            harvest_object,
                            "Import",
                        )
                        return False

                else:
                    log.info(
                        "No changes to package with GUID: %s, skipping..."
                        % harvest_object.guid
                    )
                    # NB harvest_object.current/package_id are not set
                    return "unchanged"

                # Flag this as the current harvest object
                harvest_object.package_id = package_dict["id"]
                harvest_object.save()

            else:
                # Package needs to be created
                package_dict["id"] = package_dict["identifier"]

                # Get rid of auth audit on the context otherwise we'll get an
                # exception
                context.pop("__auth_audit", None)

                # Set name for new package to prevent name conflict, see issue #117
                if package_dict.get("name", None):
                    package_dict["name"] = self._gen_new_name(package_dict["name"])
                else:
                    package_dict["name"] = self._gen_new_name(package_dict["title"])

                log.info(
                    "Created new package ID: %s with GUID: %s",
                    package_dict["id"],
                    harvest_object.guid,
                )

                # log.debug('Package: %s', package_dict)
                harvest_object.package_id = package_dict["id"]
                # Defer constraints and flush so the dataset can be indexed with
                # the harvest object id (on the after_show hook from the harvester
                # plugin)
                harvest_object.add()

                model.Session.execute(
                    "SET CONSTRAINTS harvest_object_package_id_fkey DEFERRED"
                )
                model.Session.flush()

                try:
                    new_package = p.toolkit.get_action("package_create")(
                        context, package_dict
                    )
                    log.info(
                        "Created new package: %s with GUID: %s",
                        new_package["name"],
                        harvest_object.guid,
                    )
                except p.toolkit.ValidationError as e:
                    error_message = ", ".join(
                        f"{k}: {v}" for k, v in e.error_dict.items()
                    )
                    self._save_object_error(
                        f"Validation Error: {error_message}", harvest_object, "Import"
                    )
                    return False

            Session.commit()

            return True

        except p.toolkit.ValidationError as e:
            log.exception(e)
            self._save_object_error(
                "Invalid package with GUID: %s: %r"
                % (harvest_object.guid, e.error_dict),
                harvest_object,
                "Import",
            )
        except Exception as e:
            log.exception(e)
            self._save_object_error("%r" % e, harvest_object, "Import")

        return None

    def _create_or_update_pkg(self, package_dict, harvest_object):
        print(True)


class ContentFetchError(Exception):
    pass


class ContentNotFoundError(ContentFetchError):
    pass


class RemoteResourceError(Exception):
    pass


class SearchError(Exception):
    pass


class ReadError(Exception):
    pass


class RemoteSchemaError(Exception):
    pass
