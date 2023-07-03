from ckan.common import request
import json
import ckan.plugins as plugins
import ckanext.facet_scheming.config as config
import ckanext.facet_scheming.utils as utils

import logging
import sys

FACET_OPERATOR_PARAM_NAME = '_facet_operator'
FACET_SORT_PARAM_NAME = '_%s_sort'

log = logging.getLogger(__name__)


class PackageController():

    plugins.implements(plugins.IPackageController)

    default_facet_operator = config.default_facet_operator

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
        facet_field = search_params.get('facet.field', '')
        if facet_field is not None and len(facet_field) > 0:
            new_fq = self._facet_search_operator(
                (search_params.get('fq', '')), facet_field)
            search_params.update({'fq': new_fq})

        return search_params

    def after_search(self, search_results, search_params):
        return search_results

    def before_index(self, data_dict):
        for facet, label in utils.get_facets_dict().items():
            data = data_dict.get(facet)
            logging.debug("Datos ({1}) en data: {0}".format(data, facet))
            if data:
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
        """
        Si en el request se ha incluido información para el operador de
        facets y está definido como OR, se devuelve una versión de fq
        donde se incluyen todos los filtros unidos por el operador OR
        """

        new_fq = fq
        facets_group = ""
        no_facets_group = ""
        try:
            facet_operator = self.default_facet_operator
            try:
                #    busco si hay definido un operador de facetas en el request,
                #    y lo guardo en facet_operator
                if request is not None and \
                        request.params and \
                        request.params.items():

                    log.debug('request.params %r' % request.params)
                    if (FACET_OPERATOR_PARAM_NAME, 'AND') in request.params.items():
                        facet_operator = 'AND'
                    elif (FACET_OPERATOR_PARAM_NAME, 'OR') in request.params.items():
                        facet_operator = 'OR'

            except Exception as e:
                log.warn("[_facet_search_operator]exception:%r: " % e)
                facet_operator = self.default_facet_operator

            log.debug(u'facet_operator {0}'.format(facet_operator))

# Por defecto la búsqueda por facetas es por intersección, pero si he pedido el
# operador OR, la hago aditiva

            if (facet_operator == 'OR'):
                fq_split = fq.split('" ')
                faceted = False
                first_facet = True
                first_no_facet = True
                if facet_field is not None and len(facet_field) > 0:
                    log.debug(u'facet_field {0}'.format(facet_field))
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
# y aquí viene el salto final
                    if faceted:
                        if not first_no_facet:
                            no_facets_group = '%s"' % no_facets_group
                    elif not first_facet:
                        facets_group = '(%s") AND ' % facets_group

                    new_fq = '%s %s' % (facets_group, no_facets_group)

                    log.debug(u'temp2 new_fq {0}'.format(new_fq))
#                    log.info('#### fq = %s' % fq)
#                    log.info('#### new_fq = %s' % new_fq)
        except UnicodeEncodeError as e:
            log.warn('UnicodeDecodeError %s  %s' % (e.errno, e.strerror))
        except Exception:
            log.warn("Unexpected error:%r: " % sys.exc_info()[0])
            new_fq = fq
        log.debug(u'new fq {0}'.format(new_fq))
        return new_fq
