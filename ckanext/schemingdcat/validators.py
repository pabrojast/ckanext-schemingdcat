import json
import re
import six

import ckanext.scheming.helpers as sh
import ckan.lib.helpers as h
from urllib.parse import urlparse
from ckantoolkit import (
    config,
    get_validator,
    UnknownValidator,
    missing,
    Invalid,
    StopOnError,
    _,
    unicode_safe,
)

import datetime

import logging
from wsgiref.validate import validator
from ckanext.fluent.helpers import (
    fluent_form_languages, fluent_alternate_languages)

from ckanext.fluent.validators import (
    BCP_47_LANGUAGE, fluent_text_output, scheming_language_text, LANG_SUFFIX)

from ckanext.schemingdcat.utils import parse_json

log = logging.getLogger(__name__)

all_validators = {}

FORM_EXTRAS = ('__extras',)

def validator(fn):
    """
    collect validator functions into ckanext.schemingdcat.all_validators dict
    """
    all_validators[fn.__name__] = fn
    return fn

def scheming_validator(fn):
    """
    Decorate a validator that needs to have the scheming fields
    passed with this function. When generating navl validator lists
    the function decorated will be called passing the field
    and complete schema to produce the actual validator for each field.
    """
    fn.is_a_scheming_validator = True
    return fn

@scheming_validator
@validator
def schemingdcat_multiple_choice(field, schema):
    """
    Accept zero or more values from a list of choices and convert
    to a json list for storage. Also act like scheming_required to check for at least one non-empty string when required is true:
    1. a list of strings, eg.:
       ["choice-a", "choice-b"]
    2. a single string for single item selection in form submissions:
       "choice-a"
    """
    static_choice_values = None
    if 'choices' in field:
        static_choice_order = [c['value'] for c in field['choices']]
        static_choice_values = set(static_choice_order)
    def validator(key, data, errors, context):
        # if there was an error before calling our validator
        # don't bother with our validation
        if errors[key]:
            return

        value = data[key]
        # 1. single string to List or 2. List
        if value is not missing:
            if isinstance(value, six.string_types):
                if "[" not in value:
                    value = value.split(",")
                else:
                    value = json.loads(value)
            if not isinstance(value, list):
                errors[key].append(_('expecting list of strings'))
                raise StopOnError
        else:
            value = []
        choice_values = static_choice_values
        if not choice_values:
            choice_order = [
                choice['value']
                for choice in sh.scheming_field_choices(field)
            ]
            choice_values = set(choice_order)
        selected = set()
        for element in value:
            if element in choice_values:
                selected.add(element)
                continue
            errors[key].append(_('unexpected choice "%s"') % element)

        if not errors[key]:
            # Return as a JSON string list of values
            data[key] = json.dumps([v for v in
                (static_choice_order if static_choice_values else choice_order)
                if v in selected], ensure_ascii=False)

            if field.get('required') and not selected:
                errors[key].append(_('Select at least one'))
    return validator

@validator
def schemingdcat_valid_json_object(value, context):
    """Store a JSON object as a serialized JSON string
    It accepts two types of inputs:
        1. A valid serialized JSON string (it must be an object or a list)
        2. An object that can be serialized to JSON
    Returns a parsing JSON string 
    """
    if not value:
        return
    elif isinstance(value, six.string_types):
        try:
            loaded = json.loads(value)
            if not isinstance(loaded, dict):
                raise Invalid(
                    _('Unsupported value for JSON field: {}').format(value)
                )

            return json.dumps(loaded, ensure_ascii=False)
        except (ValueError, TypeError) as e:
            raise Invalid(_('Invalid JSON string: {}').format(e))

    elif isinstance(value, dict):
        try:
            return json.dumps(value, ensure_ascii=False)
        except (ValueError, TypeError) as e:
            raise Invalid(_('Invalid JSON object: {}').format(e))
    else:
        raise Invalid(
            _('Unsupported type for JSON field: {}').format(type(value))
        )


