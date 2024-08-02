from ckan.common import json, c, request, is_flask_request
from ckan.lib import helpers as ckan_helpers
import ckan.logic as logic
from ckan import model
from ckan.lib.i18n import get_available_locales, get_lang
import ckan.plugins as p
import six
import re
import yaml
from yaml.loader import SafeLoader
from pathlib import Path
from functools import lru_cache
import datetime
import typing
from urllib.parse import urlparse
from urllib.error import URLError

from six.moves.urllib.parse import urlencode

from ckanext.scheming.helpers import (
    scheming_choices_label,
    scheming_language_text,
    scheming_dataset_schemas,
    scheming_get_schema
)

from ckanext.harvest.helpers import (
    get_harvest_source
)
from ckanext.harvest.utils import (
    DATASET_TYPE_NAME
)

import ckanext.schemingdcat.config as sdct_config
from ckanext.schemingdcat.utils import (
    get_facets_dict,
    public_file_exists,
    public_dir_exists,
)
from ckanext.dcat.utils import CONTENT_TYPES, get_endpoint
from ckanext.fluent.validators import LANG_SUFFIX
import logging

log = logging.getLogger(__name__)

all_helpers = {}
prettify_cache = {}
DEFAULT_LANG = None

@lru_cache(maxsize=None)
def get_scheming_dataset_schemas():
    """
    Retrieves the dataset schemas using the scheming_dataset_schemas function.
    Caches the result using the LRU cache decorator for efficient retrieval.
    """
    return scheming_dataset_schemas()


def helper(fn):
    """Collect helper functions into the ckanext.schemingdcat.all_helpers dictionary.

    Args:
        fn (function): The helper function to add to the dictionary.

    Returns:
        function: The helper function.
    """
    all_helpers[fn.__name__] = fn
    return fn


@helper
def schemingdcat_get_schema_names():
    """
    Get the names of all the schemas defined for the Scheming DCAT extension.

    Returns:
        list: A list of schema names.
    """
    schemas = get_scheming_dataset_schemas()

    return [schema["schema_name"] for schema in schemas.values()]


@helper
def schemingdcat_default_facet_search_operator():
    """Return the default facet search operator: AND/OR.

    Returns:
        str: The default facet search operator.
    """
    facet_operator = sdct_config.default_facet_operator
    if facet_operator and (
        facet_operator.upper() == "AND" or facet_operator.upper() == "OR"
    ):
        facet_operator = facet_operator.upper()
    else:
        facet_operator = "AND"
    return facet_operator


@helper
def schemingdcat_decode_json(json_text):
    """Convert a JSON string to a Python object.

    Args:
        json_text (str): The JSON string to convert.

    Returns:
        object: A Python object representing the JSON data.
    """
    return json.loads(json_text)


@helper
def schemingdcat_organization_name(org_id):
    """Return the name of the organization from its ID.

    Args:
        org_id (dict): A dictionary containing the ID of the organization.

    Returns:
        str: The name of the organization, or None if the organization cannot be found.
    """
    org_name = None
    try:
        org_dic = ckan_helpers.get_organization(org_id["display_name"])
        if org_dic is not None:
            org_name = org_dic["name"]
        else:
            log.warning(
                "Could not find the name of the organization with ID {0}".format(
                    org_id["display_name"]
                )
            )
    except Exception as e:
        log.error(
            "Exception while trying to find the name of the organization: {0}".format(e)
        )
    return org_name


@helper
def schemingdcat_get_facet_label(facet):
    """Return the label for a given facet.

    Args:
        facet (str): The name of the facet.

    Returns:
        str: The label for the given facet.
    """
    return get_facets_dict[facet]


@helper
def schemingdcat_get_facet_items_dict(
    facet, search_facets=None, limit=None, exclude_active=False, scheming_choices=None
):
    """Return the list of unselected facet items for the given facet, sorted
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

    """

    # log.debug("Returning facets for: {0}".format(facet))

    order = "default"
    items = []

    search_facets = search_facets or getattr(c, "search_facets", None)

    if (
        search_facets
        and isinstance(search_facets, dict)
        and search_facets.get(facet, {}).get("items")
    ):
        for facet_item in search_facets.get(facet)["items"]:
            if scheming_choices:
                facet_item["label"] = scheming_choices_label(
                    scheming_choices, facet_item["name"]
                )
            else:
                facet_item["label"] = facet_item["display_name"]

            if not len(facet_item["name"].strip()):
                continue

            params_items = (
                request.params.items(multi=True)
                if is_flask_request()
                else request.params.items()
            )

            if not (facet, facet_item["name"]) in params_items:
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
            "count_r": ("count", True),
        }
        if sorts.get(order):
            items.sort(
                key=lambda it: (it[sorts.get(order)[0]]), reverse=sorts.get(order)[1]
            )
        else:
            items.sort(key=lambda it: (-it["count"], it["label"].lower()))

        if hasattr(c, "search_facets_limits"):
            if c.search_facets_limits and limit is None:
                limit = c.search_facets_limits.get(facet)
        # zero treated as infinite for hysterical raisins
        if limit is not None and limit > 0:
            return items[:limit]

    return items


