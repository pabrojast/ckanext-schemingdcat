"""Author edits must survive the paginated form's package_patch merge."""

import pytest
from ckanext.scheming.plugins import expand_form_composite
from ckanext.schemingdcat.plugin import SchemingDCATDatasetsPlugin


@pytest.mark.parametrize('field', ['authors', 'authors_json'])
def test_form_rows_replace_stored_authors_before_patch_merge(field):
    previous = {
        'id': 'test-package',
        'publisher_name': 'Publisher unchanged',
        field: [{'name': 'Old author'}, {'name': 'Removed author'}],
    }

    def core_patch(context, payload):
        merged = dict(previous, **payload)
        # Scheming validation skips flat rows when a list is already present.
        expand_form_composite(merged, {field})
        assert field in context['_schemingdcat_package_patch_payload_keys']
        return merged

    context = {}
    result = SchemingDCATDatasetsPlugin().package_patch(core_patch, context, {
        'id': 'test-package',
        field + '-0-name': 'Edited author',
        field + '-0-orcid': '0000-0002-1825-0097',
        field + '-2-name': 'Added author',
    })
    assert result[field] == [
        {'name': 'Edited author', 'orcid': '0000-0002-1825-0097'},
        {'name': 'Added author'},
    ]
    assert result['publisher_name'] == 'Publisher unchanged'
    assert '_schemingdcat_package_patch_payload_keys' not in context


@pytest.mark.parametrize('authors', [[], [{'name': 'API author'}]])
def test_explicit_api_author_list_is_preserved(authors):
    payload = {'id': 'test-package', 'authors': authors}
    result = SchemingDCATDatasetsPlugin().package_patch(lambda ctx, data: data, {}, payload)
    assert result == {'id': 'test-package', 'authors': authors}


def test_unrelated_patch_does_not_replace_authors():
    payload = {'id': 'test-package', 'publisher_name': 'Edited publisher'}
    result = SchemingDCATDatasetsPlugin().package_patch(lambda ctx, data: data, {}, payload)
    assert result == {'id': 'test-package', 'publisher_name': 'Edited publisher'}
    assert 'authors' not in result and 'authors_json' not in result


def test_form_authors_leave_unrelated_tuple_keys_unchanged():
    payload = {'id': 'test-package', ('groups', 0, 'name'): 'test-group',
               'authors-0-name': 'Edited author'}
    result = SchemingDCATDatasetsPlugin().package_patch(lambda ctx, data: data, {}, payload)
    assert result['authors'] == [{'name': 'Edited author'}]
    assert result[('groups', 0, 'name')] == 'test-group'
