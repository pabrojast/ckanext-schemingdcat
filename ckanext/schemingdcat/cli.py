# -*- coding: utf-8 -*-

from __future__ import print_function

import ckantoolkit as tk
import click
import logging

import ckanext.schemingdcat.utils as utils

import ckanext.schemingdcat.config as sdct_config
import ckanext.scheming.helpers as sh
import ckanext.schemingdcat.helpers as helpers

log = logging.getLogger(__name__)


def get_commands():
    return [schemingdcat]

@click.group()
def schemingdcat():
    """
    This is the main entry point for the CLI. It groups all the schemingdcat commands together.
    """
    pass
   
def create_vocab(vocab_name, schema_name="dataset", lang="en"):
    """
    This function creates a CKAN tag vocabulary and adds configured INSPIRE themes to it.

    Parameters:
    vocab_name (str): The name of the vocabulary to be created.
    schema_name (str, optional): The name of the schema. Defaults to "dataset".
    lang (str, optional): The language for the vocabulary. Defaults to "en".

    The function first retrieves the site user and the list of vocabularies. It checks if the
    vocabulary already exists. If it does, it skips the creation step. If it doesn't, it creates a new vocabulary.

    Then, it retrieves the dataset schema and checks if the vocabulary field exists. If it
    does, it iterates over the field choices. For each choice, it checks if the tag already
    exists in the vocabulary. If it doesn't, it creates a new tag.

    This function can be safely called multiple times. It will only create the vocabulary and
    tags once.

    Returns:
    None
    """
    log.info(
        "Creating '{0}' CKAN tag vocabulary and adding configured INSPIRE themes to it...".format(
            vocab_name
        )
    )

    user = tk.get_action("get_site_user")({"ignore_auth": True}, {})
    context = {"user": user["name"]}
    vocab_list = tk.get_action("vocabulary_list")(context)
    for voc in vocab_list:
        if voc["name"] == vocab_name:
            vocabulary = voc
            log.info(
                "Vocabulary '{0}' already exists, skipping creation...".format(
                    vocab_name
                )
            )
            break
    else:
        log.info(
            "Creating vocabulary {0}...".format(
                vocab_name
            )
        )
        vocabulary = tk.get_action("vocabulary_create")(
            context, {"name": vocab_name}
        )

    schema = helpers.schemingdcat_get_dataset_schema(schema_name)
    vocab_field = next((field for field in schema["dataset_fields"] if field['field_name'] == vocab_name), None)

    #log.debug(sh.scheming_field_choices(vocab_field))
    if vocab_field:
        for tag_name in sh.scheming_field_choices(vocab_field):
            if tag_name['value'] != "":
                vocab_value = helpers.get_ckan_cleaned_name(tag_name['value'].split('/')[-1])
                vocab_label = sh.scheming_language_text(tag_name['label'], lang)
                already_exists = vocab_value in [tag["name"] for tag in vocabulary["tags"]]
                if not already_exists:
                    log.info(
                        "Adding tag '{0}' and label to vocabulary {1}...".format(
                            vocab_value,
                            vocab_name
                        )
                    )
                    tk.get_action("tag_create")(
                        context, {"name": vocab_value, "vocabulary_id": vocabulary["id"]}
                    )
                else:
                    log.info(
                        "Tag '{0}' is already part of the {1} vocabulary, skipping...".format(
                            vocab_value,
                            vocab_name
                        )
                    )
        log.info("Done!")
        
    else:
        log.warning(
            "No field {0} in schema: {1}".format(
                vocab_name,
                schema_name
            )
        )

def delete_vocab(vocab_name):
    """
    This function deletes a CKAN tag vocabulary and its respective tags.

    Parameters:
    vocab_name (str): The name of the vocabulary to be deleted.

    The function first retrieves the site user and the list of vocabularies. It checks if the
    vocabulary exists. If it does, it logs a message and retrieves the tags in the vocabulary.

    For each tag, it logs a message and deletes the tag. After all tags have been deleted, it
    logs a message and deletes the vocabulary.

    If the vocabulary does not exist, it logs a message and does nothing.

    This function can be safely called even if the vocabulary does not exist. It will not
    raise an error in this case.

    Returns:
    None
    """
    user = tk.get_action("get_site_user")({"ignore_auth": True}, {})
    context = {"user": user["name"]}
    vocabulary_list = tk.get_action("vocabulary_list")(context)
    if vocab_name in [voc["name"] for voc in vocabulary_list]:
        log.info(
            "Deleting {0} CKAN tag vocabulary and respective tags...".format(
                vocab_name
            )
        )
        existing_tags = tk.get_action("tag_list")(
            context, {"vocabulary_id": vocab_name}
        )
        for tag_name in existing_tags:
            log.info("Deleting tag {0}...".format(tag_name))
            tk.get_action("tag_delete")(
                context, {"id": tag_name, "vocabulary_id": vocab_name}
            )
        log.info("Deleting vocabulary {0}...".format(vocab_name))
        tk.get_action("vocabulary_delete")(
            context, {"id": vocab_name}
        )
    else:
        log.info(
            "Vocabulary {0} does not exist, nothing to do".format(
                vocab_name
            )
        )
    log.info("Done!")
    
