from ckan.common import json, c, request, is_flask_request
from ckan.lib import helpers as ckan_helpers
import ckan.plugins as p
import six
import re
import yaml
from yaml.loader import SafeLoader
from pathlib import Path

from six.moves.urllib.parse import urlencode

from ckanext.scheming.helpers import scheming_choices_label

import ckanext.scheming_dcat.config as sd_config
from ckanext.scheming_dcat.utils import (get_facets_dict, public_file_exists,
                                          public_dir_exists)
from ckanext.scheming_dcat import config as sd_config
from ckanext.dcat.utils import CONTENT_TYPES, get_endpoint

import logging

log = logging.getLogger(__name__)

all_helpers = {}


def helper(fn):
    """Collect helper functions into the ckanext.scheming_dcat.all_helpers dictionary.

    Args:
        fn (function): The helper function to add to the dictionary.

    Returns:
        function: The helper function.
    """
    all_helpers[fn.__name__] = fn
    return fn

@helper
def schemingdct_default_facet_search_operator():
    """Return the default facet search operator: AND/OR.

    Returns:
        str: The default facet search operator.
    """
    facet_operator = sd_config.default_facet_operator
    if facet_operator and (facet_operator.upper() == 'AND'
                           or facet_operator.upper() == 'OR'):
        facet_operator = facet_operator.upper()
    else:
        facet_operator = 'AND'
    return facet_operator

@helper
def schemingdct_decode_json(json_text):
    """Convert a JSON string to a Python object.

    Args:
        json_text (str): The JSON string to convert.

    Returns:
        object: A Python object representing the JSON data.
    """
    return json.loads(json_text)

@helper
def schemingdct_organization_name(org_id):
    """Return the name of the organization from its ID.

    Args:
        org_id (dict): A dictionary containing the ID of the organization.

    Returns:
        str: The name of the organization, or None if the organization cannot be found.
    """
    org_name = None
    try:
        org_dic = ckan_helpers.get_organization(org_id['display_name'])
        if org_dic is not None:
            org_name = org_dic['name']
        else:
            log.warning(
                'Could not find the name of the organization with ID {0}'.format(org_id['display_name']))
    except Exception as e:
        log.error(
            "Exception while trying to find the name of the organization: {0}".format(e))
    return org_name

@helper
def schemingdct_get_facet_label(facet):
    """Return the label for a given facet.

    Args:
        facet (str): The name of the facet.

    Returns:
        str: The label for the given facet.
    """
    return get_facets_dict[facet]

@helper
def schemingdct_get_facet_items_dict(
        facet, search_facets=None, limit=None,
        exclude_active=False, scheming_choices=None):
    '''Return the list of unselected facet items for the given facet, sorted
    by count.

    Returns the list of unselected facet contraints or facet items (e.g. tag
    names like "russian" or "tolstoy") for the given search facet (e.g.
    "tags"), sorted by facet item count (i.e. the number of search results that
    match each facet item).

    Reads the complete list of facet items for the given facet from
    c.search_facets, and filters out the facet items that the user has already
    selected.

    List of facet items are ordered acording the faccet_sort parameter

    Arguments:
    facet -- the name of the facet to filter.
    search_facets -- dict with search facets(c.search_facets in Pylons)
    limit -- the max. number of facet items to return.
    exclude_active -- only return unselected facets.
    scheming_choices -- scheming choices to use to get label from value.

    '''

    #log.debug("Returning facets for: {0}".format(facet))

    order = "default"
    items = []

    search_facets = (search_facets or getattr(c, u'search_facets', None))

    if search_facets \
       and isinstance(search_facets, dict) \
       and search_facets.get(facet, {}).get('items'):

        for facet_item in search_facets.get(facet)['items']:
            if scheming_choices:
                facet_item['label'] = scheming_choices_label(
                    scheming_choices, facet_item['name'])
            else:
                facet_item['label'] = facet_item['display_name']

            if not len(facet_item['name'].strip()):
                continue

            params_items = request.params.items(multi=True) \
                if is_flask_request() else request.params.items()

            if not (facet, facet_item['name']) in params_items:
                items.append(dict(active=False, **facet_item))
            elif not exclude_active:
                items.append(dict(active=True, **facet_item))

            #    log.debug("params: {0}:{1}".format(
            #    facet,request.params.getlist("_%s_sort" % facet)))
            order_lst = request.params.getlist("_%s_sort" % facet)
            if len(order_lst):
                order = order_lst[0]
        #     Sort descendingly by count and ascendingly by case-sensitive display name
        #    items.sort(key=lambda it: (-it['count'], it['display_name'].lower()))
        sorts = {
            "name": ("label", False),
            "name_r": ("label", True),
            "count": ("count", False),
            "count_r": ("count", True)
            }
        if sorts.get(order):
            items.sort(key=lambda it: (it[sorts.get(order)[0]]), reverse=sorts.get(order)[1])
        else:
            items.sort(key=lambda it: (-it['count'], it['label'].lower()))

        if hasattr(c, 'search_facets_limits'):
            if c.search_facets_limits and limit is None:
                limit = c.search_facets_limits.get(facet)
        # zero treated as infinite for hysterical raisins
        if limit is not None and limit > 0:
            return items[:limit]

    return items

