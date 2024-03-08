# -*- coding: utf-8 -*-
# Always prefer setuptools over distutils
from setuptools import setup, find_packages
from codecs import open  # To use a consistent encoding
from os import path

here = path.abspath(path.dirname(__file__))

version = "1.2.1"

# Get the long description from the relevant file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='''ckanext-scheming_dcat''',
    version=version,
    description='''Custom CKAN schemas for DCAT vocabularies''',
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='ckan',
    author="mjanez",
    url='https://github.com/mjanez/ckanext-scheming_dcat',
    license='AGPL',   
    packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
    namespace_packages=['ckanext'],
    include_package_data=True,
    entry_points='''
        [ckan.plugins]
        scheming_dcat=ckanext.scheming_dcat.plugin:FacetSchemingDCATPlugin
        scheming_dcat_datasets=ckanext.scheming_dcat.plugin:SchemingDCATDatasetsPlugin
        scheming_dcat_groups=ckanext.scheming_dcat.plugin:SchemingDCATGroupsPlugin
        scheming_dcat_organizations=ckanext.scheming_dcat.plugin:SchemingDCATOrganizationsPlugin
        
        # Harvesters
        scheming_dcat_ckan_harvester=ckanext.scheming_dcat.harvesters:SchemingDCATCKANHarvester
        scheming_dcat_xls_harvester=ckanext.scheming_dcat.harvesters:SchemingDCATXLSHarvester

        [babel.extractors]
        ckan = ckan.lib.extract:extract_ckan
    ''',
    message_extractors={
        'ckanext': [
            ('**.py', 'python', None),
            ('**.js', 'javascript', None),
            ('**/templates/**.html', 'ckan', None),
        ],
    }
)