@helper
def schemingdcat_new_order_url(facet_name, order_concept, extras=None):
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

    controller = getattr(c, "controller", False) or request.blueprint
    action = getattr(c, "action", False) or p.toolkit.get_endpoint()[1]
    url = ckan_helpers.url_for(controller=controller, action=action, **extras)

    if len(order_lst):
        old_order = order_lst[0]

    order_mapping = {
        "name": {"name": "name_r", "name_r": None, None: "name"},
        "count": {"count": "count_r", "count_r": None, None: "count"},
    }

    new_order = order_mapping.get(order_concept, {}).get(old_order)

    params_items = (
        request.params.items(multi=True)
        if is_flask_request()
        else request.params.items()
    )
    params_nopage = [(k, v) for k, v in params_items if k != order_param]

    if new_order:
        params_nopage.append((order_param, new_order))

    if params_nopage:
        url = url + "?" + urlencode(params_nopage)

    return url

@helper
def schemingdcat_get_facet_list_limit():
    """
    Retrieves the limit for the facet list from the scheming DCAT configuration.

    Returns:
        int: The limit for the facet list.
    """
    return sdct_config.facet_list_limit

@helper
def schemingdcat_get_icons_dir(field=None, field_name=None):
    """
    Returns the defined icons directory for a given scheming field definition or field name.

    This function is used to retrieve the icons directory associated with a 
    specific field in a scheming dataset or directly by field name. If no icons directory is defined, 
    the function will return None.

    Args:
        field (dict, optional): A dictionary representing the scheming field definition. 
                                This should include all the properties of the field, 
                                including the icons directory if one is defined.
        field_name (str, optional): The name of the field. If provided, the function will 
                                     look for an icons directory with this name.

    Returns:
        str: A string representing the icons directory for the field or field name. 
             If no icons directory is defined or found, the function will return None.
    """
    if field:
        if "icons_dir" in field:
            return field["icons_dir"]

        if "field_name" in field:
            dir = sdct_config.icons_dir + "/" + field["field_name"]
            if public_dir_exists(dir):
                return dir

    elif field_name:
        dir = sdct_config.icons_dir + "/" + field_name
        if public_dir_exists(dir):
            return dir    

    return None

@helper
def schemingdcat_get_default_icon(field):
    """Return the defined default icon for a scheming field definition.

    Args:
        field (dict): The scheming field definition.

    Returns:
        str: The defined default icon, or None if not found.
    """
    if "default_icon" in field:
        return field["default_icon"]
    
@helper
def schemingdcat_get_default_package_item_icon():
    """
    Returns the default icon defined for a given scheming field definition.

    This function is used to retrieve the default icon associated with a 
    specific field in a scheming dataset. If no default icon is defined, 
    the function will return None.

    Args:
        field (dict): A dictionary representing the scheming field definition. 
                      This should include all the properties of the field, 
                      including the default icon if one is defined.

    Returns:
        str: A string representing the default icon for the field. This could 
             be a URL, a data URI, or any other string format used to represent 
             images. If no default icon is defined for the field, the function 
             will return None.
    """
    return sdct_config.default_package_item_icon

@helper
def schemingdcat_get_default_package_item_show_spatial():
    """
    Returns the configuration value for showing spatial information in the default package item.

    This function is used to retrieve the configuration value that determines 
    whether the spatial information should be shown in the default package item. 
    If no value is defined in the configuration, the function will return None.

    Returns:
        bool: A boolean value representing whether the spatial information should 
              be shown in the default package item. If no value is defined in the 
              configuration, the function will return None.
    """
    return sdct_config.default_package_item_show_spatial

@helper
def schemingdcat_get_show_metadata_templates_toolbar():
    """
    Returns the configuration value for showing the metadata templates toolbar.

    This function is used to retrieve the configuration value that determines 
    whether the metadata templates toolbar should be shown or not. If the configuration 
    value is not set, the function will return False.

    Returns:
        bool: A boolean value representing whether the metadata templates toolbar 
              should be shown. If the configuration value is not set, the function 
              will return False.
    """
    return sdct_config.show_metadata_templates_toolbar

