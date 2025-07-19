# -*- coding: utf-8 -*-
# Always prefer setuptools over distutils
from setuptools import setup, find_packages
from codecs import open  # To use a consistent encoding
from os import path

here = path.abspath(path.dirname(__file__))

version = "3.1.0"

# Get the long description from the relevant file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='''ckanext-schemingdcat''',
    version=version,
    description='''Custom CKAN schemas for DCAT vocabularies''',
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='ckan',
    author="mjanez",
    url='https://github.com/mjanez/ckanext-schemingdcat',
    license='AGPL',   
    packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
    namespace_packages=['ckanext'],
    include_package_data=True,
    install_requires=[
        # Core dependencies
        'gspread>=6.1.2',
        'msal>=1.29.0',
        'Office365-REST-Python-Client>=2.5.5',
        'openpyxl>=3.1.2',
        'pandas',
        'azure-storage-blob>=12.14.0',
    ],
    extras_require={
        'spatial': [
            # Spatial dependencies for extent extraction
            'fiona>=1.8.0',
            'rasterio>=1.3.0',
            'pyproj>=3.2.0',
            'GDAL>=3.0.0',
        ],
        'dev': [
            'pytest-ckan',
        ],
    },
    entry_points='''
        [ckan.plugins]
        schemingdcat=ckanext.schemingdcat.plugin:SchemingDCATPlugin
        schemingdcat_datasets=ckanext.schemingdcat.plugin:SchemingDCATDatasetsPlugin
        schemingdcat_groups=ckanext.schemingdcat.plugin:SchemingDCATGroupsPlugin
        schemingdcat_organizations=ckanext.schemingdcat.plugin:SchemingDCATOrganizationsPlugin
        
        # Harvesters
        schemingdcat_ckan_harvester=ckanext.schemingdcat.harvesters:SchemingDCATCKANHarvester
        schemingdcat_xls_harvester=ckanext.schemingdcat.harvesters:SchemingDCATXLSHarvester
        schemingdcat_ows_harvester=ckanext.schemingdcat.harvesters:SchemingDCATOWSHarvester

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
