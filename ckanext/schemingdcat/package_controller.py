from ckan.common import request
import json
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckanext.schemingdcat.config as sdct_config
import ckanext.schemingdcat.utils as utils

import logging
import sys

FACET_OPERATOR_PARAM_NAME = '_facet_operator'
FACET_SORT_PARAM_NAME = '_%s_sort'

log = logging.getLogger(__name__)


class PackageController():

    plugins.implements(plugins.IPackageController)

    default_facet_operator = sdct_config.default_facet_operator

    def read(self, entity):
        pass

    def create(self, entity):
        pass

    def edit(self, entity):
        pass

    def authz_add_role(self, object_role):
        pass

    def authz_remove_role(self, object_role):
        pass

    def delete(self, entity):
        pass

    def before_dataset_search(self, search_params):
        """Modifies search parameters before executing a search.

        This method adjusts the 'fq' (filter query) parameter based on the 'facet.field' value in the search parameters. If 'facet.field' is a list, it iterates through each field, applying the '_facet_search_operator' to modify 'fq'. If 'facet.field' is a string, it directly applies the '_facet_search_operator'. If 'facet.field' is not present or is invalid, no modification is made.

        Args:
            search_params (dict): The search parameters to be modified. Expected to contain 'facet.field' and 'fq'.

        Returns:
            dict: The modified search parameters.

        Raises:
            Exception: Captures and logs any exception that occurs during the modification of search parameters.
        """
        try:
            facet_field = search_params.get('facet.field', '')
            if not facet_field:
                return search_params
            elif isinstance(facet_field, list):
                for field in facet_field:
                    new_fq = self._facet_search_operator(search_params.get('fq', ''), field)
                    if new_fq and isinstance(new_fq, str):
                        search_params.update({'fq': new_fq})
            elif isinstance(facet_field, str):
                new_fq = self._facet_search_operator(search_params.get('fq', ''), facet_field)
                if new_fq and isinstance(new_fq, str):
                    search_params.update({'fq': new_fq})
        except Exception as e:
            log.error("[before_search] Error: %s", e)
        return search_params

    def after_dataset_search(self, search_results, search_params):
        return search_results

    def before_dataset_index(self, data_dict):
        """Processes the data dictionary before indexing.

        Iterates through each facet defined in the system's facets dictionary. For each facet present in the data dictionary, it attempts to parse its value as JSON. If the value is a valid JSON string, it replaces the original string value with the parsed JSON object. If the value cannot be parsed as JSON (e.g., because it's not a valid JSON string), it leaves the value unchanged. Facets present in the data dictionary but not containing any data are removed.

        Also handles repeating_subfields by converting them to JSON strings for Solr indexing.

        Args:
            data_dict (dict): The data dictionary to be processed. It's expected to contain keys corresponding to facet names with their associated data as values.

        Returns:
            dict: The processed data dictionary with JSON strings parsed into objects where applicable and empty facets removed.
        """
        # Process facets
        for facet, label in utils.get_facets_dict().items():
            data = data_dict.get(facet)
            #log.debug("[before_index] Data ({1}) in facet: {0}".format(data, facet))
            if data:
                if isinstance(data, str):
                    try:
                        data_dict[facet] = json.loads(data)
                    except json.decoder.JSONDecodeError:
                        data_dict[facet] = data
            else:
                if facet in data_dict:
                    del data_dict[facet]

        # Handle repeating_subfields: convert complex objects to JSON strings for Solr
        # List of fields with repeating_subfields that need special handling
        repeating_fields = ['authors']

        for field_name in repeating_fields:
            if field_name in data_dict:
                field_data = data_dict[field_name]
                # If the field contains a list of dicts (repeating_subfields), convert to JSON string
                if isinstance(field_data, list) and field_data and isinstance(field_data[0], dict):
                    try:
                        data_dict[field_name] = json.dumps(field_data)
                        log.debug(f"[before_index] Converted {field_name} to JSON string for Solr indexing")
                    except (TypeError, ValueError) as e:
                        log.warning(f"[before_index] Could not serialize {field_name} to JSON: {e}")
                        # If serialization fails, remove the field from indexing to avoid Solr errors
                        del data_dict[field_name]

        return data_dict

    def before_dataset_view(self, pkg_dict):
        # Asegurarnos de que el modo del formulario esté disponible
        if 'form_mode' not in pkg_dict:
            pkg_dict['form_mode'] = 'basic'
        return pkg_dict

    def after_dataset_create(self, context, data_dict):
        """
        Hook que se ejecuta después de crear un dataset.
        """
        # Limpiar el modo del formulario si es necesario
        if 'form_mode' in data_dict:
            del data_dict['form_mode']
        
        return data_dict

    def after_dataset_update(self, context, data_dict):
        """
        Hook que se ejecuta después de actualizar un dataset.
        """
        return data_dict

    def after_dataset_delete(self, context, data_dict):
        return data_dict

    def after_dataset_show(self, context, data_dict):
        return data_dict

    def update_facet_titles(self, facet_titles):
        return facet_titles

    def package_controller_config(self, default_facet_operator):
        self.default_facet_operator = default_facet_operator

    def _facet_search_operator(self, fq, facet_field):
        """Modifies the query filter (fq) to use the OR operator among the specified facet filters.

        Args:
            fq (str): The current query filter.
            facet_field (list): List of facet fields to consider for the OR operation.

        Returns:
            str: The modified query filter.
        """
        new_fq = fq
        try:
            facet_operator = self.default_facet_operator
            # Determine the facet operator based on request parameters
            if request.params.get(FACET_OPERATOR_PARAM_NAME) == 'OR':
                facet_operator = 'OR'
            elif request.params.get(FACET_OPERATOR_PARAM_NAME) == 'AND':
                facet_operator = 'AND'

            if facet_operator == 'OR' and facet_field:
                # Split the original fq into conditions, assuming they are separated by " AND "
                conditions = fq.split(' AND ')
                # Filter and group conditions that correspond to facet fields
                facet_conditions = [cond for cond in conditions if any(fld in cond for fld in facet_field)]
                non_facet_conditions = [cond for cond in conditions if not any(fld in cond for fld in facet_field)]
                # Reconstruct fq using " OR " to join facet conditions and " AND " for the rest
                if facet_conditions:
                    new_fq = ' OR '.join(facet_conditions)
                    if non_facet_conditions:
                        new_fq = f"({new_fq}) AND {' AND '.join(non_facet_conditions)}"
                else:
                    new_fq = ' AND '.join(non_facet_conditions)

        except Exception as e:
            log.error("[_facet_search_operator] Error modifying the query filter: %s", e)
            # In case of error, return the original fq
            new_fq = fq

        return new_fq


if not toolkit.check_ckan_version(min_version='2.10.0'):
    # Assign legacy hook names when running on CKAN < 2.10
    PackageController.before_search = PackageController.before_dataset_search
    PackageController.after_search = PackageController.after_dataset_search
    PackageController.before_index = PackageController.before_dataset_index
    PackageController.before_view = PackageController.before_dataset_view
    PackageController.after_create = PackageController.after_dataset_create
    PackageController.after_update = PackageController.after_dataset_update
    PackageController.after_delete = PackageController.after_dataset_delete
    PackageController.after_show = PackageController.after_dataset_show