@helper
def schemingdcat_get_metadata_templates_search_identifier():
    """
    Returns the default icon defined for a given scheming field definition.

    This function is used to retrieve the default value to retrieve metadata templates. If no default value is defined, 
    the function will return None.

    Args:
        field (dict): A dictionary representing the scheming field definition. 
                      This should include all the properties of the field, 
                      including the default icon if one is defined.

    Returns:
        str: A string representing the default icon for the field. This could 
             be a URL, a data URI, or any other string format used to represent 
             images. If no default icon is defined for the field, the function 
             will return None.
    """
    return sdct_config.metadata_templates_search_identifier

@helper
def schemingdcat_get_schemingdcat_xls_harvest_templates(search_identifier=sdct_config.metadata_templates_search_identifier, count=10):
    """
    This helper function retrieves the schemingdcat_xls templates from the CKAN instance. 
    It uses the 'package_search' action of the CKAN logic layer to perform a search with specific parameters.
    
    Parameters:
    search_identifier (str): The text to search in the identifier. Default is sdct_config.metadata_templates_search_identifier.
    count (int): The number of featured datasets to retrieve. Default is 10.

    Returns:
    list: A list of dictionaries, each representing a featured dataset. If no results are found, returns None.
    """
    fq = f'+extras_schemingdcat_xls_metadata_template:{True}'
    search_dict = {
        'fq': fq, 
        'fl': 'name,extras_identifier,title,notes,metadata_modified,extras_title_translated,extras_notes_translated',
        'rows': count
    }
    context = {'model': model, 'session': model.Session}
    result = logic.get_action('package_search')(context, search_dict)
    
    if not result['results']:
        fq = f'+extras_schemingdcat_xls_metadata_template:*{search_identifier}*'
        search_dict['fq'] = fq
        result = logic.get_action('package_search')(context, search_dict)

    return result['results'] if result['results'] else None

@helper
def schemingdcat_get_icon(
    choice=None, icons_dir=None, default="/images/default/no_icon.svg", choice_value=None
):
    """Return the relative URL to the icon for the item.

    Args:
        choice (dict, optional): The choice selected for the field.
        icons_dir (str, optional): The path to search for the icon. Usually the common path for icons for this field.
        default (str, optional): The default value to return if no icon is found.
        choice_value (str, optional): The value of the choice selected for the field. If provided, it will be used instead of choice['value'].

    Returns:
        str: The relative URL to the icon, or the default value if not found.
    """
    extensions = [".svg", ".png", ".jpg", ".jpeg", ".gif"]
    icon_name = None

    if choice_value is None and choice:
        choice_value = choice.get("icon") or choice.get("value")

    if choice_value:
        if ckan_helpers.is_url(choice_value):
            url_parts = choice_value.split("/")

            if len(url_parts) == 1:
                icon_name = url_parts[-1].lower()
            else:
                icon_name = url_parts[-2].lower() + "/" + url_parts[-1].lower()
        else:
            icon_name = choice_value

        url_path = (icons_dir + "/" if icons_dir else "") + icon_name

        for extension in extensions:
            if public_file_exists(url_path + extension):
                return url_path + extension

    return default

@helper
def schemingdcat_get_choice_item(field, value):
    """Return the whole choice item for the given value in the scheming field.

    Args:
        field (dict): The scheming field to look for the choice item in.
        value (str): The option item value.

    Returns:
        dict: The whole option item in scheming, or None if not found.
    """
    if field and ("choices" in field):
        # log.debug("Searching: {0} en {1}".format(value,field['choices']))
        for choice in field["choices"]:
            if choice["value"] == value:
                return choice

    return None

@helper
def schemingdcat_get_choice_property(choices, value, property):
    """
    Retrieve a specific property from a choice dictionary based on the given value.

    Args:
        choices (list): List of dictionaries containing "label" and "value" keys.
        value (str): The value to match against the choices.
        property (str): The property to retrieve from the matching choice dictionary.

    Returns:
        str or None: The property value from the matching choice dictionary, or None if not found.
    """
    for c in choices:
        if c['value'] == value:
            return c.get(property, None)
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
        value = value.strip(" ").replace('\\"', "%%%@#")
        value = value.replace('"', "")
        value = value.replace("%%%@#", '"')
        return value
    except (TypeError, ValueError):
        return value

