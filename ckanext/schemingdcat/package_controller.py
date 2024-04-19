from ckan.common import request
import json
import ckan.plugins as plugins
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

    def before_search(self, search_params):
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
                    else:
                        log.debug("new_fq generate a invalid value: %s", new_fq)
            elif isinstance(facet_field, str):
                new_fq = self._facet_search_operator(search_params.get('fq', ''), facet_field)
                if new_fq and isinstance(new_fq, str):
                    search_params.update({'fq': new_fq})
                else:
                    log.debug("new_fq generate a invalid value: %s", new_fq)
        except Exception as e:
            log.error("[before_search] error: %s", e)
        return search_params

    def after_search(self, search_results, search_params):
        return search_results

    def before_index(self, data_dict):
        """Processes the data dictionary before indexing.

        Iterates through each facet defined in the system's facets dictionary. For each facet present in the data dictionary, it attempts to parse its value as JSON. If the value is a valid JSON string, it replaces the original string value with the parsed JSON object. If the value cannot be parsed as JSON (e.g., because it's not a valid JSON string), it leaves the value unchanged. Facets present in the data dictionary but not containing any data are removed.

        Args:
            data_dict (dict): The data dictionary to be processed. It's expected to contain keys corresponding to facet names with their associated data as values.

        Returns:
            dict: The processed data dictionary with JSON strings parsed into objects where applicable and empty facets removed.
        """
        for facet, label in utils.get_facets_dict().items():
            data = data_dict.get(facet)
            log.debug("Data ({1}) in facet: {0}".format(data, facet))
            if data:
                if isinstance(data, str):
                    try:
                        data_dict[facet] = json.loads(data)
                    except json.decoder.JSONDecodeError:
                        data_dict[facet] = data
            else:
                if facet in data_dict:
                    del data_dict[facet]

        return data_dict

    def before_view(self, pkg_dict):
        return pkg_dict

    def after_create(self, context, data_dict):
        return data_dict

    def after_update(self, context, data_dict):
        return data_dict

    def after_delete(self, context, data_dict):
        return data_dict

    def after_show(self, context, data_dict):
        return data_dict

    def update_facet_titles(self, facet_titles):
        return facet_titles

    def package_controller_config(self, default_facet_operator):
        self.default_facet_operator = default_facet_operator

    def _facet_search_operator(self, fq, facet_field):
        """Return a version of fq where all filters are joined by the OR operator.

        If information for the facets operator is included in the request and defined as OR,
        a version of fq is returned where all filters are joined by the OR operator.

        Args:
            fq (str): The filter query to modify.
            facet_field (list): A list of facet fields.

        Returns:
            str: A modified version of fq where all filters are joined by the OR operator.
        """
        new_fq = fq
        facets_group = ""
        no_facets_group = ""
        try:
            facet_operator = self.default_facet_operator
            try:
                if request is not None and \
                        request.params and \
                        request.params.items():

                    #log.debug('request.params %r' % request.params)
                    if (FACET_OPERATOR_PARAM_NAME, 'AND') in request.params.items():
                        facet_operator = 'AND'
                    elif (FACET_OPERATOR_PARAM_NAME, 'OR') in request.params.items():
                        facet_operator = 'OR'

            except Exception as e:
                log.error("[_facet_search_operator] error:%r: " % e)
                facet_operator = self.default_facet_operator

            #log.debug(u'facet_operator {0}'.format(facet_operator))

            if (facet_operator == 'OR'):
                fq_split = fq.split('" ')
                faceted = False
                first_facet = True
                first_no_facet = True
                if facet_field is not None and len(facet_field) > 0:
                    #log.debug(u'facet_field {0}'.format(facet_field))
                    for fq_s in fq_split:
                        faceted = False
                        for facet in facet_field:
                            if fq_s.startswith('%s:' % facet):
                                faceted = True
                                if first_facet:
                                    facets_group = '%s' % fq_s
                                    first_facet = False
                                else:
                                    facets_group = ('%s" OR %s' %
                                                    (facets_group, fq_s))
                        if not faceted:
                            if first_no_facet:
                                no_facets_group = '%s' % fq_s
                                first_no_facet = False
                            else:
                                no_facets_group = ('%s" AND %s' %
                                                (no_facets_group, fq_s))
                    if faceted:
                        if not first_no_facet:
                            no_facets_group = '%s"' % no_facets_group
                    elif not first_facet:
                        facets_group = '(%s") AND ' % facets_group

                    new_fq = '%s %s' % (facets_group, no_facets_group)

                    #log.debug(u'temp2 new_fq {0}'.format(new_fq))
                    #log.info('#### fq = %s' % fq)
                    #log.info('#### new_fq = %s' % new_fq)

        except UnicodeEncodeError as e:
            log.warn('UnicodeDecodeError %s  %s' % (e.errno, e.strerror))
        except Exception:
            log.warn("Unexpected error:%r: " % sys.exc_info()[0])
            new_fq = fq
        #log.debug(u'new fq {0}'.format(new_fq))
        return new_fq