@scheming_validator
@validator
def schemingdcat_multiple_text(field, schema):
    """
    Accept repeating text input in the following forms and convert to a json list for storage.
    1. a list of strings, eg.
       ["Person One", "Person Two"]
    2. a single string value to allow single text fields to be
       migrated to repeating text
       "Person One"
    """

    def _scheming_multiple_text(key, data, errors, context):
        # just in case there was an error before our validator,
        # bail out here because our errors won't be useful
        if errors[key]:
            return

        value = data[key]
        # 1. single string to List or 2. List
        if value is not missing:
            if isinstance(value, six.string_types):
                if "[" not in value:
                    value = value.split(",")
                else:
                    value = json.loads(value)
            if not isinstance(value, list):
                errors[key].append(_('expecting list of strings'))
                raise StopOnError
            out = []
            for element in value:
                if not element:
                    continue
                if not isinstance(element, six.string_types):
                    errors[key].append(_('invalid type for repeating text: %r')
                                       % element)
                    continue
                if isinstance(element, six.binary_type):
                    try:
                        element = element.decode('utf-8')
                        element = element.strip()
                    except UnicodeDecodeError:
                        errors[key]. append(_('invalid encoding for "%s" value')
                                            % element)
                        continue

                # Avoid errors
                if '"' in element:
                    element=element.replace('"', '\"')
                if h.is_url(element):
                    element=element.replace(' ', '')
                out.append(element)

            if errors[key]:
                raise StopOnError

            # Return as a JSON string list of values
            if not errors[key]:
                data[key] = json.dumps([v for v in out], ensure_ascii=False)

        if (data[key] is missing or data[key] == '[]') and field.get('required'):
            errors[key].append(_('Missing value'))
            raise StopOnError
    return _scheming_multiple_text


@scheming_validator
@validator
def schemingdcat_valid_url(field, schema):
    """Validates a URL field.

    This validator checks if the value of the field is a string and starts with 'http'. If the value is not a string or does not start with 'http', it adds an error message to the errors dictionary.

    Args:
        field (dict): The field to validate.
            A dictionary containing information about the field to be validated.
        schema (dict): The schema for the field.
            A dictionary containing the schema for the field to be validated.

    Returns:
        function: A validation function that can be used to validate the field.

    """
    def validator(key, data, errors, context):
        value = data[key].strip()
        
        if value is missing or value is None or value == '':
            data[key] = value
            return validator
        elif not isinstance(value, six.string_types):
            errors[key].append(_('URL must be a string'))
        elif not value.startswith('http'):
            errors[key].append(_('Please provide a valid URL'))
            
        data[key] = value

    return validator

@validator
def schemingdcat_clean_identifier(value: str) -> str:
    """
    Cleans a value by removing spaces at the beginning and end of the string and replacing spaces between letters with underscores.
    
    Args:
    - value: A string representing the value.
    
    Returns:
    - The cleaned value string.
    """
    if not value.startswith('http'):
        value = value.strip().replace(' ', '-').strip()
    
    return value

@scheming_validator
@validator
def name_identifier_validator(field, schema):
    """Validates and normalizes a name field.

    This validator checks if the value of the field is a URL and, if so, extracts the last part of the URL as the name. If the value is not a URL but starts with 'http', it extracts the last part of the string after splitting it by '-' characters.

    Args:
        field (dict): The field to validate.
        schema (dict): The schema for the field.
    """
    def validator(key, data, errors, context):        
        value = data[key]
                
        if value.startswith('http'):
            data[key] = value.split('-')[-1].strip()
        elif check_url(value):
            data[key] = value.split('/')[-1].strip()

    return validator

# ckanext-fluent
@scheming_validator
@validator
def schemingdcat_translated_output(field, schema):
    """
    Output validator that returns a value for a core field using a multilingual dict.
    
    Args:
    - field: A dictionary containing the field information.
    - schema: A dictionary containing the schema information.
    
    Returns:
    - A validator function that returns a value for a core field using a multilingual dict.
    """
    assert field['field_name'].endswith(LANG_SUFFIX), 'Output validator "fluent_core_translated" must only used on a field that ends with "_translated"'

    required_langs = schema.get('required_language', field.get('required_language'))
    if required_langs and not isinstance(required_langs, list):
        required_langs = [required_langs]
    
    lang = required_langs[0] if required_langs else config.get('ckan.locale_default', 'en')

    def validator(key, data, errors, context):
        """
        Return a value for a core field using a multilingual dict.
        """
        data[key] = fluent_text_output(data[key])

        k = key[-1]
        new_key = key[:-1] + (k[:-len(LANG_SUFFIX)],)

        if new_key in data:
            data[new_key] = scheming_language_text(data[key], lang)

    return validator


