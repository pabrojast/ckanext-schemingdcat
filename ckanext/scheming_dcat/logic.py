from ckantoolkit import side_effect_free

from ckanext.scheming_dcat.helpers import schemingdct_get_schema_names


@side_effect_free
def scheming_dcat_dataset_schema_name(context, data_dict):
    """
    Returns a list of schema names for the scheming_dcat extension.

    Args:
        context (dict): The context of the API call.
        data_dict (dict): The data dictionary containing any additional parameters.

    Returns:
        list: A list of schema names.
    """
    return schemingdct_get_schema_names()