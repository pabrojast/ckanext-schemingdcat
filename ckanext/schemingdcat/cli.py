# -*- coding: utf-8 -*-

from __future__ import print_function

import json

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


# Formats that the spatial analyser knows how to inspect.
# Mirrors the candidate list used at upload time in
# SchemingDCATPlugin._should_extract_metadata. CSV/XLS(X) are included
# because the tabular extractor now derives a bounding box from
# latitude/longitude columns when present.
_SPATIAL_FORMATS = {
    'shp', 'zip', 'tif', 'tiff', 'geotiff',
    'kml', 'kmz', 'geojson', 'gpkg',
    'csv', 'xls', 'xlsx',
}


def _resource_spatial_candidate(resource):
    """Return True if the resource looks like a spatial file we can analyse."""
    import os
    fmt = (resource.get('format') or '').lower().strip()
    if fmt in _SPATIAL_FORMATS:
        return True
    url = resource.get('url') or ''
    if not url:
        return False
    clean_url = url.split('?')[0].split('#')[0]
    ext = os.path.splitext(clean_url)[1].lower().lstrip('.')
    return ext in _SPATIAL_FORMATS


@schemingdcat.command()
@click.option('-d', '--dataset-id', 'dataset_id', default=None,
              help='Run only on this dataset (id or name). Repeat for several.',
              multiple=True)
@click.option('-o', '--organization', 'organization', default=None,
              help='Restrict to datasets belonging to this organization (id or name).')
@click.option('--limit', type=int, default=None,
              help='Process at most this many datasets.')
@click.option('--skip-with-member-states/--include-with-member-states',
              default=True,
              help='Skip datasets that already have at least one member-state '
                   'group assigned. Defaults to skipping. New countries are '
                   'always merged with existing memberships when included.')
@click.option('--sync/--queue', default=False,
              help='Run the extraction synchronously in this process (default) '
                   'or enqueue it on the CKAN jobs queue (--queue).')
@click.option('--dry-run', is_flag=True, default=False,
              help='List the datasets/resources that would be processed and exit.')
def assign_member_states(dataset_id, organization, limit,
                         skip_with_member_states, sync, dry_run):
    """Retroactively detect and assign member-state groups from existing
    SHP/TIF (and other spatial) resources.

    Existing group memberships and spatial extents are preserved: the
    underlying job merges newly detected countries/geometries with what
    the dataset already has, it never removes them.
    """
    import time
    user = tk.get_action('get_site_user')({'ignore_auth': True}, {})
    context = {'user': user['name'], 'ignore_auth': True}

    package_search = tk.get_action('package_search')
    package_show = tk.get_action('package_show')

    org_filter = None
    if organization:
        try:
            org = tk.get_action('organization_show')(context, {'id': organization})
            org_filter = org['name']
        except Exception as err:
            raise click.ClickException(
                f"Organization '{organization}' not found: {err}"
            )

    def _iter_packages():
        if dataset_id:
            for ident in dataset_id:
                try:
                    yield package_show(context, {'id': ident})
                except Exception as err:
                    click.echo(f"  ! could not load dataset '{ident}': {err}",
                               err=True)
            return

        rows = 200
        start = 0
        fq_parts = ['+state:active']
        if org_filter:
            fq_parts.append(f'+organization:{org_filter}')
        fq = ' '.join(fq_parts)

        while True:
            result = package_search(context, {
                'q': '*:*',
                'fq': fq,
                'rows': rows,
                'start': start,
                'include_private': True,
            })
            results = result.get('results') or []
            if not results:
                return
            for pkg in results:
                # package_search results omit some extras (e.g. groups list
                # may be truncated); refetch full package_show payload so we
                # can reliably inspect groups + resources.
                try:
                    yield package_show(context, {'id': pkg['id']})
                except Exception as err:
                    click.echo(f"  ! could not load dataset '{pkg.get('name')}': {err}",
                               err=True)
            start += len(results)
            if start >= result.get('count', 0):
                return

    # Resolve job function lazily so the CLI loads even if jobs.py has
    # optional spatial deps missing at import time.
    from ckanext.schemingdcat.jobs import extract_comprehensive_metadata_job

    processed_pkgs = 0
    processed_resources = 0
    skipped_with_groups = 0
    enqueued = 0

    for pkg in _iter_packages():
        if limit is not None and processed_pkgs >= limit:
            break

        groups = pkg.get('groups') or []
        if skip_with_member_states and groups:
            # Heuristic: any existing group counts as "already classified".
            # Users can override with --include-with-member-states; the job
            # itself will still only add missing countries.
            skipped_with_groups += 1
            continue

        spatial_resources = [
            r for r in (pkg.get('resources') or [])
            if _resource_spatial_candidate(r) and r.get('url')
        ]
        if not spatial_resources:
            continue

        processed_pkgs += 1
        click.echo(
            f"[{processed_pkgs}] {pkg.get('name')} "
            f"({len(spatial_resources)} spatial resource(s))"
        )

        for resource in spatial_resources:
            resource_id = resource.get('id')
            click.echo(
                f"    - {resource.get('format') or '?':<8} "
                f"{resource_id} :: {resource.get('name') or resource.get('url')}"
            )
            if dry_run:
                continue

            job_payload = {
                'resource_id': resource_id,
                'resource_url': resource.get('url'),
                'resource_format': resource.get('format'),
                'package_id': pkg.get('id'),
            }

            if sync:
                try:
                    extract_comprehensive_metadata_job(job_payload)
                    processed_resources += 1
                except Exception as err:
                    click.echo(f"      ! extraction failed: {err}", err=True)
                # Small pause to avoid hammering remote storage when many
                # resources share the same backend.
                time.sleep(0.1)
            else:
                try:
                    from ckan.lib import jobs
                    job = jobs.enqueue(
                        extract_comprehensive_metadata_job,
                        [job_payload],
                        title=f"schemingdcat retroactive member-state {resource_id}",
                        queue='default',
                        rq_kwargs={'timeout': 600},
                    )
                    click.echo(f"      -> queued as job {job.id}")
                    enqueued += 1
                except Exception as err:
                    click.echo(f"      ! could not enqueue job: {err}", err=True)

    click.echo("")
    click.echo("Done.")
    click.echo(f"  Datasets processed:        {processed_pkgs}")
    click.echo(f"  Datasets skipped (have groups): {skipped_with_groups}")
    if dry_run:
        click.echo("  (dry-run, no changes applied)")
    elif sync:
        click.echo(f"  Resources analysed inline: {processed_resources}")
    else:
        click.echo(f"  Resources enqueued:        {enqueued}")