@scheming_validator
@validator
def schemingdcat_fluent_core_translated_output(field, schema):
    """
    Output validator that returns a value for a core field using a multilingual dict.
    
    Args:
    - field: A dictionary containing the field information.
    - schema: A dictionary containing the schema information.
    
    Returns:
    - A validator function that returns a value for a core field using a multilingual dict.
    """
    assert field['field_name'].endswith(LANG_SUFFIX), 'Output validator "fluent_core_translated" must only used on a field that ends with "_translated"'

    required_langs = schema.get('required_language', field.get('required_language'))
    if required_langs and not isinstance(required_langs, list):
        required_langs = [required_langs]
    
    lang = required_langs[0] if required_langs else config.get('ckan.locale_default', 'en')

    def validator(key, data, errors, context):
        """
        Return a value for a core field using a multilingual dict.
        """
        data[key] = fluent_text_output(data[key])

        k = key[-1]
        new_key = key[:-1] + (k[:-len(LANG_SUFFIX)],)

        if new_key in data:
            data[new_key] = scheming_language_text(data[key], lang)

    return validator

@scheming_validator
@validator
def schemingdcat_fluent_text(field, schema):
    """
    Accept multilingual text input in the following forms
    and convert to a json string for storage:

    1. a multilingual dict, eg.

       {"en": "Text", "fr": "texte"}

    2. a JSON encoded version of a multilingual dict, for
       compatibility with old ways of loading data, eg.

       '{"en": "Text", "fr": "texte"}'

    3. separate fields per language (for form submissions):

       fieldname-en = "Text"
       fieldname-fr = "texte"

    When using this validator in a ckanext-scheming schema setting
    "required" to true will make all required_language key required to
    pass validation.
    
    When type is group or organization and field name is title, the display_name field will be populated with the value of the first required language.
    
    4. If the value is missing and is required, an error message will be added to the errors list.
    
    5. If the value is missing and is not required, an empty JSON string will be assigned to the data key.
    """
    # combining scheming required checks and fluent field processing
    # into a single validator makes this validator more complicated,
    # but should be easier for fluent users and eliminates quite a
    # bit of duplication in handling the different types of input
    required_langs = []
    form_languages = fluent_form_languages(field, schema=schema)
    alternate_langs = {}
    if field and field.get('required'):
        if field.get('required_language'):
            if isinstance(field.get('required_language'), list):
                required_langs = field.get('required_language')
            else:
                required_langs = [field.get('required_language')]
        alternate_langs = fluent_alternate_languages(field, schema=schema)

    #log.debug("Start | required_langs: {0}".format(required_langs))
    #log.debug("Start | field: {0}".format(field))

    def validator(key, data, errors, context):
        # just in case there was an error before our validator,
        # bail out here because our errors won't be useful
        if errors[key]:
            return

        value = data[key]
        pkg_type = data.get(key[:-1] + ('type',), {})

        #log.debug("Start | key: {0}".format(key))
        #log.debug("Start | key: {0} and data:{1}".format(key, data))

        # Extract any extras from the data dictionary that match the prefix
        try:
            extras = data.get(key[:-1] + ('__extras',), {})
        except:
            extras = None

        # Extract the last character of the key and append a hyphen to it
        prefix = key[-1] + '-'
        
        # Check if extras is not None and contains keys starting with the fluent prefix
        extras_mode = extras is not None and any(name.startswith(prefix) for name in extras.keys())

        #log.debug("Start | extras_mode: {1} and extras: {0}".format(extras, extras_mode))

        # 1 or 2. dict or JSON encoded string
        if value is not missing and (value != '' and not field.get('required')) and extras_mode is False:
            #log.debug("1-2 | key: {0} - value: {1}".format(key, value))
            if isinstance(value, six.string_types):
                try:
                    value = json.loads(value)
                except ValueError:
                    errors[key].append(_('Failed to decode JSON string'))
                    return
                except UnicodeDecodeError:
                    errors[key].append(_('Invalid encoding for JSON string'))
                    return
            if not isinstance(value, dict):
                errors[key].append(_('expecting JSON object'))
                return

            for lang, text in value.items():
                try:
                    m = re.match(BCP_47_LANGUAGE, lang)
                except TypeError:
                    errors[key].append(_('invalid type for language code: %r')
                        % lang)
                    continue
                if not m:
                    errors[key].append(_('invalid language code: "%s"') % lang)
                    continue
                if not isinstance(text, six.string_types):
                    errors[key].append(_('invalid type for "%s" value') % lang)
                    continue
                if isinstance(text, str):
                    try:
                        value[lang] = text if six.PY3 else text.decode(
                            'utf-8')
                    except UnicodeDecodeError:
                        errors[key]. append(_('invalid encoding for "%s" value')
                            % lang)

            for lang in required_langs:
                if value.get(lang) or any(
                        value.get(l) for l in alternate_langs.get(lang, [])):
                    continue
                errors[key].append(_('Required language "%s" missing') % lang)

            if not errors[key]:
                data[key] = json.dumps(value)
                #log.debug("1-2 | output: {0}".format(data))
            return

        # 3. separate fields
        if extras_mode:
            #log.debug("3 | key: {0}".format(key))
            output = {}
            extras = data.get(key[:-1] + ('__extras',), {})

            for name, text in extras.items():
                if not name.startswith(prefix):
                    continue
                lang = name.split('-', 1)[1]
                m = re.match(BCP_47_LANGUAGE, lang)
                if not m:
                    errors[name] = [_('invalid language code: "%s"') % lang]
                    output = None
                    continue

                if output is not None:
                    output[lang] = text

            for lang in required_langs:
                if extras.get(prefix + lang) or any(
                        extras.get(prefix + l) for l in alternate_langs.get(lang, [])):
                    continue
                errors[key[:-1] + (key[-1] + '-' + lang,)] = [_('Missing value')]
                output = None

            if output is None:
                return

            for lang in output:
                del extras[prefix + lang]
            data[key] = json.dumps(output)
            #log.debug("3 | output: {0}".format(data))

            # group/organizations display_name fields
            if pkg_type in ('group', 'organization') and 'title' in ''.join(key):
                try:
                    lang = required_langs[0] if required_langs else config.get('ckan.locale_default', 'en')
                    display_name = ('display_name',)
                    #log.debug('3-group/organization | output[lang]: {0} and data: {1}'.format(output[lang], data))
                    data[display_name] = output[lang] or ''
                except ValueError:
                    data[display_name] = ''

        # 4. value is missing and is required
        if (value is missing) and field.get('required'):
            errors[key].append(_('Missing value'))
            return

        # 5. value is missing and is not required and is fluent field
        if (value is missing) and not field.get('required'):
            data[key] = {language: "" for language in form_languages}

    return validator

