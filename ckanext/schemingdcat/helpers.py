from ckan.common import json, c, request, is_flask_request
from ckan.lib import helpers as ckan_helpers
import ckan.logic as logic
from ckan.lib.i18n import get_available_locales, get_lang
import ckan.plugins as p
import six
import re
import yaml
from yaml.loader import SafeLoader
from pathlib import Path
from functools import lru_cache

from six.moves.urllib.parse import urlencode

from ckanext.scheming.helpers import (
    scheming_choices_label,
    scheming_language_text,
    scheming_dataset_schemas,
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
def schemingdcat_get_icons_dir(field):
    """Return the defined icons directory for a scheming field definition.

    Args:
        field (dict): The scheming field definition.

    Returns:
        str: The defined icons directory, or None if not found.
    """
    if field:
        if "icons_dir" in field:
            return field["icons_dir"]

        if "field_name" in field:
            dir = sdct_config.icons_dir + "/" + field["field_name"]
            if public_dir_exists(dir):
                return dir
        # log.debug("No directory found for {0}".format(field['field_name']))

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
def schemingdcat_get_icon(
    choice, icons_dir=None, default="/images/default/no_icon.svg"
):
    """Return the relative URL to the icon for the item.

    Args:
        choice (dict): The choice selected for the field.
        icons_dir (str, optional): The path to search for the icon. Usually the common path for icons for this field.
        default (str, optional): The default value to return if no icon is found.

    Returns:
        str: The relative URL to the icon, or the default value if not found.
    """
    extensions = [".svg", ".png", ".jpg", ".gif"]
    icon_name = None
    # log.debug("Field value: {0}".format(choice))

    if choice:
        if "icon" in choice:
            return (icons_dir + "/" if icons_dir else "") + choice["icon"]

        if ckan_helpers.is_url(choice["value"]):
            url_parts = choice["value"].split("/")

            if len(url_parts) == 1:
                icon_name = url_parts[-1].lower()
            else:
                icon_name = url_parts[-2].lower() + "/" + url_parts[-1].lower()
        else:
            icon_name = choice["value"]

        url_path = (icons_dir + "/" if icons_dir else "") + icon_name
        # log.debug("Searching for: {0}".format(url_path))

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


@helper
def schemingdcat_prettify_url(url):
    """Clean a URL to remove 'http://', 'https://', and 'www.'.

    Args:
        url (str): The URL to clean.

    Returns:
        str: The cleaned URL.
    """
    try:
        cleaned_url = re.sub(r"^https?://(?:www\.)?", "", url).rstrip("/")
        return cleaned_url
    except AttributeError:
        return url


@helper
def schemingdcat_prettify_url_name(url):
    """Extracts the name of the last segment of a URL.

    Args:
        url (str): The URL to extract the name from.

    Returns:
        str: The name of the last segment of the URL.
    """
    url_name = url.split("/")[-1] if "/" in url else url

    if url_name is not None:
        url_name = re.sub(r"^https?://", "", url_name)
    else:
        url_name = re.sub(r"^https?://", "", url)

    return url_name


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
    linkeddata_links = (
        schemingdcat_load_yaml("linkeddata_links.yaml")
        if sdct_config.debug
        else sdct_config.linkeddata_links
    )

    return [
        {
            "name": name,
            "display_name": linkeddata_links.get(name, {"display_name": content_type})[
                "display_name"
            ],
            "format": linkeddata_links.get(name, {}).get("format"),
            "image_display_url": linkeddata_links.get(name, {}).get(
                "image_display_url"
            ),
            "description": linkeddata_links.get(name, {}).get("description")
            or f"Formats {content_type}",
            "description_url": linkeddata_links.get(name, {}).get("description_url"),
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
    endpoints = (
        schemingdcat_load_yaml("endpoints.yaml")
        if sdct_config.debug
        else sdct_config.endpoints
    )

    csw_uri = schemingdcat_get_geospatial_endpoint("catalog")

    return [
        {
            "name": item["name"],
            "display_name": item["display_name"],
            "format": item["format"],
            "image_display_url": item["image_display_url"],
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
        for item in endpoints["catalog_endpoints"]
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
    geometadata_links = (
        schemingdcat_load_yaml("geometadata_links.yaml")
        if sdct_config.debug
        else sdct_config.geometadata_links
    )

    csw_uri = schemingdcat_get_geospatial_endpoint("dataset")

    return [
        {
            "name": item["name"],
            "display_name": item["display_name"],
            "format": item["format"],
            "image_display_url": item["image_display_url"],
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
        for item in geometadata_links["csw_formats"]
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
def schemingdcat_get_default_lang():
    return p.toolkit.config.get("ckan.locale_default", "en")


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
    """Extracts the text content for a specified language from a string.

    Args:
        text (str): The string to extract the language content from.
        current_lang (str): The language code to extract the content for.

    Returns:
        str: The extracted language content, or the original string if no content is found.

    """

    def process_language_content(language_label):
        """Helper function to process the content for a specific language label.

        Args:
            language_label (str): The language label to process.

        Returns:
            list: A list of lines containing the language content.

        """
        lang_text = []
        in_target_lang = False
        for line in text.split("\n"):
            if line.startswith(language_label):
                in_target_lang = True
            elif (
                in_target_lang
                and line.strip().startswith("[#")
                and line.strip().endswith("#]")
            ):
                break
            elif in_target_lang:
                lang_text.append(line)
        return lang_text

    lang_label = f"[#{current_lang}#]"
    default_lang = schemingdcat_get_default_lang()
    default_lang_label = f"[#{default_lang}#]"

    lang_text = process_language_content(lang_label)

    if not lang_text and lang_label != default_lang_label:
        lang_text = process_language_content(default_lang_label)

    if not lang_text:
        return text

    return "\n".join(lang_text)


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

    return scheming_dct_get_localized_value_from_dict(
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
    return scheming_dct_get_localized_value_from_dict(
        package_or_package_dict, field_name
    )


@helper
def scheming_dct_get_localized_value_from_dict(
    package_or_package_dict, field_name, default=""
):
    """
    Returns the localized value for a given field name from the provided package or package dictionary.

    Args:
        package_or_package_dict (str or dict): The package or package dictionary to extract the value from.
        field_name (str): The name of the field to extract the value for.
        default (str, optional): The default value to return if the field is not found. Defaults to ''.

    Returns:
        str: The localized value for the given field name, or the default value if the field is not found.
    """
    if isinstance(package_or_package_dict, str):
        try:
            package_or_package_dict = json.loads(package_or_package_dict)
        except ValueError:
            return default

    lang_code = schemingdcat_get_current_lang().split("_")[0]
    default_lang_code = schemingdcat_get_default_lang()

    translated_package_or_package_dict = package_or_package_dict.get(
        field_name + "_translated", {}
    )

    # Check the lang_code, if not check the default_lang, if not check the field without translation
    value = (
        translated_package_or_package_dict.get(lang_code, None)
        or translated_package_or_package_dict.get(default_lang_code, None)
        or package_or_package_dict.get(field_name, None)
    )

    return value if value is not None else default


@helper
def scheming_dct_get_readable_file_size(num, suffix="B"):
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
