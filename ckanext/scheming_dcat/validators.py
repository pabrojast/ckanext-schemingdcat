import json
import six
import ckanext.scheming.helpers as sh
import ckan.lib.helpers as h
from urllib.parse import urlparse

from ckantoolkit import (
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

logger = logging.getLogger(__name__)

all_validators = {}


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