@scheming_validator
@validator
def schemingdcat_if_empty_same_as_title(field, schema):
    """
    Returns a validator function that sets a value for a core field using a multilingual dict.

    Args:
        field (dict): The field to validate.
        schema (dict): The schema for the field.

    Returns:
        function: A validator function that sets a value for a core field using a multilingual dict.
    """
    required_langs = schema.get('required_language', field.get('required_language'))
    if required_langs and not isinstance(required_langs, list):
        required_langs = [required_langs]
    
    lang = required_langs[0] if required_langs else config.get('ckan.locale_default', 'en')

    def validator(key, data, errors, context):
        """
        Return a value for a core field check a multilingual dict.
        """
        # title_translated
        fallback_key = 'title' + LANG_SUFFIX
        pkg_type = data.get(key[:-1] + ('type',), {})
        
        extras = schemingdcat_get_extras(data, pkg_type)
        output = json.loads(extras.get(fallback_key, '{}')).get(lang, '')

        data[key] = output
        #log.debug('schemingdcat_if_empty_same_as_title | output: {0}'.format(output))

    return validator

@scheming_validator
@validator
def schemingdcat_if_empty_datenow(field, schema):
    """
    Returns a validator function that sets the current datetime as the value for a field if it's empty.

    This validator checks if the value of the field is missing, None, or an empty string. If so, it sets the current datetime in ISO format as the value of the field.

    Args:
        field (dict): The field to validate.
            A dictionary containing information about the field to be validated.
        schema (dict): The schema for the field.
            A dictionary containing the schema for the field to be validated.

    Returns:
        function: A validation function that can be used to validate the field and set the current datetime if it's empty.
    """
    def validator(key, data, errors, context):
        value = data[key]
        
        if value is missing or value is None or value == '':
            data[key] = datetime.datetime.now().isoformat()

    return validator

@scheming_validator
@validator
def schemingdcat_update_modified(field, schema):
    """
    Returns a validator function that always sets the current datetime as the value for a field.

    This validator does not check the current value of the field. It always sets the current datetime in ISO format as the value of the field.

    Args:
        field (dict): The field to update.
            A dictionary containing information about the field to be updated.
        schema (dict): The schema for the field.
            A dictionary containing the schema for the field to be updated.

    Returns:
        function: A validation function that can be used to update the field with the current datetime.
    """
    def validator(key, data, errors, context):
        data[key] = datetime.datetime.now().isoformat()

    return validator

