import ckan.plugins as plugins
from ckan.common import request
import ckanext.facet_scheming.config as facet_scheming_config
from ckanext.facet_scheming.utils import get_facets_dict
import logging

logger = logging.getLogger(__name__)

class Faceted():

    plugins.implements(plugins.IFacets)
    facet_list = []
    
    def facet_load_config(self, facet_list):
        self.facet_list = facet_list
        logger.debug("Configured facet_list= {0}".format(self.facet_list))

#    Remove group facet
    def _facets(self, facets_dict):
        
#        if 'groups' in facets_dict:
#            del facets_dict['groups']
        return facets_dict

    def dataset_facets(self,
                       facets_dict,
                       package_type):
        
        return self._custom_facets(facets_dict, package_type)

    def _custom_facets(self,
                       facets_dict,
                       package_type):

        lang_code = request.environ['CKAN_LANG']

        _facets_dict = {}
        for facet in self.facet_list:
            try:
                scheming_item = get_facets_dict()[facet]
            except KeyError:
                try:
                    _facets_dict[facet] = facets_dict[facet]
                except KeyError:
                    logger.warning(
                        "No existe el valor '{0}' para facetar".format(facet))
            else:
                try:
                    _facets_dict[facet] = scheming_item[lang_code]
                except KeyError:
                    try:
                        _facets_dict[facet] = plugins.toolkit._(
                            scheming_item[facet_scheming_config.default_locale])
                    except KeyError:
                        try:
                            _facets_dict[facet] = plugins.toolkit._(
                                list(scheming_item.values())[0])
                        except IndexError:
                            logger.warning(
                                "Ha sido imposible encontrar una etiqueta "
                                "válida para el campo '{0}' al facetar".format(
                                    facet))

#        tag_key = 'tags_' + lang_code
#        facets_dict[tag_key] = plugins.toolkit._('Tag')
#         FIXME: PARA FACETA COMUN DE TAGS
        logger.debug("dataset_facets._facets_dict: {0}".format(_facets_dict))
        return _facets_dict

    def group_facets(self,
                     facets_dict,
                     group_type,
                     package_type):

        if facet_scheming_config.group_custom_facets:
            logger.debug("facetas personalizadas para grupo")
            facets_dict = self._custom_facets(facets_dict, package_type)
        return facets_dict

    def organization_facets(self,
                            facets_dict,
                            organization_type,
                            package_type):

        if facet_scheming_config.group_custom_facets:
            logger.debug("facetas personalizadas para organización")
            facets_dict = self._custom_facets(facets_dict, package_type)
        else:
            logger.debug("facetas por defecto para organización")

#        lang_code = pylons.request.environ['CKAN_LANG']
#        facets_dict.clear()
#        facets_dict['organization'] = plugins.toolkit._('Organization')
#        facets_dict['theme_id'] =  plugins.toolkit._('Category')
#        facets_dict['res_format_label'] = plugins.toolkit._('Format')
#        facets_dict['publisher_display_name'] = plugins.toolkit._('Publisher')
#        facets_dict['administration_level'] = plugins.toolkit._(
#                                                'Administration level')
#        facets_dict['frequency'] = plugins.toolkit._('Update frequency')
#        tag_key = 'tags_' + lang_code
#        facets_dict[tag_key] = plugins.toolkit._('Tag')
#         FIXME: PARA FACETA COMUN DE TAGS
#         facets_dict['tags'] = plugins.toolkit._('Tag')
#        return self._facets(facets_dict)
        return facets_dict
