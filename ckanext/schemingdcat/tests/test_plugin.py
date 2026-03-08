from types import SimpleNamespace

import ckan.model as model
import ckan.plugins.toolkit as toolkit

import ckanext.schemingdcat.helpers as helpers
import ckanext.schemingdcat.plugin as plugin


def test_stage_requested_group_memberships_preserves_current_groups(monkeypatch):
    subject = plugin.SchemingDCATDatasetsPlugin()
    context = {}
    data_dict = {'groups': [{'name': 'argentina'}]}

    monkeypatch.setattr(
        subject,
        '_read_package_for_dataset_update',
        lambda ctx, payload: {
            'id': 'pkg-1',
            'groups': [{'name': 'argentina'}, {'name': 'climwar'}],
        },
    )
    monkeypatch.setattr(subject, '_get_raw_group_identifiers_from_request', lambda: ['chile', 'climwar'])
    monkeypatch.setattr(subject, '_resolve_group_names', lambda values: list(values))
    monkeypatch.setattr(subject, '_resolve_spatial_memberstate_groups', lambda ctx, payload: [])

    subject._stage_requested_group_memberships(context, data_dict)

    assert context['_schemingdcat_requested_group_memberships'] == {
        'requested_group_names': ['chile', 'climwar'],
        'current_group_names': ['argentina', 'climwar'],
        'package_id': 'pkg-1',
    }
    assert data_dict['groups'] == [{'name': 'argentina'}, {'name': 'climwar'}]


def test_stage_requested_group_memberships_preserves_initiatives_for_spatial_patch(monkeypatch):
    subject = plugin.SchemingDCATDatasetsPlugin()
    context = {
        '_schemingdcat_package_patch_payload_keys': {'id', 'spatial_uri'},
    }
    data_dict = {
        'groups': [{'name': 'chile'}, {'name': 'climwar'}],
        'spatial_uri': '["http://publications.europa.eu/resource/authority/country/CHL"]',
    }

    monkeypatch.setattr(
        subject,
        '_read_package_for_dataset_update',
        lambda ctx, payload: {
            'id': 'pkg-1',
            'groups': [{'name': 'chile'}, {'name': 'climwar'}],
        },
    )
    monkeypatch.setattr(subject, '_get_raw_group_identifiers_from_request', lambda: [])
    monkeypatch.setattr(subject, '_resolve_group_names', lambda values: list(values))
    monkeypatch.setattr(subject, '_resolve_spatial_memberstate_groups', lambda ctx, payload: ['chile'])
    monkeypatch.setattr(subject, '_managed_form_group_names', lambda: {'chile', 'climwar'})
    monkeypatch.setattr(subject, '_initiative_group_names', lambda: {'climwar'})

    subject._stage_requested_group_memberships(context, data_dict)

    assert context['_schemingdcat_requested_group_memberships'] == {
        'requested_group_names': ['climwar', 'chile'],
        'current_group_names': ['chile', 'climwar'],
        'package_id': 'pkg-1',
    }
    assert data_dict['groups'] == [{'name': 'chile'}, {'name': 'climwar'}]


def test_extract_group_identifiers_prefers_explicit_fields_over_existing_groups(monkeypatch):
    subject = plugin.SchemingDCATDatasetsPlugin()

    monkeypatch.setattr(subject, '_get_raw_group_identifiers_from_request', lambda: [])

    identifiers = subject._extract_group_identifiers(
        {
            'groups': [{'name': 'argentina'}, {'name': 'climwar'}],
            'groups__0__id': 'chile',
            'groups__1__id': 'climwar',
        }
    )

    assert identifiers == ['chile', 'climwar']


def test_extract_group_identifiers_can_ignore_groups_list(monkeypatch):
    subject = plugin.SchemingDCATDatasetsPlugin()

    monkeypatch.setattr(subject, '_get_raw_group_identifiers_from_request', lambda: [])

    identifiers = subject._extract_group_identifiers(
        {'groups': [{'name': 'argentina'}, {'name': 'climwar'}]},
        include_groups_list=False,
    )

    assert identifiers == []