def format_eli_label(parsed_url):
    """
    Formats the label for a parsed URL with 'eli' segment.

    Args:
        parsed_url (ParseResult): The parsed URL.

    Returns:
        str: The formatted label.
    """
    segments = parsed_url.path.split('/')
    eli_index = next(i for i, segment in enumerate(segments) if segment == 'eli')
    return '/'.join(segments[eli_index + 1:]).upper()

@helper
def schemingdcat_prettify_url(url):
    """
    Prettifies a URL by removing the protocol and trailing slash.

    Args:
        url (str): The URL to prettify.

    Returns:
        str: The prettified URL, or the original URL if an error occurred.
    """
    if url in prettify_cache:
        return prettify_cache[url]

    try:
        prettified_url = re.sub(r"^https?://(?:www\.)?", "", url).rstrip("/")
        prettify_cache[url] = prettified_url
        return prettified_url
    except (TypeError, AttributeError):
        return url

@helper
def schemingdcat_prettify_url_name(url):
    """
    Prettifies a URL name by extracting the last segment and cleaning it.

    Args:
        url (str): The URL to extract the name from.

    Returns:
        str: The prettified URL name, or the original URL if an error occurred.
    """
    if url is None:
        return url

    if url in prettify_cache:
        return prettify_cache[url]

    try:
        parsed_url = urlparse(url)
        
        if '/eli/' in url:
            prettified_url_name = format_eli_label(parsed_url)
        else:
            url_name = parsed_url.path.split("/")[-1].split('.')[0].replace('_', '-')
            prettified_url_name = ' '.join(url_name.split(' ')[:4])

        prettify_cache[url] = prettified_url_name
        return prettified_url_name

    except (URLError, ValueError) as e:
        print(f"Error while prettifying URL: {e}")
        return url

@helper
def schemingdcat_listify_str(values):
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
        values = values.strip("][").split(",")
        values = [item.strip().strip('"') for item in values]
    elif not isinstance(values, (list, tuple)):
        log.debug("Not a list or string: {0}".format(values))
        values = [""]

    return values

@helper
def schemingdcat_load_yaml(file, folder="codelists"):
    """Load a YAML file from the folder, by default 'codelists' directory.

    Args:
        file (str): The name of the YAML file to load.

    Returns:
        dict: A dictionary containing the data from the YAML file.
    """
    source_path = Path(__file__).resolve(True)
    yaml_data = {}
    try:
        p = source_path.parent.joinpath(folder, file)
        with open(p, "r") as f:
            yaml_data = yaml.load(f, Loader=SafeLoader)
    except FileNotFoundError:
        log.error("The file {0} does not exist".format(file))
    except Exception as e:
        log.error("Could not read configuration from {0}: {1}".format(file, e))

    return yaml_data

@helper
def schemingdcat_get_linked_data(id):
    """Get linked data for a given identifier.

    Args:
        id (str): The identifier to get linked data for.

    Returns:
        list: A list of dictionaries containing linked data for the identifier.
    """
    return [
        {
            "name": name,
            "display_name": sdct_config.linkeddata_links.get(name, {"display_name": content_type})[
                "display_name"
            ],
            "format": sdct_config.linkeddata_links.get(name, {}).get("format"),
            "image_display_url": sdct_config.linkeddata_links.get(name, {}).get(
                "image_display_url"
            ),
            "endpoint_icon": sdct_config.linkeddata_links.get(name, {}).get(
                "endpoint_icon"
            ),
            "description": sdct_config.linkeddata_links.get(name, {}).get("description")
            or f"Formats {content_type}",
            "description_url": sdct_config.linkeddata_links.get(name, {}).get("description_url"),
            "endpoint": "dcat.read_dataset",
            "endpoint_data": {
                "_id": id,
                "_format": name,
            },
        }
        for name, content_type in CONTENT_TYPES.items()
    ]

@helper
def schemingdcat_get_catalog_endpoints():
    """Get the catalog endpoints.

    Returns:
        list: A list of dictionaries containing linked data for the identifier.
    """    
    csw_uri = schemingdcat_get_geospatial_endpoint("catalog")

    return [
        {
            "name": item["name"],
            "display_name": item["display_name"],
            "format": item["format"],
            "image_display_url": item["image_display_url"],
            "endpoint_icon": item["endpoint_icon"],
            "fa_icon": item["fa_icon"],
            "description": item["description"],
            "type": item["type"],
            "profile": item["profile"],
            "profile_label": item["profile_label"],
            "endpoint": get_endpoint("catalog")
            if item.get("type").lower() == "lod"
            else csw_uri.format(version=item["version"])
            if item.get("type").lower() == "ogc"
            else None,
            "endpoint_data": {
                "_format": item["format"],
                "_external": True,
                "profiles": item["profile"],
            },
        }
        for item in sdct_config.endpoints["catalog_endpoints"]
    ]