@helper
def schemingdct_new_order_url(facet_name, order_concept, extras=None):
    """Return a URL with the order parameter for the given facet and concept to use.

    Based on the actual order, it rotates cyclically from no order -> direct order -> inverse order over the given concept.

    Args:
        facet_name (str): The name of the facet to order.
        order_concept (str): The concept (name or count) that will be used to order.
        extras (dict, optional): Extra parameters to include in the URL.

    Returns:
        str: The URL with the order parameter for the given facet and concept.
    """
    old_order = None
    order_param = "_%s_sort" % facet_name
    order_lst = request.params.getlist(order_param)
    if not extras:
        extras = {}

    controller = getattr(c, 'controller', False) or request.blueprint
    action = getattr(c, 'action', False) or p.toolkit.get_endpoint()[1]
    url = ckan_helpers.url_for(controller=controller, action=action, **extras)

    if len(order_lst):
        old_order = order_lst[0]

    order_mapping = {
        "name": {
            "name": "name_r",
            "name_r": None,
            None: "name"
            },
        "count": {
            "count": "count_r",
            "count_r": None,
            None: "count"
            }
        }

    new_order = order_mapping.get(order_concept, {}).get(old_order)

    params_items = request.params.items(multi=True) \
        if is_flask_request() else request.params.items()
    params_nopage = [
        (k, v) for k, v in params_items
        if k != order_param
    ]

    if new_order:
        params_nopage.append((order_param, new_order))

    if params_nopage:
        url = url + u'?' + urlencode(params_nopage)

    return url

@helper
def schemingdct_get_icons_dir(field):
    """Return the defined icons directory for a scheming field definition.

    Args:
        field (dict): The scheming field definition.

    Returns:
        str: The defined icons directory, or None if not found.
    """
    if field:
        if 'icons_dir' in field:
            return field['icons_dir']

        if 'field_name' in field:
            dir = sd_config.icons_dir + '/' + field['field_name']
            if public_dir_exists(dir):
                return dir
        log.debug("No directory found for {0}".format(field['field_name']))
    
    return None

@helper
def schemingdct_get_default_icon(field):
    """Return the defined default icon for a scheming field definition.

    Args:
        field (dict): The scheming field definition.

    Returns:
        str: The defined default icon, or None if not found.
    """
    if 'default_icon' in field:
        return field['default_icon']

@helper
def schemingdct_get_icon(choice, icons_dir=None, default='/images/default/no_icon.svg'):
    """Return the relative URL to the icon for the item.

    Args:
        choice (dict): The choice selected for the field.
        icons_dir (str, optional): The path to search for the icon. Usually the common path for icons for this field.
        default (str, optional): The default value to return if no icon is found.

    Returns:
        str: The relative URL to the icon, or the default value if not found.
    """
    extensions = ['.svg', '.png', '.jpg', '.gif']
    icon_name = None 
    #log.debug("Field value: {0}".format(choice))

    if choice:
        if 'icon' in choice:
            return (icons_dir+"/" if icons_dir else "") + choice['icon']

        if ckan_helpers.is_url(choice['value']):
            url_parts = choice['value'].split('/')

            if len(url_parts) == 1:
                icon_name = url_parts[-1].lower()
            else:
                icon_name = url_parts[-2].lower()+'/'+url_parts[-1].lower()
        else:
            icon_name = choice['value']

        url_path = (icons_dir+"/" if icons_dir else "") + icon_name
        #log.debug("Searching for: {0}".format(url_path))

        for extension in extensions:
            if public_file_exists(url_path+extension):
                return url_path+extension
    return default

