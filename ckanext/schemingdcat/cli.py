# -*- coding: utf-8 -*-

from __future__ import print_function

import ckantoolkit as tk
import click
import logging

import ckanext.schemingdcat.config as sdct_config
import ckanext.scheming.helpers as sh
import ckanext.schemingdcat.helpers as helpers

log = logging.getLogger(__name__)


def get_commands():
    return [schemingdcat]


@click.group()
def schemingdcat():
    """Main entry point for CLI. Groups all schemingdcat commands."""
    pass


def create_vocab(vocab_name, schema_name="dataset", lang="en"):
    """
    Create a CKAN tag vocabulary and add configured INSPIRE themes to it.

    Args:
        vocab_name: The name of the vocabulary to be created.
        schema_name: The name of the schema. Defaults to "dataset".
        lang: The language for the vocabulary. Defaults to "en".

    The function retrieves the site user and vocabularies list. It checks if
    the vocabulary exists. If not, it creates a new one.

    Then it retrieves the dataset schema and checks if the vocabulary field
    exists. For each choice, it checks if the tag exists; if not, creates it.

    Can be safely called multiple times - only creates vocabulary/tags once.
    """
    log.info(
        "Creating '%s' CKAN tag vocabulary...", vocab_name
    )

    user = tk.get_action("get_site_user")({"ignore_auth": True}, {})
    context = {"user": user["name"]}
    vocab_list = tk.get_action("vocabulary_list")(context)
    for voc in vocab_list:
        if voc["name"] == vocab_name:
            vocabulary = voc
            log.info("Vocabulary '%s' already exists, skipping...", vocab_name)
            break
    else:
        log.info("Creating vocabulary %s...", vocab_name)
        vocabulary = tk.get_action("vocabulary_create")(
            context, {"name": vocab_name}
        )

    schema = helpers.schemingdcat_get_dataset_schema(schema_name)
    vocab_field = next(
        (f for f in schema["dataset_fields"] if f['field_name'] == vocab_name),
        None
    )

    # log.debug(sh.scheming_field_choices(vocab_field))
    if vocab_field:
        for tag_name in sh.scheming_field_choices(vocab_field):
            if tag_name['value'] != "":
                vocab_value = helpers.get_ckan_cleaned_name(
                    tag_name['value'].split('/')[-1]
                )
                already_exists = vocab_value in [
                    tag["name"] for tag in vocabulary["tags"]
                ]
                if not already_exists:
                    log.info(
                        "Adding tag '%s' to vocabulary %s...",
                        vocab_value, vocab_name
                    )
                    tk.get_action("tag_create")(
                        context,
                        {"name": vocab_value, "vocabulary_id": vocabulary["id"]}
                    )
                else:
                    log.info(
                        "Tag '%s' already in %s vocabulary, skipping...",
                        vocab_value, vocab_name
                    )
        log.info("Done!")
    else:
        log.warning("No field %s in schema: %s", vocab_name, schema_name)


def delete_vocab(vocab_name):
    """
    Delete a CKAN tag vocabulary and its respective tags.

    Args:
        vocab_name: The name of the vocabulary to be deleted.

    The function retrieves the site user and vocabularies. If the vocabulary
    exists, it deletes all tags then deletes the vocabulary.

    Can be safely called even if the vocabulary does not exist.
    """
    user = tk.get_action("get_site_user")({"ignore_auth": True}, {})
    context = {"user": user["name"]}
    vocabulary_list = tk.get_action("vocabulary_list")(context)
    if vocab_name in [voc["name"] for voc in vocabulary_list]:
        log.info("Deleting %s CKAN tag vocabulary and tags...", vocab_name)
        existing_tags = tk.get_action("tag_list")(
            context, {"vocabulary_id": vocab_name}
        )
        for tag_name in existing_tags:
            log.info("Deleting tag %s...", tag_name)
            tk.get_action("tag_delete")(
                context, {"id": tag_name, "vocabulary_id": vocab_name}
            )
        log.info("Deleting vocabulary %s...", vocab_name)
        tk.get_action("vocabulary_delete")(context, {"id": vocab_name})
    else:
        log.info("Vocabulary %s does not exist, nothing to do", vocab_name)
    log.info("Done!")


def manage_vocab(vocab_name, schema_name="dataset", lang="en", delete=False):
    """
    Base function to create or delete a CKAN vocabulary and manage its tags.

    Retrieves the site user and vocabularies. Creates or deletes vocabulary
    and tags based on the delete flag.

    Can be safely called multiple times.
    """
    if delete:
        delete_vocab(vocab_name)
    else:
        create_vocab(vocab_name, schema_name, lang)


@schemingdcat.command()
@click.option("-l", "--lang", default="en", show_default=True)
def create_inspire_tags(lang):
    """Create the INSPIRE themes vocabulary."""
    manage_vocab(
        sdct_config.SCHEMINGDCAT_INSPIRE_THEMES_VOCAB,
        sdct_config.SCHEMINGDCAT_DEFAULT_DATASET_SCHEMA_NAME,
        lang
    )


@schemingdcat.command()
def delete_inspire_tags():
    """Delete the INSPIRE themes vocabulary."""
    manage_vocab(
        sdct_config.SCHEMINGDCAT_INSPIRE_THEMES_VOCAB,
        sdct_config.SCHEMINGDCAT_DEFAULT_DATASET_SCHEMA_NAME,
        delete=True
    )


@schemingdcat.command()
@click.option("-l", "--lang", default="en", show_default=True)
def create_dcat_tags(lang):
    """Create the DCAT themes vocabularies."""
    for theme in sdct_config.SCHEMINGDCAT_DCAT_THEMES_VOCAB:
        manage_vocab(
            theme,
            sdct_config.SCHEMINGDCAT_DEFAULT_DATASET_SCHEMA_NAME,
            lang
        )


@schemingdcat.command()
def delete_dcat_tags():
    """Delete the DCAT themes vocabularies."""
    for theme in sdct_config.SCHEMINGDCAT_DCAT_THEMES_VOCAB:
        manage_vocab(
            theme,
            sdct_config.SCHEMINGDCAT_DEFAULT_DATASET_SCHEMA_NAME,
            delete=True
        )


@schemingdcat.command()
@click.option("-l", "--lang", default="en", show_default=True)
def create_iso_topic_tags(lang):
    """Create the ISO 19115 topics vocabulary."""
    manage_vocab(
        sdct_config.SCHEMINGDCAT_ISO19115_TOPICS_VOCAB,
        sdct_config.SCHEMINGDCAT_DEFAULT_DATASET_SCHEMA_NAME,
        lang
    )


@schemingdcat.command()
def delete_iso_topic_tags():
    """Delete the ISO 19115 topics vocabulary."""
    manage_vocab(
        sdct_config.SCHEMINGDCAT_ISO19115_TOPICS_VOCAB,
        sdct_config.SCHEMINGDCAT_DEFAULT_DATASET_SCHEMA_NAME,
        delete=True
    )