@helper
def schemingdcat_get_geospatial_endpoint(type="dataset"):
    """Get geospatial base URI for CSW Endpoint.

    Args:
        type (str): The type of endpoint to return. Can be 'catalog' or 'dataset'.

    Returns:
        str: The base URI of the CSW Endpoint with the appropriate format.
    """
    try:
        if sdct_config.geometadata_base_uri:
            csw_uri = sdct_config.geometadata_base_uri

        if (
            sdct_config.geometadata_base_uri
            and "/csw" not in sdct_config.geometadata_base_uri
        ):
            csw_uri = sdct_config.geometadata_base_uri.rstrip("/") + "/csw"
        elif sdct_config.geometadata_base_uri == "":
            csw_uri = "/csw"
        else:
            csw_uri = sdct_config.geometadata_base_uri.rstrip("/")
    except:
        csw_uri = "/csw"

    if type == "catalog":
        return csw_uri + "?service=CSW&version={version}&request=GetCapabilities"
    else:
        return (
            csw_uri
            + "?service=CSW&version={version}&request=GetRecordById&id={id}&elementSetName={element_set_name}&outputSchema={output_schema}&OutputFormat={output_format}"
        )

@helper
def schemingdcat_get_geospatial_metadata():
    """Get geospatial metadata for CSW formats.

    Returns:
        list: A list of dictionaries containing geospatial metadata for CSW formats.
    """
    csw_uri = schemingdcat_get_geospatial_endpoint("dataset")

    return [
        {
            "name": item["name"],
            "display_name": item["display_name"],
            "format": item["format"],
            "image_display_url": item["image_display_url"],
            "endpoint_icon": item["endpoint_icon"],
            "description": item["description"],
            "description_url": item["description_url"],
            "url": csw_uri.format(
                output_format=item["output_format"],
                version=item["version"],
                element_set_name=item["element_set_name"],
                output_schema=item["output_schema"],
                id="{id}",
            ),
        }
        for item in sdct_config.geometadata_links["csw_formats"]
    ]

@helper
def schemingdcat_get_all_metadata(id):
    """Get linked data and geospatial metadata for a given identifier.

    Args:
        id (str): The identifier to get linked data and geospatial metadata for.

    Returns:
        list: A list of dictionaries containing linked data and geospatial metadata for the identifier.
    """
    geospatial_metadata = schemingdcat_get_geospatial_metadata()
    linked_data = schemingdcat_get_linked_data(id)

    for metadata in geospatial_metadata:
        metadata["endpoint_type"] = "csw"

    for data in linked_data:
        data["endpoint_type"] = "dcat"

    return geospatial_metadata + linked_data

@helper
def fluent_form_languages(field=None, entity_type=None, object_type=None, schema=None):
    """
    Return a list of language codes for this form (or form field)

    1. return field['form_languages'] if it is defined
    2. return schema['form_languages'] if it is defined
    3. get schema from entity_type + object_type then
       return schema['form_languages'] if they are defined
    4. return languages from site configuration
    """
    if field and "form_languages" in field:
        return field["form_languages"]
    if schema and "form_languages" in schema:
        return schema["form_languages"]
    if entity_type and object_type:
        # late import for compatibility with older ckanext-scheming
        from ckanext.scheming.helpers import scheming_get_schema

        schema = scheming_get_schema(entity_type, object_type)
        if schema and "form_languages" in schema:
            return schema["form_languages"]

    langs = []
    for l in get_available_locales():
        if l.language not in langs:
            langs.append(l.language)
    return langs

@helper
def schemingdcat_fluent_form_label(field, lang):
    """Returns a label for the input field in the specified language.

    If the field has a `fluent_form_label` defined, the label will be taken from there.
    If a matching label cannot be found, this helper will return the standard label
    with the language code in uppercase.

    Args:
        field (dict): A dictionary representing the input field.
        lang (str): A string representing the language code.

    Returns:
        str: A string representing the label for the input field in the specified language.
    """
    form_label = field.get("fluent_form_label", {})
    label = scheming_language_text(form_label.get(lang, field["label"]))
    return f"{label} ({lang.upper()})"

