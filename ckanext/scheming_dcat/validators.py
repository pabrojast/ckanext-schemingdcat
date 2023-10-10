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

import logging
from wsgiref.validate import validator
from ckanext.fluent.helpers import (
    fluent_form_languages, fluent_alternate_languages)

from ckanext.fluent.validators import (
    BCP_47_LANGUAGE, fluent_text_output, scheming_language_text, LANG_SUFFIX)

logger = logging.getLogger(__name__)

all_validators = {}

FORM_EXTRAS = ('__extras',)

def validator(fn):
    """
    collect helper functions into ckanext.scheming_dcat.all_helpers dict
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
def scheming_dcat_multiple_choice(field, schema):
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
def scheming_dcat_valid_json_object(value, context):
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
def scheming_dcat_multiple_text(field, schema):
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


@validator
def scheming_dcat_valid_url(value: str) -> str:
    """
    Check if value is a valid URL string
    """
    def check_url(url):
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False

    if not isinstance(value, six.string_types):
        raise Invalid(_('URL must be a string'))
    try:
        if check_url(value):
            return value
    except (ValueError) as e:
        raise Invalid(_('URL must be a string'))


# ckanext-fluent
@scheming_validator
@validator
def scheming_dcat_translated_output(field, schema):
    assert field['field_name'].endswith(LANG_SUFFIX), 'Output validator "fluent_core_translated" must only used on a field that ends with "_translated"'

    def validator(key, data, errors, context):
        """
        Return a value for a core field using a multilingual dict.
        """
        data[key] = fluent_text_output(data[key])

        k = key[-1]
        new_key = key[:-1] + (k[:-len(LANG_SUFFIX)],)

        if new_key in data:
            data[new_key] = scheming_language_text(data[key], config.get('ckan.locale_default', 'en'))

    return validator


@scheming_validator
@validator
def scheming_dcat_fluent_text(field, schema):
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


    #logger.debug("Start | required_langs: {0}".format(required_langs))
    #logger.debug("Start | field: {0}".format(field))

    def validator(key, data, errors, context):
        # just in case there was an error before our validator,
        # bail out here because our errors won't be useful
        if errors[key]:
            return

        value = data[key]

        logger.debug("Start | key: {0}".format(key))
        #logger.debug("Start | key: {0} and data:{1}".format(key, data))

        # Extract any extras from the data dictionary that match the prefix
        try:
            extras = data.get(key[:-1] + ('__extras',), {})
        except:
            extras = None

        # Extract the last character of the key and append a hyphen to it
        prefix = key[-1] + '-'
        
        # Check if extras is not None and contains keys starting with the fluent prefix
        extras_mode = extras is not None and any(name.startswith(prefix) for name in extras.keys())

        #logger.debug("Start | extras_mode: {1} and extras: {0}".format(extras, extras_mode))

        # 1 or 2. dict or JSON encoded string
        if value is not missing and (value is not '' and not field.get('required')) and extras_mode is False:
            logger.debug("1-2 | key: {0} - value: {1}".format(key, value))
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
                logger.debug("1-2 | output: {0}".format(data))
            return

        # 3. separate fields
        if extras_mode:
            #logger.debug("3 | key: {0}".format(key))
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
            logger.debug("3 | output: {0}".format(data))

        # 4. value is missing and is required
        if (value is missing) and field.get('required'):
            errors[key].append(_('Missing value'))
            return

        # 5. value is missing and is not required and is fluent field
        if (value is missing) and not field.get('required'):
            data[key] = {language: "" for language in form_languages}

    return validator