@helper
def schemingdct_get_choice_item(field, value):
    """Return the whole choice item for the given value in the scheming field.

    Args:
        field (dict): The scheming field to look for the choice item in.
        value (str): The option item value.

    Returns:
        dict: The whole option item in scheming, or None if not found.
    """
    if field and ('choices' in field):
        #log.debug("Searching: {0} en {1}".format(value,field['choices']))
        for choice in field['choices']:
            if choice['value'] == value:
                return choice

    return None

@helper
def scheming_display_json_list(value):
    """Return the object passed serialized as a JSON list.

    Args:
        value (any): The object to serialize.

    Returns:
        str: The serialized object as a JSON list, or the original value if it cannot be serialized.
    """
    if isinstance(value, six.string_types):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return value

@helper
def scheming_clean_json_value(value):
    """Clean a JSON list value to avoid errors with: '"' and spaces.

    Args:
        value (str): The object to serialize.

    Returns:
        str: The cleaned value, or the original value if it cannot be cleaned.
    """
    try:
        value = value.strip(' ').replace('\\"', '%%%@#')
        value = value.replace('"', '')
        value = value.replace('%%%@#', '"')
        return value
    except (TypeError, ValueError):
        return value

@helper
def schemingdct_prettify_url(url):
    """Clean a URL to remove 'http://', 'https://', and 'www.'.

    Args:
        url (str): The URL to clean.

    Returns:
        str: The cleaned URL.
    """
    try:
        cleaned_url = re.sub(r'^https?://(?:www\.)?', '', url).rstrip('/')
        return cleaned_url
    except AttributeError:
        return url

@helper
def schemingdct_prettify_url_name(url):
    """Extracts the name of the last segment of a URL.

    Args:
        url (str): The URL to extract the name from.

    Returns:
        str: The name of the last segment of the URL.
    """
    if '/' in url:
        url_name = url.split("/")[-1]
    else:
        url_name = url
    return url_name

@helper
def schemingdct_listify_str(values):
    """Converts a string or list/tuple of strings to a list of strings.

    If `values` is already a list or tuple, it is returned as is. If `values` is a string,
    it is split into a list of strings using commas as the delimiter. Each string in the
    resulting list is stripped of leading/trailing whitespace and quotes.

    Args:
        values (str or list or tuple): The value(s) to convert to a list of strings.

    Returns:
        list: A list of strings.
    """
    if isinstance(values, str):
        values = values.strip('][').split(',')
        values = [item.strip().strip('"') for item in values]
    elif not isinstance(values, (list, tuple)):
        log.debug("Not a list or string: {0}".format(values))
        values = ['']
    
    return values
@helper
def schemingdct_load_yaml(file):
    """Load a YAML file from the 'config' directory.

    Args:
        file (str): The name of the YAML file to load.

    Returns:
        dict: A dictionary containing the data from the YAML file.
    """
    source_path = Path(__file__).resolve(True)
    yaml_data = {}
    try:
        p = source_path.parent.joinpath('config',file)
        with open(p,'r') as f:
            yaml_data=yaml.load(f, Loader=SafeLoader )
    except FileNotFoundError:
        log.error("The file {0} does not exist".format(file))
    except Exception as e:
        log.error("Could not read configuration from {0}: {1}".format(file, e))

    return yaml_data