@helper
def schemingdcat_multiple_field_required(field, lang):
    """
    Returns whether a field is required or not based on the field definition and language.

    Args:
        field (dict): The field definition.
        lang (str): The language to check for required fields.

    Returns:
        bool: True if the field is required, False otherwise.
    """
    if "required" in field:
        return field["required"]
    if "required_language" in field and field["required_language"] == lang:
        return True
    return "not_empty" in field.get("validators", "").split()

def parse_json(value, default_value=None):
    try:
        return json.loads(value)
    except (ValueError, TypeError, AttributeError):
        if default_value is not None:
            return default_value
        return value

@helper
def schemingdcat_get_default_lang():
    global DEFAULT_LANG
    if DEFAULT_LANG is None:
        DEFAULT_LANG = p.toolkit.config.get("ckan.locale_default", "en")
    return DEFAULT_LANG

@helper
def schemingdcat_get_current_lang():
    """
    Returns the current language of the CKAN instance.

    Returns:
        str: The current language of the CKAN instance. If the language cannot be determined, the default language 'en' is returned.
    """
    try:
        return get_lang()
    except TypeError:
        return p.toolkit.config.get("ckan.locale_default", "en")

@helper
def schemingdcat_extract_lang_text(text, current_lang):
    """
    Extracts the text content for a specified language from a string.

    Args:
        text (str): The string to extract the language content from.
            Example: "[#en#]Welcome to the CKAN Open Data Portal.[#es#]Bienvenido al portal de datos abiertos CKAN."
        current_lang (str): The language code to extract the content for.
            Example: "es"

    Returns:
        str: The extracted language content, or the original string if no content is found.
            Example: "Bienvenido al portal de datos abiertos CKAN."

    """

    @lru_cache(maxsize=30)
    def process_language_content(language_label, text):
        """Helper function to process the content for a specific language label.

        Args:
            language_label (str): The language label to process.
            text (str): The text to process.

        Returns:
            str: The text corresponding to the specified language label.

        """
        pattern = re.compile(r'\[#(.*?)#\](.*?)(?=\[#|$)', re.DOTALL)
        matches = pattern.findall(text)

        for lang, content in matches:
            if lang == language_label.replace('[#', '').replace('#]', ''):
                return content.strip()

        return ''

    lang_label = f"[#{current_lang}#]"
    default_lang = schemingdcat_get_default_lang()
    default_lang_label = f"[#{default_lang}#]"

    lang_text = process_language_content(lang_label, text)

    if not lang_text and lang_label != default_lang_label:
        lang_text = process_language_content(default_lang_label, text)

    if not lang_text:
        return text

    return lang_text

@helper
def dataset_display_name(package_or_package_dict):
    """
    Returns the localized value of the dataset name by extracting the correct translation.

    Args:
    - package_or_package_dict: A dictionary containing the package information.

    Returns:
    - The localized value of the dataset name.
    """
    field_name = "title" if "title" in package_or_package_dict else "name"

    return schemingdcat_get_localized_value_from_dict(
        package_or_package_dict, field_name
    )


@helper
def dataset_display_field_value(package_or_package_dict, field_name):
    """
    Extracts the correct translation of the dataset field.

    Args:
        package_or_package_dict (dict): The package or package dictionary to extract the value from.
        field_name (str): The name of the field to extract the value for.

    Returns:
        str: The localized value for the given field name.
    """
    return schemingdcat_get_localized_value_from_dict(
        package_or_package_dict, field_name
    )

@helper
def schemingdcat_get_localized_value_from_dict(
    package_or_package_dict, field_name, default=""
):
    """
    Get the localized value from a dictionary.

    This function tries to get the value of a field in a specific language.
    If the value is not available in the specific language, it tries to get it in the default language.
    If the value is not available in the default language, it tries to get the untranslated value.
    If the untranslated value is not available, it returns a default value.

    Args:
        package_or_package_dict (dict or str): The package or dictionary to get the value from.
            If it's a string, it tries to convert it to a dictionary using json.loads.
        field_name (str): The name of the field to get the value from.
        default (str, optional): The default value to return if the value is not available. Defaults to "".

    Returns:
        str: The localized value, or the default value if the localized value is not available.
    """
    if isinstance(package_or_package_dict, str):
        try:
            package_or_package_dict = json.loads(package_or_package_dict)
        except ValueError:
            return default

    lang_code = schemingdcat_get_current_lang().split("_")[0]
    schemingdcat_get_default_lang()

    translated_field = package_or_package_dict.get(field_name + "_translated", {})
    if isinstance(translated_field, str):
        try:
            translated_field = json.loads(translated_field)
        except ValueError:
            translated_field = {}

    # Check the lang_code, if not check the default_lang, if not check the field without translation
    return translated_field.get(lang_code) or translated_field.get(DEFAULT_LANG) or package_or_package_dict.get(field_name, default)

