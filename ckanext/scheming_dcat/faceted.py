import ckan.plugins as plugins
from ckan.common import request
import ckanext.scheming_dcat.config as sdct_config
from ckanext.scheming_dcat.utils import get_facets_dict
import logging

log = logging.getLogger(__name__)


class Faceted():

    plugins.implements(plugins.IFacets)
    facet_list = []

    def facet_load_config(self, facet_list):
        self.facet_list = facet_list
        #log.debug("Configured facet_list= {0}".format(self.facet_list))

    # Remove group facet
    def _facets(self, facets_dict):

        # if 'groups' in facets_dict:
        #   del facets_dict['groups']
        return facets_dict

    def dataset_facets(self,
                       facets_dict,
                       package_type):
        # This patch is necessary to avoid collisions with the harvest package type from the harvest plugin
        if package_type == "dataset":
            return self._custom_facets(facets_dict, package_type)
        else:
            return facets_dict

    def _custom_facets(self,
                       facets_dict,
                       package_type):

        lang_code = request.environ['CKAN_LANG']

        _facets_dict = {}
        for facet in self.facet_list:
            # Look for the field label in the scheming file.
            # If it's not there, use the default dictionary provided
            scheming_item = get_facets_dict().get(facet)

            if scheming_item:
                # Retrieve the corresponding label for the used language
                _facets_dict[facet] = scheming_item.get(lang_code)
                if not _facets_dict[facet]:
                    # If the label doesn't exist, try the default language label.
                    # And if that doesn't exist either, use the first one available.
                    raw_label = scheming_item.get(sdct_config.default_locale,
                                                  list(scheming_item.values())[0])
                    if raw_label:
                        _facets_dict[facet] = plugins.toolkit._(raw_label)
                    else:
                        log.warning(
                            "Unable to find a valid label for the field '%s' when faceting" % facet)

                if not _facets_dict[facet]:
                    _facets_dict[facet] = plugins.toolkit._(facet)

            else:
                _facets_dict[facet] = plugins.toolkit._(facets_dict.get(facet))

        # tag_key = 'tags_' + lang_code
        # facets_dict[tag_key] = plugins.toolkit._('Tag')
        #FIXME: FOR COMMON TAG FACET
        #log.debug("dataset_facets._facets_dict: {0}".format(_facets_dict))
        return _facets_dict

    def group_facets(self,
                     facets_dict,
                     group_type,
                     package_type):

        if sdct_config.group_custom_facets:
            #log.debug("Custom facets for group")
            facets_dict = self._custom_facets(facets_dict, package_type)
        return facets_dict

    def organization_facets(self,
                            facets_dict,
                            organization_type,
                            package_type):

        if sdct_config.group_custom_facets:
            #log.debug("facetas personalizadas para organización")
            facets_dict = self._custom_facets(facets_dict, package_type)
        else:
            log.debug("Default facets for Organization")

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