@helper
def schemingdct_get_linked_data(id):
    """Get linked data for a given identifier.

    Args:
        id (str): The identifier to get linked data for.

    Returns:
        list: A list of dictionaries containing linked data for the identifier.
    """
    linkeddata_links = schemingdct_load_yaml('linkeddata_links.yaml') if sd_config.debug else sd_config.linkeddata_links

    return [{
        'name': name,
        'display_name': linkeddata_links.get(name, {'display_name': content_type})['display_name'],
        'format': linkeddata_links.get(name, {}).get('format'),
        'image_display_url': linkeddata_links.get(name, {}).get('image_display_url'),
        'description': linkeddata_links.get(name, {}).get('description') or f"Formats {content_type}",
        'description_url': linkeddata_links.get(name, {}).get('description_url'),
        'endpoint': 'dcat.read_dataset',
        'endpoint_data': {
            '_id': id,
            '_format': name,
        }
    } for name, content_type in CONTENT_TYPES.items()]

@helper
def schemingdct_get_catalog_endpoints():
    """Get the catalog endpoints.

    Returns:
        list: A list of dictionaries containing linked data for the identifier.
    """
    endpoints = schemingdct_load_yaml('endpoints.yaml') if sd_config.debug else sd_config.endpoints
    
    csw_uri = schemingdct_get_geospatial_endpoint('catalog')
    
    return [{
        'name': item['name'],
        'display_name': item['display_name'],
        'format': item['format'],
        'image_display_url': item['image_display_url'],
        'description': item['description'],
        'type': item['type'],
        'profile': item['profile'],
        'profile_label': item['profile_label'],
        'endpoint': get_endpoint('catalog') if item.get('type').lower() == 'lod' else csw_uri.format(version=item['version']) if item.get('type').lower() == 'ogc' else None,
        'endpoint_data': {
            '_format': item['format'],
            '_external': True,
            'profiles': item['profile'],
        }
    } for item in endpoints['catalog_endpoints']]

@helper
def schemingdct_get_geospatial_endpoint(type='dataset'):
    """Get geospatial base URI for CSW Endpoint.

    Args:
        type (str): The type of endpoint to return. Can be 'catalog' or 'dataset'.

    Returns:
        str: The base URI of the CSW Endpoint with the appropriate format.
    """    
    try:
        
        if sd_config.geometadata_base_uri:
            csw_uri = sd_config.geometadata_base_uri
        
        if sd_config.geometadata_base_uri and '/csw' not in sd_config.geometadata_base_uri:
            csw_uri = sd_config.geometadata_base_uri.rstrip('/') + '/csw'
        elif sd_config.geometadata_base_uri == '':
            csw_uri = '/csw'
        else:
            csw_uri = sd_config.geometadata_base_uri.rstrip('/')
    except:
        csw_uri = '/csw'

    if type == 'catalog':
        return csw_uri + '?service=CSW&version={version}&request=GetCapabilities'
    else:
        return csw_uri + '?service=CSW&version={version}&request=GetRecordById&id={id}&elementSetName={element_set_name}&outputSchema={output_schema}&OutputFormat={output_format}'

@helper
def schemingdct_get_geospatial_metadata():
    """Get geospatial metadata for CSW formats.

    Returns:
        list: A list of dictionaries containing geospatial metadata for CSW formats.
    """
    geometadata_links = schemingdct_load_yaml('geometadata_links.yaml') if sd_config.debug else sd_config.geometadata_links
    
    csw_uri = schemingdct_get_geospatial_endpoint('dataset')

    return [{
        'name': item['name'],
        'display_name': item['display_name'],
        'format': item['format'],
        'image_display_url': item['image_display_url'],
        'description': item['description'],
        'description_url': item['description_url'],
        'url': csw_uri.format(output_format=item['output_format'], version=item['version'], element_set_name=item['element_set_name'], output_schema=item['output_schema'], id='{id}')
    } for item in geometadata_links['csw_formats']]

@helper
def schemingdct_get_all_metadata(id):
    """Get linked data and geospatial metadata for a given identifier.

    Args:
        id (str): The identifier to get linked data and geospatial metadata for.

    Returns:
        list: A list of dictionaries containing linked data and geospatial metadata for the identifier.
    """
    geospatial_metadata = schemingdct_get_geospatial_metadata()
    linked_data = schemingdct_get_linked_data(id)

    for metadata in geospatial_metadata:
        metadata['endpoint_type'] = 'csw'

    for data in linked_data:
        data['endpoint_type'] = 'dcat'

    return geospatial_metadata + linked_data