@helper
def schemingdcat_get_readable_file_size(num, suffix="B"):
    if not num:
        return False
    try:
        for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
            num = float(num)
            if abs(num) < 1024.0:
                return "%3.1f%s%s" % (num, unit, suffix)
            num /= 1024.0
        return "%.1f%s%s" % (num, "Y", suffix)
    except ValueError:
        return False

@helper
def schemingdcat_get_group_or_org(id, type="group"):
    """
    Retrieve information about a group or organization in CKAN.

    Args:
        id (str): The ID of the group or organization.
        type (str, optional): The type of the entity to retrieve. Defaults to 'group'.

    Returns:
        dict: A dictionary containing information about the group or organization.
    """
    return logic.get_action(f"{type}_show")({}, {"id": id})

@helper
def schemingdcat_package_list_for_source(source_id):
    '''
    Creates a dataset list with the ones belonging to a particular harvest
    source.

    It calls the package_list snippet and the pager.
    '''
    limit = 20
    page = int(request.args.get('page', 1))
    fq = '+harvest_source_id:"{0}"'.format(source_id)
    search_dict = {
        'fq': fq,
        'rows': limit,
        'sort': 'metadata_modified desc',
        'start': (page - 1) * limit,
        'include_private': True
    }

    context = {'model': model, 'session': model.Session}
    harvest_source = get_harvest_source(source_id)
    owner_org = harvest_source.get('owner_org', '')
    if owner_org:
        user_member_of_orgs = [org['id'] for org
                               in ckan_helpers.organizations_available('read')]
        if (harvest_source and owner_org in user_member_of_orgs):
            context['ignore_capacity_check'] = True

    query = logic.get_action('package_search')(context, search_dict)

    base_url = ckan_helpers.url_for(
        '{0}.read'.format(DATASET_TYPE_NAME),
        id=harvest_source['name']
    )

    def pager_url(q=None, page=None):
        url = base_url
        if page:
            url += '?page={0}'.format(page)
        return url

    pager = ckan_helpers.Page(
        collection=query['results'],
        page=page,
        url=pager_url,
        item_count=query['count'],
        items_per_page=limit
    )
    pager.items = query['results']

    if query['results']:
        out = ckan_helpers.snippet('snippets/package_list.html', packages=query['results'])
        out += pager.pager()
    else:
        out = ckan_helpers.snippet('snippets/package_list_empty.html')

    return out
@helper
def schemingdcat_package_count_for_source(source_id):
    '''
    Returns the current package count for datasets associated with the given
    source id
    '''
    fq = '+harvest_source_id:"{0}"'.format(source_id)
    search_dict = {'fq': fq, 'include_private': True}
    context = {'model': model, 'session': model.Session}
    result = logic.get_action('package_search')(context, search_dict)
    return result.get('count', 0)

@helper
def schemingdcat_parse_localised_date(date_=None):
    '''Parse a datetime object or timestamp string as a localised date.
    If timestamp is badly formatted, then None is returned.

    :param date_: the date
    :type date_: datetime or date or ISO string format
    :rtype: date
    '''
    if not date_:
        return None
    if isinstance(date_, str):
        try:
            date_ = ckan_helpers.date_str_to_datetime(date_)
        except (TypeError, ValueError):
            return None
    # check we are now a datetime or date
    if isinstance(date_, datetime.datetime):
        date_ = date_.date()
    elif not isinstance(date_, datetime.date):
        return None

    # Format date based on locale
    locale = schemingdcat_get_current_lang()
    if locale == 'es':
        return date_.strftime('%d-%m-%Y')
    else:
        return date_.strftime('%Y-%m-%d')

@lru_cache(maxsize=None)
@helper
def schemingdcat_get_dataset_schema(schema_type="dataset"):
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

@helper
def schemingdcat_get_schema_form_groups(entity_type=None, object_type=None, schema=None):
    """
    Return a list of schema metadata groups for this form.

    1. return schema['schema_form_groups'] if it is defined
    2. get schema from entity_type + object_type then
       return schema['schema_form_groups'] if they are defined
    """
    if schema and "schema_form_groups" in schema:
        return schema["schema_form_groups"]
    elif entity_type and object_type:
        schema = scheming_get_schema(entity_type, object_type)
        return schema["schema_form_groups"] if schema and "schema_form_groups" in schema else None
    else:
        return None