def test_apply_requested_group_memberships_replaces_managed_groups(monkeypatch):
    subject = plugin.SchemingDCATDatasetsPlugin()
    context = {
        '_schemingdcat_requested_group_memberships': {
            'requested_group_names': ['chile', 'climwar'],
            'package_id': 'pkg-1',
        }
    }
    created = []
    deleted = []

    monkeypatch.setattr(subject, '_managed_form_group_names', lambda: {'argentina', 'chile', 'climwar'})

    groups = {
        'argentina': SimpleNamespace(id='group-argentina', name='argentina'),
        'chile': SimpleNamespace(id='group-chile', name='chile'),
        'climwar': SimpleNamespace(id='group-climwar', name='climwar'),
    }
    monkeypatch.setattr(model.Group, 'get', lambda identifier: groups.get(identifier))

    def fake_get_action(name):
        if name == 'package_show':
            return lambda ctx, payload: {
                'id': 'pkg-1',
                'groups': [{'name': 'argentina'}, {'name': 'climwar'}],
            }
        if name == 'get_site_user':
            return lambda ctx, payload: {'name': 'site-user'}
        if name == 'member_delete':
            return lambda ctx, payload: deleted.append(payload)
        if name == 'member_create':
            return lambda ctx, payload: created.append(payload)
        raise AssertionError('Unexpected action {}'.format(name))

    monkeypatch.setattr(toolkit, 'get_action', fake_get_action)

    subject._apply_requested_group_memberships(context, {'id': 'pkg-1'})

    assert deleted == [
        {
            'id': 'group-argentina',
            'object': 'pkg-1',
            'object_type': 'package',
        }
    ]
    assert created == [
        {
            'id': 'group-chile',
            'object': 'pkg-1',
            'object_type': 'package',
            'capacity': 'public',
        }
    ]


def test_package_update_backfills_missing_fields_and_retries(monkeypatch):
    subject = plugin.SchemingDCATDatasetsPlugin()
    calls = {'next_action': 0, 'backfill': None, 'apply': 0}

    monkeypatch.setattr(subject, '_stage_requested_group_memberships', lambda ctx, payload: None)
    monkeypatch.setattr(
        subject,
        '_apply_requested_group_memberships',
        lambda ctx, payload: calls.__setitem__('apply', calls['apply'] + 1),
    )

    def fake_backfill(ctx, payload, missing_fields):
        calls['backfill'] = missing_fields
        return True

    monkeypatch.setattr(subject, '_backfill_missing_dataset_fields_for_package_update', fake_backfill)

    def next_action(ctx, payload):
        calls['next_action'] += 1
        if calls['next_action'] == 1:
            raise toolkit.ValidationError(
                {
                    'identifier': ['Missing value'],
                    'language': ['Missing value'],
                }
            )
        return {'id': 'pkg-1'}

    result = subject.package_update(next_action, {}, {'id': 'pkg-1'})

    assert result == {'id': 'pkg-1'}
    assert calls['next_action'] == 2
    assert calls['backfill'] == {'identifier', 'language'}
    assert calls['apply'] == 1


def test_fluent_form_value_falls_back_to_legacy_core_field(monkeypatch):
    monkeypatch.setattr(helpers, 'schemingdcat_get_default_lang', lambda: 'en')

    translated_value = helpers.schemingdcat_fluent_form_value(
        data={'title_translated': {'en': 'Current title'}},
        field={'field_name': 'title_translated', 'required_language': 'en'},
        lang='en',
        schema={'required_language': 'en'},
    )

    assert translated_value == 'Current title'

    value = helpers.schemingdcat_fluent_form_value(
        data={'title': 'Legacy title'},
        field={'field_name': 'title_translated', 'required_language': 'en'},
        lang='en',
        schema={'required_language': 'en'},
    )

    assert value == 'Legacy title'

    secondary_lang_value = helpers.schemingdcat_fluent_form_value(
        data={'title': 'Legacy title'},
        field={'field_name': 'title_translated', 'required_language': 'en'},
        lang='es',
        schema={'required_language': 'en'},
    )

    assert secondary_lang_value == ''