# Scheming fields stored as package extras via convert_to_extras that
# package_show must promote to the top level. If any of them shows up inside a
# dataset's cached ``extras`` list, the Solr ``validated_data_dict`` is the
# unpromoted/corrupted form that drives the metadata-wipe-on-resource-update bug.
_UNPROMOTED_MARKER_FIELDS = ('title_translated', 'notes_translated', 'dcat_type',
                             'language', 'topic')


def _cached_validated_data_dict(name_or_id):
    """Return the Solr-cached validated_data_dict for a dataset, or None."""
    from ckan.lib import search
    try:
        result = search.show(name_or_id)
    except Exception:
        return None
    raw = (result or {}).get('validated_data_dict')
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


def _is_unpromoted_cache(vdd):
    """True when the cached validated_data_dict has scheming fields stranded in extras."""
    if not vdd:
        return False
    extra_keys = {e.get('key') for e in (vdd.get('extras') or []) if isinstance(e, dict)}
    return any(f in extra_keys for f in _UNPROMOTED_MARKER_FIELDS)


@schemingdcat.command()
@click.option('-d', '--dataset', 'datasets', default=None, multiple=True,
              help='Repair only this dataset (id or name). Repeat for several. '
                   'When omitted, scans all active datasets.')
@click.option('--apply/--dry-run', default=False,
              help='Apply the reindex (--apply) or only list affected datasets '
                   '(--dry-run, the default).')
@click.option('--limit', type=int, default=None,
              help='Process at most this many affected datasets.')
