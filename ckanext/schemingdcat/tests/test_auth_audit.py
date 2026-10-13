"""Nested reads of not-yet-created datasets must not poison CKAN auth audits."""

import pytest

import ckan.logic as logic
import ckan.plugins.toolkit as toolkit
from ckanext.schemingdcat.plugin import (
    SchemingDCATDatasetsPlugin,
    _fresh_context,
)


@pytest.mark.parametrize('error', [toolkit.ObjectNotFound, toolkit.NotAuthorized])
def test_failed_nested_dataset_read_preserves_parent_auth_audit(monkeypatch, error):
    parent_audit = [('package_create', 123)]
    context = {'user': 'dataset-editor', '__auth_audit': parent_audit}

    def failed_read(nested, payload):
        assert nested['user'] == context['user']
        nested.setdefault('__auth_audit', []).append(('package_show', 456))
        raise error()

    monkeypatch.setattr(toolkit, 'get_action', lambda name: failed_read)
    result = SchemingDCATDatasetsPlugin()._read_package_for_dataset_update(
        context, {'name': 'not-created-yet'},
    )

    assert result is None
    assert context['__auth_audit'] is parent_audit
    assert parent_audit == [('package_create', 123)]
    assert 'ignore_auth' not in context


@pytest.mark.parametrize('ignore_auth', [False, True])
def test_fresh_context_preserves_permissions_and_transaction(ignore_auth):
    session = object()
    context = {
        'user': 'dataset-editor', 'ignore_auth': ignore_auth,
        'session': session, 'defer_commit': True,
        '__auth_audit': [('package_create', 123)],
    }

    nested = _fresh_context(context)

    assert nested == {key: value for key, value in context.items()
                      if key != '__auth_audit'}
    assert nested['session'] is session
    assert context['__auth_audit'] == [('package_create', 123)]


@pytest.mark.usefixtures('with_plugins', 'clean_db')
@pytest.mark.ckan_config('ckan.plugins', '')
def test_real_ckan_audit_survives_not_found_before_successful_read():
    """Exercise CKAN's real get_action/check_access wrappers and package lookup."""
    import ckan.model as model
    from ckan.tests import factories

    dataset = factories.Dataset()
    context = {
        'model': model, 'session': model.Session, 'ignore_auth': True,
        '__auth_audit': [],
    }
    subject = SchemingDCATDatasetsPlugin()

    assert subject._read_package_for_dataset_update(
        context, {'name': 'auth-audit-missing-dataset'},
    ) is None
    assert logic.get_action('package_show')(
        context, {'id': dataset['id']},
    )['id'] == dataset['id']
    assert context.get('__auth_audit', []) == []