@validator
def multilingual_text_output(value):
    """
    Returns a multilingual dictionary representation of the stored JSON value.
    If the value is already a dictionary, it is returned as is.

    Args:
        value (str or dict): The value to convert to a multilingual dictionary.

    Returns:
        dict: A multilingual dictionary representation of the stored JSON value.
    """
    if isinstance(value, dict):
        return value
    return parse_json(value)
    
def schemingdcat_get_extras(data, pkg_type='dataset'):
    """
    Returns the extras for a given package type from the provided data dictionary.

    Args:
        data (dict): The data dictionary to extract extras from.
        pkg_type (str, optional): The package type to extract extras for. Defaults to 'dataset'.

    Returns:
        dict: A dictionary containing the extras for the given package type.
    """
    extras = {}
    try:
        if pkg_type == 'dataset':
            extras = data.get(key[:-1] + ('__extras',), {})
            return extras
        elif pkg_type in ('group', 'organization'):
            for key, value in data.items():
                if isinstance(key, tuple) and key[0] == 'extras' and key[2] == '__extras':
                    extras[value['key']] = value['value']
            return extras
    except:
        return extras

@scheming_validator
@validator
def schemingdcat_multiple_choice_custom_tag_string(field, schema):
    """
    Accept zero or more values from a list of choices and convert
    to a json list for storage. Also act like scheming_required to check for at least one non-empty string when required is true:
    1. a list of strings, eg.:
       ["choice-a", "choice-b"]
    2. a single string for single item selection in form submissions:
       "choice-a"
    """
    static_choice_values = None
    if 'choices' in field:
        static_choice_order = [c['value'] for c in field['choices']]
        static_choice_values = set(static_choice_order)
    def validator(key, data, errors, context):
        # if there was an error before calling our validator
        # don't bother with our validation
        if errors[key]:
            return

        value = data[key]
        
        # 1. single string to List or 2. List to string comma separated
        if value is not missing:
            if isinstance(value, six.string_types):
                if "," not in value:
                    # If there are no commas, treat the whole string as one value
                    value = [value]
                elif "[" not in value:
                    # If there are commas but no brackets, split on commas
                    value = value.split(",")
                else:
                    # If there are brackets, assume it's a JSON array
                    value = json.loads(value)
            if not isinstance(value, list):
                errors[key].append(_('expecting list of strings'))
                raise StopOnError
        else:
            value = []
        choice_values = static_choice_values
        if not choice_values:
            choice_order = [
                choice['value']
                for choice in sh.scheming_field_choices(field)
            ]
            choice_values = set(choice_order)
        selected = set()
        for element in value:
            if element in choice_values:
                selected.add(element)
                continue
            errors[key].append(_('unexpected choice "%s"') % element)

        if not errors[key]:
            # Return as a comma-separated string of values
            data[key] = ','.join([v for v in
                (static_choice_order if static_choice_values else choice_order)
                if v in selected])

            if field.get('required') and not selected:
                errors[key].append(_('Select at least one'))
    
    return validator

@validator
def schemingdcat_multiple_choice_custom_tag_output(value):
    """
    Output validator that returns a list of values for a field.
    
    This function takes a value and checks if it is a list. If it is, it returns the list as is.
    If the value is a string that can be loaded as a JSON, it does so and returns the result.
    If the value is a string containing commas, it splits the string into a list of strings.
    If the value is a string without commas, it returns a list containing the string.
    
    Args:
    - value: The value to be processed.
    
    Returns:
    - A list of values derived from the input value.
    """
    if isinstance(value, list):
        return value
    try:
        return json.loads(value)
    except ValueError:
        if ',' in value:
            return [tag_string.strip() for tag_string in value.split(',') if tag_string.strip()]
        else:
            return [value]

@validator
def copy_from(copy_key):
    def validator(key, data, errors, context):
        current_value = data.get(key)
        if current_value and current_value is not missing:
            return
        value = data.pop((copy_key, ), None)
        if not value:
            value = data.get(('__extras', ), {}).get(copy_key)
        if value is not missing:
            data[key] = value

    return validator

def check_url(url):
    """Checks if a given URL is valid.

    Args:
        url (str): The URL to check.

    Returns:
        bool: True if the URL is valid, False otherwise.
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False