def repair_unpromoted_cache(datasets, apply, limit):
    """Heal datasets whose Solr cache holds an *unpromoted* validated_data_dict.

    Such datasets return their scheming fields (title_translated, dcat_type, …)
    inside ``extras`` instead of at the top level, which makes a later
    package_update wipe them. This command re-reads each affected dataset fresh
    (use_cache=False, which promotes the fields correctly) and re-indexes it so
    the cached data is correct again. It never writes to the package row, only
    to the search index.
    """
    from ckan.lib import search
    from ckan import model

    user = tk.get_action('get_site_user')({'ignore_auth': True}, {})
    base_ctx = {'user': user['name'], 'ignore_auth': True, 'use_cache': False}
    package_show = tk.get_action('package_show')

    def _iter_names():
        if datasets:
            for ident in datasets:
                yield ident
            return
        q = (model.Session.query(model.Package.name)
             .filter(model.Package.state == 'active')
             .filter(model.Package.type == 'dataset'))
        for (name,) in q.yield_per(500):
            yield name

    pkg_index = search.index_for(model.Package)

    scanned = 0
    affected = 0
    repaired = 0
    for name in _iter_names():
        scanned += 1
        if not _is_unpromoted_cache(_cached_validated_data_dict(name)):
            continue
        if limit is not None and affected >= limit:
            break
        affected += 1
        click.echo(f"[unpromoted] {name}")
        if not apply:
            continue
        try:
            # use_cache=False forces a fresh, validated (promoted) read.
            promoted = package_show(dict(base_ctx), {'id': name})
            # A fully-promoted dict may omit the now-empty ``extras`` key, but
            # scheming's show-validate inside index_package does
            # ``data_dict['extras']`` directly -> KeyError. Guarantee the key.
            promoted.setdefault('extras', [])
            pkg_index.update_dict(promoted, defer_commit=False)
            repaired += 1
        except Exception as err:
            click.echo(f"  ! could not repair '{name}': {err}", err=True)

    if apply:
        try:
            search.commit()
        except Exception:
            pass

    click.echo("")
    click.echo("Done.")
    click.echo(f"  Datasets scanned:  {scanned}")
    click.echo(f"  Unpromoted cache:  {affected}")
    if apply:
        click.echo(f"  Reindexed:         {repaired}")
    else:
        click.echo("  (dry-run, no changes applied; pass --apply to reindex)")


def _slug_norm(value):
    """Normalise a string for slug comparison (lowercase, only alnum)."""
    if not value:
        return ''
    return ''.join(ch for ch in str(value).lower() if ch.isalnum())


def _fluent_en(value):
    """Best-effort 'en' text from a fluent value (dict or JSON string)."""
    if isinstance(value, str):
        stripped = value.strip()
        if stripped[:1] == '{':
            try:
                value = json.loads(stripped)
            except (ValueError, TypeError):
                return stripped
        else:
            return stripped
    if isinstance(value, dict):
        return value.get('en') or next((v for v in value.values() if v), '') or ''
    return ''


def _title_is_clobbered(pkg):
    """True when the dataset title is the URL slug verbatim (wiped).

    ``if_empty_same_as(name)`` sets the title to the slug *verbatim* when the
    fluent value is empty, so the precise signature is literal equality with the
    name. A real, human-cased title that merely normalises to the same slug
    (e.g. "TerriaJS Map Catalog in JSON Format") is intentionally NOT flagged.
    """
    name = pkg.get('name') or ''
    title_en = (_fluent_en(pkg.get('title_translated')) or pkg.get('title') or '').strip()
    return bool(name) and title_en == name


def _parse_pycsw_xml(path):
    """Parse a ckan2pycsw ISO-19139 XML -> (dataset_keys, title, abstract).

    dataset_keys is the set of dataset id/slug tokens found in embedded
    ``/dataset/<token>/`` URLs, used to match the record to a CKAN dataset.
    """
    import re
    import xml.etree.ElementTree as ET

    try:
        tree = ET.parse(path)
    except Exception:
        return set(), '', ''
    root = tree.getroot()

    def _local(tag):
        return tag.split('}')[-1]

    title = ''
    abstract = ''
    for el in root.iter():
        ln = _local(el.tag)
        if ln in ('title', 'abstract'):
            cs = next((c.text for c in el.iter() if _local(c.tag) == 'CharacterString' and c.text), None)
            if cs:
                if ln == 'title' and not title:
                    title = cs.strip()
                elif ln == 'abstract' and not abstract:
                    abstract = cs.strip()

    raw = ''
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
            raw = fh.read()
    except Exception:
        raw = ''
    keys = set(re.findall(r'/dataset/([0-9a-fA-F-]{36}|[a-z0-9][a-z0-9_-]+)/', raw))
    return keys, title, abstract


@schemingdcat.command()
@click.option('--metadata-dir', default=None,
              help='Path to a local copy of the ckan2pycsw /app/metadata ISO-XML '
                   'directory (e.g. via `kubectl cp`). When omitted, the command '
                   'only lists clobbered datasets without attempting recovery.')
