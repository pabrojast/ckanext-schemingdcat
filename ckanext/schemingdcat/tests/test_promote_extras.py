"""Tests for the metadata-wipe guard: promoting scheming schema fields that
arrive only inside the raw ``extras`` list back to the top level so the
package_update round-trip preserves them instead of wiping them.

See ``SchemingDCATDatasetsPlugin._promote_extras_schema_fields`` in plugin.py.
"""

import ckanext.schemingdcat.plugin as plugin


SCHEMA_FIELDS = {
    'title_translated', 'notes_translated', 'dcat_type',
    'language', 'topic', 'identifier', 'contact_email',
}


def _subject(monkeypatch):
    subject = plugin.SchemingDCATDatasetsPlugin()
    monkeypatch.setattr(
        subject, '_dataset_schema_field_names', lambda data_dict: set(SCHEMA_FIELDS)
    )
    return subject


def test_promote_restores_unpromoted_scheming_fields(monkeypatch):
    subject = _subject(monkeypatch)
    data_dict = {
        'id': 'pkg-1',
        'name': 'potential-iot-ghana',
        'type': 'dataset',
        'title': 'potential-iot-ghana',
        'extras': [
            {'key': 'title_translated', 'value': '{"en": "Potential IoT Ghana"}'},
            {'key': 'dcat_type', 'value': 'http://example/dataset'},
            {'key': 'topic', 'value': 'http://example/environment'},
            {'key': 'groups__0__id', 'value': 'ghana'},
            {'key': 'groups__1__id', 'value': 'mali'},
            {'key': 'spatial', 'value': '{"type": "Point"}'},  # non-schema extra kept
        ],
    }

    subject._promote_extras_schema_fields({}, data_dict)

    # Fluent value parsed to a dict and promoted to the top level.
    assert data_dict['title_translated'] == {'en': 'Potential IoT Ghana'}
    assert data_dict['dcat_type'] == 'http://example/dataset'
    assert data_dict['topic'] == 'http://example/environment'

    extra_keys = {e['key'] for e in data_dict['extras']}
    # Promoted schema fields removed from extras.
    assert 'title_translated' not in extra_keys
    assert 'dcat_type' not in extra_keys
    assert 'topic' not in extra_keys
    # Leaked group multiselect form artifacts dropped.
    assert 'groups__0__id' not in extra_keys
    assert 'groups__1__id' not in extra_keys
    # Genuine non-schema extras preserved.
    assert 'spatial' in extra_keys


def test_promote_does_not_override_top_level_values(monkeypatch):
    subject = _subject(monkeypatch)
    data_dict = {
        'id': 'pkg-1',
        'name': 'd',
        'dcat_type': '',  # present but empty (legitimate clear) -> must be kept
        'title_translated': {'en': 'Real Title'},  # present -> must be kept
        'extras': [
            {'key': 'dcat_type', 'value': 'http://example/dataset'},
            {'key': 'title_translated', 'value': '{"en": "Stale"}'},
        ],
    }

    subject._promote_extras_schema_fields({}, data_dict)

    # Only keys ABSENT at top-level are promoted; present ones are untouched.
    assert data_dict['dcat_type'] == ''
    assert data_dict['title_translated'] == {'en': 'Real Title'}
    extra_keys = {e['key'] for e in data_dict['extras']}
    assert 'dcat_type' in extra_keys
    assert 'title_translated' in extra_keys


def test_promote_skips_internal_backfill_patch(monkeypatch):
    subject = _subject(monkeypatch)
    data_dict = {
        'id': 'pkg-1', 'name': 'd',
        'extras': [{'key': 'dcat_type', 'value': 'x'}],
    }
    subject._promote_extras_schema_fields(
        {'_schemingdcat_internal_backfill_patch': True}, data_dict
    )
    assert 'dcat_type' not in data_dict  # untouched
    assert data_dict['extras'] == [{'key': 'dcat_type', 'value': 'x'}]


def test_promote_noop_without_extras_list(monkeypatch):
    subject = _subject(monkeypatch)
    data_dict = {'id': 'pkg-1', 'name': 'd'}
    subject._promote_extras_schema_fields({}, data_dict)
    assert 'extras' not in data_dict


# ── after_dataset_show: heal unpromoted Solr-cache dicts on read ──────────


def test_after_show_promotes_stranded_schema_fields(monkeypatch):
    subject = _subject(monkeypatch)
    data_dict = {
        'id': 'pkg-1',
        'name': 'potential-iot-ghana',
        'type': 'dataset',
        'title': 'potential-iot-ghana',
        'extras': [
            {'key': 'title_translated', 'value': '{"en": "Potential IoT Ghana"}'},
            {'key': 'dcat_type', 'value': 'http://example/dataset'},
            {'key': 'spatial', 'value': '{"type": "Point"}'},  # non-schema extra
        ],
    }

    result = subject.after_dataset_show({}, data_dict)

    assert result is data_dict
    # Stranded schema fields promoted (fluent JSON parsed).
    assert data_dict['title_translated'] == {'en': 'Potential IoT Ghana'}
    assert data_dict['dcat_type'] == 'http://example/dataset'
    # Non-schema extras are not promoted and extras stay intact for readers.
    assert 'spatial' not in data_dict or data_dict.get('spatial') != {'type': 'Point'}
    assert {e['key'] for e in data_dict['extras']} == {
        'title_translated', 'dcat_type', 'spatial'
    }


def test_after_show_keeps_existing_top_level_values(monkeypatch):
    subject = _subject(monkeypatch)
    data_dict = {
        'id': 'pkg-1',
        'name': 'd',
        'title_translated': {'en': 'Real Title'},
        'extras': [
            {'key': 'title_translated', 'value': '{"en": "Stale"}'},
        ],
    }

    subject.after_dataset_show({}, data_dict)

    assert data_dict['title_translated'] == {'en': 'Real Title'}


def test_after_show_never_raises(monkeypatch):
    subject = plugin.SchemingDCATDatasetsPlugin()

    def _boom(data_dict):
        raise RuntimeError('schema lookup exploded')

    monkeypatch.setattr(subject, '_dataset_schema_field_names', _boom)
    data_dict = {
        'id': 'pkg-1', 'name': 'd',
        'extras': [{'key': 'dcat_type', 'value': 'x'}],
    }

    result = subject.after_dataset_show({}, data_dict)

    assert result is data_dict
    assert 'dcat_type' not in data_dict
