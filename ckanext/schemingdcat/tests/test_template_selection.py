"""A dataset type may name its own page templates in its scheming schema.

Types whose schema does not name them must keep the templates they had before.
"""

import os

import jinja2
import pytest

import ckan.views.dataset as dataset_views
from ckan.lib.plugins import DefaultDatasetForm

import ckanext.schemingdcat.helpers as helpers
from ckanext.schemingdcat.plugin import SchemingDCATDatasetsPlugin

# What every dataset type got before per-type templates existed.
DEFAULTS = {
    'read_template': 'schemingdcat/package/read.html',
    'search_template': 'package/search.html',
    'new_template': 'package/new.html',
    'edit_template': 'package/edit.html',
    'package_form': 'schemingdcat/package/snippets/package_form.html',
}
# The keys ckanext-learning declares in its schema.json.
LEARNING = {
    'read_template': 'learning/read.html',
    'search_template': 'learning/search.html',
    'new_template': 'learning/new.html',
    'edit_template': 'learning/edit.html',
    'package_form': 'learning/form.html',
}
METHODS = sorted(DEFAULTS)


@pytest.fixture
def subject(monkeypatch):
    plugin = SchemingDCATDatasetsPlugin()
    monkeypatch.setattr(plugin, '_schemas', {
        'dataset': {'dataset_type': 'dataset', 'dataset_fields': []},
        'documents': {'dataset_type': 'documents', 'dataset_fields': []},
        'learning': dict(LEARNING, dataset_type='learning', dataset_fields=[]),
    })
    return plugin


@pytest.mark.parametrize('method', METHODS)
def test_type_that_declares_templates_gets_them(subject, method):
    assert getattr(subject, method)('learning') == LEARNING[method]


@pytest.mark.parametrize('package_type', ['dataset', 'documents', 'not-loaded', None])
@pytest.mark.parametrize('method', METHODS)
def test_type_without_template_keys_keeps_the_defaults(subject, method, package_type):
    assert getattr(subject, method)(package_type) == DEFAULTS[method]


@pytest.mark.parametrize('method', METHODS)
def test_callers_that_pass_no_type_keep_the_defaults(subject, method):
    # The theme's /dataset/<id> view calls read_template() with no arguments.
    assert getattr(subject, method)() == DEFAULTS[method]


@pytest.mark.parametrize('method', ['search_template', 'new_template', 'edit_template'])
def test_defaults_are_the_ones_ckan_core_used(method):
    # These three were inherited from CKAN before the plugin defined them.
    assert DEFAULTS[method] == getattr(DefaultDatasetForm(), method)()


@pytest.mark.parametrize('method', METHODS)
def test_ckan_hands_the_package_type_to_the_plugin(subject, monkeypatch, method):
    monkeypatch.setattr(dataset_views, 'lookup_package_plugin', lambda package_type=None: subject)

    assert dataset_views._get_pkg_template(method, 'learning') == LEARNING[method]
    assert dataset_views._get_pkg_template(method, 'documents') == DEFAULTS[method]


def test_schema_overrides_only_the_keys_it_declares(subject, monkeypatch):
    monkeypatch.setitem(subject._schemas, 'partial', {
        'dataset_type': 'partial', 'read_template': 'partial/read.html', 'search_template': '',
    })

    assert subject.read_template('partial') == 'partial/read.html'
    for method in METHODS:
        if method != 'read_template':
            assert getattr(subject, method)('partial') == DEFAULTS[method]


@pytest.mark.parametrize('method', METHODS)
def test_plugin_without_loaded_schemas_keeps_the_defaults(monkeypatch, method):
    plugin = SchemingDCATDatasetsPlugin()
    # ckanext-scheming's value until update_config() loads the schemas.
    monkeypatch.setattr(plugin, '_schemas', tuple())

    assert getattr(plugin, method)('learning') == DEFAULTS[method]


def test_resource_templates_do_not_depend_on_the_type(subject):
    assert subject.resource_template() == 'schemingdcat/package/resource_read.html'
    assert subject.resource_form() == 'schemingdcat/package/snippets/resource_form.html'


def test_learning_type_has_its_own_label(monkeypatch):
    monkeypatch.setattr(helpers.p.toolkit, '_', lambda text: text)

    assert helpers.schemingdcat_dataset_type_label('learning') == 'Learning resource'
    assert helpers.schemingdcat_dataset_type_label('learning', plural=True) == 'Learning resources'
    assert helpers.schemingdcat_dataset_type_label('documents', plural=True) == 'Documents'


@pytest.mark.parametrize('context, expected, absent', [
    ({'dataset_type': 'learning'}, 'Learning materials', 'Upload Form'),
    ({'pkg': {'type': 'learning'}}, 'Learning materials', 'Upload Form'),
    ({'dataset_type': 'documents'}, 'Document Upload Form', 'Learning materials'),
    ({'dataset_type': 'dataset'}, 'Data Upload Form', 'Learning materials'),
    ({}, 'Data Upload Form', 'Learning materials'),
])
def test_resource_help_text_per_type(context, expected, absent):
    templates = os.path.join(os.path.dirname(helpers.__file__), 'templates')
    environment = jinja2.Environment(loader=jinja2.FileSystemLoader(templates), autoescape=True)
    environment.globals['_'] = lambda text: text

    html = environment.get_template('package/snippets/resource_help.html').render(**context)

    assert expected in html
    assert absent not in html