# Vocabs
@helper
def get_inspire_themes(*args, **kwargs) -> typing.List[typing.Dict[str, str]]:
    log.debug(f"inside get_inspire_themes {args=} {kwargs=}")
    try:
        inspire_themes = p.toolkit.get_action("tag_list")(
            data_dict={"vocabulary_id": sdct_config.SCHEMINGDCAT_INSPIRE_THEMES_VOCAB}
        )
    except p.toolkit.ObjectNotFound:
        inspire_themes = []
    return [{"value": t, "label": t} for t in inspire_themes] 

@helper
def get_ckan_cleaned_name(name):
    """
    Cleans a name by removing accents, special characters, and spaces.

    Args:
        name (str): The name to clean.

    Returns:
        str: The cleaned name.
    """
    MAX_TAG_LENGTH = 100
    MIN_TAG_LENGTH = 2
    # Define a dictionary to map accented characters to their unaccented equivalents except ñ
    accent_map = {
        "á": "a", "à": "a", "ä": "a", "â": "a", "ã": "a",
        "é": "e", "è": "e", "ë": "e", "ê": "e",
        "í": "i", "ì": "i", "ï": "i", "î": "i",
        "ó": "o", "ò": "o", "ö": "o", "ô": "o", "õ": "o",
        "ú": "u", "ù": "u", "ü": "u", "û": "u",
        "ñ": "ñ",
    }

    # Convert the name to lowercase
    name = name.lower()

    # Replace accented and special characters with their unaccented equivalents or -
    name = "".join(accent_map.get(c, c) for c in name)
    name = re.sub(r"[^a-zñ0-9_.-]", "-", name.strip())

    # Truncate the name to MAX_TAG_LENGTH characters
    name = name[:MAX_TAG_LENGTH]

    # If the name is shorter than MIN_TAG_LENGTH, pad it with underscores
    if len(name) < MIN_TAG_LENGTH:
        name = name.ljust(MIN_TAG_LENGTH, '_')

    return name

@helper
def get_featured_datasets(count=1):
    """
    This helper function retrieves a specified number of featured datasets from the CKAN instance. 
    It uses the 'package_search' action of the CKAN logic layer to perform a search with specific parameters.
    
    Parameters:
    count (int): The number of featured datasets to retrieve. Default is 1.

    Returns:
    list: A list of dictionaries, each representing a featured dataset.
    """
    fq = '+featured:true'
    search_dict = {
        'fq': fq, 
        'sort': 'metadata_modified desc',
        'fl': 'id,name,title,notes,state,metadata_modified,type,extras_featured,extras_graphic_overview',
        'rows': count
    }
    context = {'model': model, 'session': model.Session}
    result = logic.get_action('package_search')(context, search_dict)
    
    return result['results']

@helper
def get_spatial_datasets(count=10):
    """
    This helper function retrieves a specified number of featured datasets from the CKAN instance. 
    It uses the 'package_search' action of the CKAN logic layer to perform a search with specific parameters.
    
    Parameters:
    count (int): The number of featured datasets to retrieve. Default is 1.

    Returns:
    list: A list of dictionaries, each representing a featured dataset.
    """
    fq = '+dcat_type:*inspire*'
    search_dict = {
        'fq': fq, 
        'fl': 'extras_dcat_type',
        'rows': count
    }
    context = {'model': model, 'session': model.Session}
    result = logic.get_action('package_search')(context, search_dict)
    
    return result['results']

@lru_cache(maxsize=None)
@helper
def get_header_endpoint_url(endpoint, site_protocol_and_host):
    url_for = ckan_helpers.url_for
    endpoint_type = endpoint['type']
    endpoint_value = endpoint['endpoint']

    if endpoint_type == 'ogc':
        if ckan_helpers.is_url(endpoint_value):
            return ckan_helpers.url_for_static_or_external(endpoint_value)
        else:
            protocol, host = site_protocol_and_host
            return f"{protocol}://{host}/{endpoint_value}"
    elif endpoint_type == 'ckan':
        return url_for('api.action', ver=3, logic_function='package_list', qualified=True)
    elif endpoint_type == 'lod':
        return url_for(endpoint_value, **endpoint['endpoint_data'])
    elif endpoint_type == 'sparql':
        return url_for('/sparql')
    
@helper
def schemingdcat_check_valid_url(url):
    """
    Check if a string is a valid URL.

    Args:
        url (str): The string to check.

    Returns:
        bool: True if the string is a valid URL, False otherwise.
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False