def manage_vocab(vocab_name, schema_name="dataset", lang="en", delete=False):
    """
    Base function to create or delete a CKAN vocabulary and manage its tags.

    This function retrieves the site user and the list of vocabularies. It checks if the
    vocabulary already exists. If it does and delete is False, it skips the creation step. If it
    doesn't and delete is False, it creates a new vocabulary.

    Then, it retrieves the dataset schema and checks if the vocabulary field exists. If it
    does, it iterates over the field choices. For each choice, it checks if the tag already
    exists in the vocabulary. If it doesn't and delete is False, it creates a new tag. If it does
    and delete is True, it deletes the tag.

    This function can be safely called multiple times. It will only create or delete the vocabulary and tags once.

    Raises:
        None

    Returns:
        None
    """

    if delete:
        delete_vocab(vocab_name)
    else:
        create_vocab(vocab_name, schema_name, lang)
        

@schemingdcat.command()
@click.option("-l", "--lang", default="en", show_default=True)
def create_inspire_tags(lang):
    """
    This command creates the INSPIRE themes vocabulary.

    Args:
        lang (str, optional): The language for the vocabulary. Defaults to "en".

    This command calls the manage_vocab function with the INSPIRE themes vocabulary name,
    the default dataset schema name, and the provided language. The manage_vocab function
    will create the vocabulary and add the INSPIRE themes to it.

    Returns:
        None
    """
    manage_vocab(sdct_config.SCHEMINGDCAT_INSPIRE_THEMES_VOCAB, sdct_config.SCHEMINGDCAT_DEFAULT_DATASET_SCHEMA_NAME, lang)

@schemingdcat.command()
def delete_inspire_tags():
    """
    This command deletes the INSPIRE themes vocabulary.

    This command calls the manage_vocab function with the INSPIRE themes vocabulary name,
    the default dataset schema name, and the delete flag set to True. The manage_vocab function
    will delete the vocabulary and all its tags.

    Returns:
        None
    """
    manage_vocab(sdct_config.SCHEMINGDCAT_INSPIRE_THEMES_VOCAB, sdct_config.SCHEMINGDCAT_DEFAULT_DATASET_SCHEMA_NAME, delete=True)

@schemingdcat.command()
@click.option("-l", "--lang", default="en", show_default=True)
def create_dcat_tags(lang):
    """
    This command creates the DCAT themes vocabularies.

    Args:
        lang (str, optional): The language for the vocabularies. Defaults to "en".

    This command iterates over the DCAT themes vocabulary names and calls the manage_vocab
    function with each vocabulary name, the default dataset schema name, and the provided language.
    The manage_vocab function will create each vocabulary and add the DCAT themes to it.

    Returns:
        None
    """
    for theme in sdct_config.SCHEMINGDCAT_DCAT_THEMES_VOCAB:
        manage_vocab(theme, sdct_config.SCHEMINGDCAT_DEFAULT_DATASET_SCHEMA_NAME, lang)

@schemingdcat.command()
def delete_dcat_tags():
    """
    This command deletes the DCAT themes vocabularies.

    This command iterates over the DCAT themes vocabulary names and calls the manage_vocab
    function with each vocabulary name, the default dataset schema name, and the delete flag set to True.
    The manage_vocab function will delete each vocabulary and all its tags.

    Returns:
        None
    """
    for theme in sdct_config.SCHEMINGDCAT_DCAT_THEMES_VOCAB:
        manage_vocab(theme, sdct_config.SCHEMINGDCAT_DEFAULT_DATASET_SCHEMA_NAME, delete=True)
        
@schemingdcat.command()
@click.option("-l", "--lang", default="en", show_default=True)
def create_iso_topic_tags(lang):
    """
    This command creates the ISO 19115 topics vocabulary.

    Args:
        lang (str, optional): The language for the vocabulary. Defaults to "en".

    This command calls the manage_vocab function with the ISO 19115 topics vocabulary name,
    the default dataset schema name, and the provided language. The manage_vocab function
    will create the vocabulary and add the ISO 19115 topics to it.

    Returns:
        None
    """
    manage_vocab(sdct_config.SCHEMINGDCAT_ISO19115_TOPICS_VOCAB, sdct_config.SCHEMINGDCAT_DEFAULT_DATASET_SCHEMA_NAME, lang)

@schemingdcat.command()
def delete_iso_topic_tags():
    """
    This command deletes the ISO 19115 topics vocabulary.

    This command calls the manage_vocab function with the ISO 19115 topics vocabulary name,
    the default dataset schema name, and the delete flag set to True. The manage_vocab function
    will delete the vocabulary and all its tags.

    Returns:
        None
    """
    manage_vocab(sdct_config.SCHEMINGDCAT_ISO19115_TOPICS_VOCAB, sdct_config.SCHEMINGDCAT_DEFAULT_DATASET_SCHEMA_NAME, delete=True)