@click.option('-d', '--dataset', 'datasets', default=None, multiple=True,
              help='Limit to these datasets (id or name). Repeat for several.')
@click.option('--apply/--dry-run', default=False,
              help='Apply the recovery via package_patch (--apply) or preview '
                   '(--dry-run, the default).')
@click.option('--limit', type=int, default=None,
              help='Process at most this many clobbered datasets.')
def recover_clobbered_metadata(metadata_dir, datasets, apply, limit):
    """List datasets whose title was overwritten with the URL slug and, when a
    ckan2pycsw XML directory is provided, restore the real title/abstract via
    ``package_patch`` (which preserves every other field).

    Recovery is best-effort: a title is only restored when the XML holds a real
    human title (different from the slug); the abstract is restored into
    ``notes_translated.en`` when the dataset's notes are empty. Always preview
    with --dry-run first.
    """
    import os

    user = tk.get_action('get_site_user')({'ignore_auth': True}, {})
    ctx = {'user': user['name'], 'ignore_auth': True, 'use_cache': False}
    package_show = tk.get_action('package_show')
    package_patch = tk.get_action('package_patch')

    # Build the recovery index from the ckan2pycsw XML directory, keyed by
    # every dataset id/slug token embedded in the record.
    recovery = {}
    if metadata_dir:
        if not os.path.isdir(metadata_dir):
            raise click.ClickException(f"--metadata-dir not found: {metadata_dir}")
        files = [os.path.join(metadata_dir, f) for f in os.listdir(metadata_dir)
                 if f.lower().endswith('.xml')]
        for path in files:
            keys, title, abstract = _parse_pycsw_xml(path)
            for key in keys:
                recovery.setdefault(key, (title, abstract))
        click.echo(f"Loaded {len(files)} XML record(s) -> {len(recovery)} dataset key(s).")

    from ckan import model

    def _iter_names():
        if datasets:
            for ident in datasets:
                yield ident
            return
        q = (model.Session.query(model.Package.name)
             .filter(model.Package.state == 'active')
             .filter(model.Package.type == 'dataset'))
        for (name,) in q.yield_per(500):
            yield name

    clobbered = 0
    recovered = 0
    for name in _iter_names():
        try:
            pkg = package_show(dict(ctx), {'id': name})
        except Exception:
            continue
        if not _title_is_clobbered(pkg):
            continue
        if limit is not None and clobbered >= limit:
            break
        clobbered += 1

        src = recovery.get(pkg.get('id')) or recovery.get(pkg.get('name'))
        new_title = ''
        new_notes = ''
        if src:
            cand_title, cand_abstract = src
            # Only restore a title that is a real one (not the slug again).
            if cand_title and _slug_norm(cand_title) != _slug_norm(pkg.get('name')):
                new_title = cand_title
            # Restore abstract only when current notes are empty.
            if cand_abstract and not _fluent_en(pkg.get('notes_translated')) and not (pkg.get('notes') or '').strip():
                new_notes = cand_abstract

        status = []
        if new_title:
            status.append(f"title='{new_title}'")
        if new_notes:
            status.append(f"notes(+{len(new_notes)} chars)")
        if not status:
            status.append('no recovery source' if metadata_dir else 'clobbered')
        click.echo(f"[clobbered] {pkg.get('name')} :: {'; '.join(status)}")

        if not apply or not (new_title or new_notes):
            continue

        patch = {'id': pkg['id']}
        if new_title:
            tt = pkg.get('title_translated')
            tt = dict(tt) if isinstance(tt, dict) else {}
            tt['en'] = new_title
            patch['title_translated'] = tt
        if new_notes:
            nt = pkg.get('notes_translated')
            nt = dict(nt) if isinstance(nt, dict) else {}
            nt['en'] = new_notes
            patch['notes_translated'] = nt
        try:
            package_patch(dict(ctx), patch)
            recovered += 1
        except Exception as err:
            click.echo(f"  ! could not patch '{pkg.get('name')}': {err}", err=True)

    click.echo("")
    click.echo("Done.")
    click.echo(f"  Clobbered titles found: {clobbered}")
    if apply:
        click.echo(f"  Recovered (patched):    {recovered}")
    else:
        click.echo("  (dry-run, no changes applied; pass --apply with --metadata-dir to recover)")
