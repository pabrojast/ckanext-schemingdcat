import typing
import re

# Default values
default_facet_operator = 'OR'
icons_dir = 'images/icons'
default_locale = 'en'
organization_custom_facets = False
group_custom_facets = False
debug = False
linkeddata_links = None
geometadata_links = None
endpoints = None
endpoints_yaml = 'endpoints.yaml'
facet_list_limit = 6
default_package_item_icon = 'theme'
default_package_item_show_spatial = True
show_metadata_templates_toolbar = True
metadata_templates_search_identifier = 'schemingdcat_xls-template'
mimetype_base_uri = 'http://www.iana.org/assignments/media-types'
slugify_pat = re.compile('[^a-zA-Z0-9]')
# schemingdcat field_mapping extras prefix, e.g. custom_field = extras_custom_field
field_mapping_extras_prefix = 'extras'
field_mapping_extras_prefix_symbol = '_'

# Default DCAT metadata configuration
OGC2CKAN_HARVESTER_MD_CONFIG = {
    'access_rights': 'http://inspire.ec.europa.eu/metadata-codelist/LimitationsOnPublicAccess/noLimitations',
    'conformance': [
        'http://inspire.ec.europa.eu/documents/inspire-metadata-regulation','http://inspire.ec.europa.eu/documents/commission-regulation-eu-no-13122014-10-december-2014-amending-regulation-eu-no-10892010-0'
    ],
    'author': 'ckanext-schemingdcat',
    'author_email': 'admin@{ckan_instance}',
    'author_url': '{ckan_instance}/organization/test',
    'author_uri': '{ckan_instance}/organization/test',
    'contact_name': 'ckanext-schemingdcat',
    'contact_email': 'admin@{ckan_instance}',
    'contact_url': '{ckan_instance}/organization/test',
    'contact_uri': '{ckan_instance}/organization/test',
    'dcat_type': {
        'series': 'http://inspire.ec.europa.eu/metadata-codelist/ResourceType/series',
        'dataset': 'http://inspire.ec.europa.eu/metadata-codelist/ResourceType/dataset',
        'spatial_data_service': 'http://inspire.ec.europa.eu/metadata-codelist/ResourceType/service',
        'default': 'http://inspire.ec.europa.eu/metadata-codelist/ResourceType/dataset',
        'collection': 'http://purl.org/dc/dcmitype/Collection',
        'event': 'http://purl.org/dc/dcmitype/Event',
        'image': 'http://purl.org/dc/dcmitype/Image',
        'still_image': 'http://purl.org/dc/dcmitype/StillImage',
        'moving_image': 'http://purl.org/dc/dcmitype/MovingImage',
        'physical_object': 'http://purl.org/dc/dcmitype/PhysicalObject',
        'interactive_resource': 'http://purl.org/dc/dcmitype/InteractiveResource',
        'service': 'http://purl.org/dc/dcmitype/Service',
        'sound': 'http://purl.org/dc/dcmitype/Sound',
        'software': 'http://purl.org/dc/dcmitype/Software',
        'text': 'http://purl.org/dc/dcmitype/Text',
    },
    'encoding': 'UTF-8',
    'frequency' : 'http://publications.europa.eu/resource/authority/frequency/UNKNOWN',
    'inspireid_theme': 'HB',
    'language': 'http://publications.europa.eu/resource/authority/language/ENG',
    'license': 'http://creativecommons.org/licenses/by/4.0/',
    'license_id': 'cc-by',
    'lineage_process_steps': 'ckanext-schemingdcat lineage process steps.',
    'maintainer': 'ckanext-schemingdcat',
    'maintainer_email': 'admin@{ckan_instance}',
    'maintainer_url': '{ckan_instance}/organization/test',
    'maintainer_uri': '{ckan_instance}/organization/test',
    'metadata_profile': [
        "http://semiceu.github.io/GeoDCAT-AP/releases/2.0.0","http://inspire.ec.europa.eu/document-tags/metadata"
    ],
    'provenance': 'ckanext-schemingdcat provenance statement.',
    'publisher_name': 'ckanext-schemingdcat',
    'publisher_email': 'admin@{ckan_instance}',
    'publisher_url': '{ckan_instance}/organization/test',
    'publisher_identifier': '{ckan_instance}/organization/test',
    'publisher_uri': '{ckan_instance}/organization/test',
    'publisher_type': 'http://purl.org/adms/publishertype/NonProfitOrganisation',
    'reference_system': 'http://www.opengis.net/def/crs/EPSG/0/4258',
    'representation_type': {
        'wfs': 'http://inspire.ec.europa.eu/metadata-codelist/SpatialRepresentationType/vector',
        'wcs': 'http://inspire.ec.europa.eu/metadata-codelist/SpatialRepresentationType/grid',
        'default': 'http://inspire.ec.europa.eu/metadata-codelist/SpatialRepresentationType/vector',
        'grid': 'http://inspire.ec.europa.eu/metadata-codelist/SpatialRepresentationType/grid',
        'vector': 'http://inspire.ec.europa.eu/metadata-codelist/SpatialRepresentationType/vector',
        'textTable': 'http://inspire.ec.europa.eu/metadata-codelist/SpatialRepresentationType/textTable',
        'tin': 'http://inspire.ec.europa.eu/metadata-codelist/SpatialRepresentationType/tin',
        'stereoModel': 'http://inspire.ec.europa.eu/metadata-codelist/SpatialRepresentationType/stereoModel',
        'video': 'http://inspire.ec.europa.eu/metadata-codelist/SpatialRepresentationType/video',
    },
    'resources': {
        'availability': 'http://publications.europa.eu/resource/authority/planned-availability/AVAILABLE',
        'name': {
            'es': 'Distribución {format}',
            'en': 'Distribution {format}'
        },
    },
    'rights': 'http://inspire.ec.europa.eu/metadata-codelist/LimitationsOnPublicAccess/noLimitations',
    'spatial': None,
    'spatial_uri': 'http://datos.gob.es/recurso/sector-publico/territorio/Pais/España',
    'status': 'http://purl.org/adms/status/UnderDevelopment',
    'temporal_start': None,
    'temporal_end': None,
    'theme': 'http://inspire.ec.europa.eu/theme/hb',
    'theme_es': 'http://datos.gob.es/kos/sector-publico/sector/medio-ambiente',
    'theme_eu': 'http://publications.europa.eu/resource/authority/data-theme/ENVI',
    'topic': 'http://inspire.ec.europa.eu/metadata-codelist/TopicCategory/biota',
    'valid': None
}

OGC2CKAN_MD_FORMATS = {
    'api': ('API', 'http://www.iana.org/assignments/media-types/application/vnd.api+json', None, 'Application Programming Interface'),
    'api feature': ('OGCFeat', 'http://www.opengis.net/def/interface/ogcapi-features', 'http://www.opengeospatial.org/standards/features', 'OGC API - Features'),
    'wms': ('WMS', 'http://www.opengis.net/def/serviceType/ogc/wms', 'http://www.opengeospatial.org/standards/wms', 'Web Map Service'),
    'zip': ('ZIP', 'http://www.iana.org/assignments/media-types/application/zip', 'http://www.iso.org/standard/60101.html', 'ZIP File'),
    'rar': ('RAR', 'http://www.iana.org/assignments/media-types/application/vnd.rar', 'http://www.rarlab.com/technote.htm', 'RAR File'),
    'wfs': ('WFS', 'http://www.opengis.net/def/serviceType/ogc/wfs', 'http://www.opengeospatial.org/standards/wfs', 'Web Feature Service'),
    'wcs': ('WCS', 'http://www.opengis.net/def/serviceType/ogc/wcs', 'http://www.opengeospatial.org/standards/wcs', 'Web Coverage Service'),
    'tms': ('TMS', 'http://wiki.osgeo.org/wiki/Tile_Map_Service_Specification', 'http://www.opengeospatial.org/standards/tms', 'Tile Map Service'),
    'wmts': ('WMTS', 'http://www.opengis.net/def/serviceType/ogc/wmts', 'http://www.opengeospatial.org/standards/wmts', 'Web Map Tile Service'),
    'kml': ('KML', 'http://www.iana.org/assignments/media-types/application/vnd.google-earth.kml+xml', 'http://www.opengeospatial.org/standards/kml', 'Keyhole Markup Language'),
    'kmz': ('KMZ', 'http://www.iana.org/assignments/media-types/application/vnd.google-earth.kmz+xml', 'http://www.opengeospatial.org/standards/kml', 'Compressed Keyhole Markup Language'),
    'gml': ('GML', 'http://www.iana.org/assignments/media-types/application/gml+xml', 'http://www.opengeospatial.org/standards/gml', 'Geography Markup Language'),
    'geojson': ('GeoJSON', 'http://www.iana.org/assignments/media-types/application/geo+json', 'http://www.rfc-editor.org/rfc/rfc7946', 'GeoJSON'),
    'json': ('JSON', 'http://www.iana.org/assignments/media-types/application/json', 'http://www.ecma-international.org/publications/standards/Ecma-404.htm', 'JavaScript Object Notation'),
    'atom': ('ATOM', 'http://www.iana.org/assignments/media-types/application/atom+xml', 'http://validator.w3.org/feed/docs/atom.html', 'Atom Syndication Format'),
    'xml': ('XML', 'http://www.iana.org/assignments/media-types/application/xml', 'http://www.w3.org/TR/REC-xml/', 'Extensible Markup Language'),
    'arcgis_rest': ('ESRI Rest', None, None, 'ESRI Rest Service'),
    'shp': ('SHP', 'http://www.iana.org/assignments/media-types/application/vnd.shp', 'http://www.esri.com/library/whitepapers/pdfs/shapefile.pdf', 'ESRI Shapefile'),
    'shapefile': ('SHP', 'http://www.iana.org/assignments/media-types/application/vnd.shp', 'http://www.esri.com/library/whitepapers/pdfs/shapefile.pdf', 'ESRI Shapefile'),
    'esri': ('SHP', 'http://www.iana.org/assignments/media-types/application/vnd.shp', 'http://www.esri.com/library/whitepapers/pdfs/shapefile.pdf', 'ESRI Shapefile'),
    'html': ('HTML', 'http://www.iana.org/assignments/media-types/text/html', 'http://www.w3.org/TR/2011/WD-html5-20110405/', 'HyperText Markup Language'),
    'html5': ('HTML', 'http://www.iana.org/assignments/media-types/text/html', 'http://www.w3.org/TR/2011/WD-html5-20110405/', 'HyperText Markup Language'),
    'visor': ('HTML', 'http://www.iana.org/assignments/media-types/text/html', 'http://www.w3.org/TR/2011/WD-html5-20110405/', 'Map Viewer'),
    'enlace': ('HTML', 'http://www.iana.org/assignments/media-types/text/html', 'http://www.w3.org/TR/2011/WD-html5-20110405/', 'Map Viewer'),
    'pdf': ('PDF', 'http://www.iana.org/assignments/media-types/application/pdf', 'http://www.iso.org/standard/75839.html', 'Portable Document Format'),
    'csv': ('CSV', 'http://www.iana.org/assignments/media-types/text/csv', 'http://www.rfc-editor.org/rfc/rfc4180', 'Comma-Separated Values'),
    'netcdf': ('NetCDF', 'http://www.iana.org/assignments/media-types/text/csv', 'http://www.opengeospatial.org/standards/netcdf', 'Network Common Data Form'),
    'csw': ('CSW', 'http://www.opengis.net/def/serviceType/ogc/csw', 'http://www.opengeospatial.org/standards/cat', 'Catalog Service for the Web'),
    'geodcatap': ('RDF', 'http://www.iana.org/assignments/media-types/application/rdf+xml', 'http://semiceu.github.io/GeoDCAT-AP/releases/2.0.0/', 'GeoDCAT-AP 2.0 Metadata')
    ,
    'inspire': ('XML', 'http://www.iana.org/assignments/media-types/application/xml', ['http://inspire.ec.europa.eu/documents/inspire-metadata-regulation','http://inspire.ec.europa.eu/documents/commission-regulation-eu-no-13122014-10-december-2014-amending-regulation-eu-no-10892010-0', 'http://www.isotc211.org/2005/gmd/'], 'INSPIRE ISO 19139 Metadata')
}

OGC2CKAN_ISO_MD_ELEMENTS = {
    'lineage_source': 'gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:source/gmd:LI_Source/gmd:description/gco:CharacterString',
    'lineage_process_steps': 'gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:processStep'
}

# loose definition of BCP47-like strings
BCP_47_LANGUAGE = u'^[a-z]{2,8}(-[0-9a-zA-Z]{1,8})*$'

DATASET_DEFAULT_SCHEMA = [
    'id',
    'type',
    'isopen',
    ]

RESOURCE_DEFAULT_SCHEMA = [
    'url',
    'name',
    ]


DATE_FIELDS = [
    {'field_name': 'created', 'fallback': 'issued', 'default_value': None, 'override': True, 'dtype': str},
    {'field_name': 'issued', 'fallback': None, 'default_value': None, 'override': True, 'dtype': str},
    {'field_name': 'modified', 'fallback': 'issued', 'default_value': None, 'override': True, 'dtype': str},
    {'field_name': 'valid', 'fallback': None, 'default_value': None, 'override': True, 'dtype': str},
    {'field_name': 'temporal_start', 'fallback': None, 'default_value': None, 'override': True, 'dtype': str},
    {'field_name': 'temporal_end', 'fallback': None, 'default_value': None, 'override': True, 'dtype': str}
]

DATASET_DEFAULT_FIELDS = [
    {'field_name': 'id', 'fallback': None, 'default_value': None, 'override': False, 'dtype': str},
    {'field_name': 'name', 'fallback': None, 'default_value': None, 'override': False, 'dtype': str},
    {'field_name': 'title', 'fallback': None, 'default_value': None, 'override': False, 'dtype': str},
    {'field_name': 'notes', 'fallback': None, 'default_value': None, 'override': False, 'dtype': str},
    {'field_name': 'description', 'fallback': None, 'default_value': None, 'override': False, 'dtype': str},
    {'field_name': 'access_rights', 'fallback': None, 'default_value': OGC2CKAN_HARVESTER_MD_CONFIG['access_rights'], 'override': True, 'dtype': str},
    {'field_name': 'license', 'fallback': None, 'default_value': OGC2CKAN_HARVESTER_MD_CONFIG['license'], 'override': True, 'dtype': str},
    {'field_name': 'license_id', 'fallback': None, 'default_value': OGC2CKAN_HARVESTER_MD_CONFIG['license_id'], 'override': True, 'dtype': str},
    {'field_name': 'topic', 'fallback': None, 'default_value': OGC2CKAN_HARVESTER_MD_CONFIG['topic'], 'override': True, 'dtype': str},
    {'field_name': 'theme', 'fallback': None, 'default_value': OGC2CKAN_HARVESTER_MD_CONFIG['theme'], 'override': True, 'dtype': str},
    {'field_name': 'theme_eu', 'fallback': None, 'default_value': OGC2CKAN_HARVESTER_MD_CONFIG['theme_eu'], 'override': True, 'dtype': str},
    {'field_name': 'status', 'fallback': None, 'default_value': OGC2CKAN_HARVESTER_MD_CONFIG['status'], 'override': True, 'dtype': str},
    {'field_name': 'hvd_category', 'fallback': None, 'default_value': None, 'override': False, 'dtype': str},
]

RESOURCE_DEFAULT_FIELDS = [
    {'field_name': 'url', 'fallback': None, 'default_value': "", 'override': False, 'dtype': str},
    {'field_name': 'name', 'fallback': None, 'default_value': None, 'override': False, 'dtype': str},
    {'field_name': 'format', 'fallback': None, 'default_value': None, 'override': False, 'dtype': str},
    {'field_name': 'protocol', 'fallback': None, 'default_value': None, 'override': False, 'dtype': str},
    {'field_name': 'mimetype', 'fallback': None, 'default_value': None, 'override': False, 'dtype': str},
    {'field_name': 'description', 'fallback': None, 'default_value': None, 'override': False, 'dtype': str},
    {'field_name': 'license', 'fallback': None, 'default_value': OGC2CKAN_HARVESTER_MD_CONFIG['license'], 'override': True, 'dtype': str},
    {'field_name': 'license_id', 'fallback': None, 'default_value': OGC2CKAN_HARVESTER_MD_CONFIG['license_id'], 'override': True, 'dtype': str},
    {'field_name': 'rights', 'fallback': None, 'default_value': OGC2CKAN_HARVESTER_MD_CONFIG['rights'], 'override': True, 'dtype': str},
    {'field_name': 'language', 'fallback': None, 'default_value': OGC2CKAN_HARVESTER_MD_CONFIG['language'], 'override': False, 'dtype': str},
    {'field_name': 'conforms_to', 'fallback': None, 'default_value': None, 'override': False, 'dtype': str},
    {'field_name': 'size', 'fallback': None, 'default_value': 0, 'override': True, 'dtype': int},
]

# Custom rules for harvesters.base._update_custom_format()
CUSTOM_FORMAT_RULES = [
    {
        'format_strings': ['esri', 'arcgis'],
        'url_string': 'viewer.html?url=',
        'format': 'HTML',
        'mimetype': 'https://www.iana.org/assignments/media-types/text/html'
    },
    {
        'format_strings': ['html', 'html5'],
        'url_string': None,
        'format': 'HTML',
        'mimetype': 'https://www.iana.org/assignments/media-types/text/html'
    },
    {
        'format_strings': None,
        'url_string': 'getrecordbyid',
        'format': 'XML',
        'mimetype': 'https://www.iana.org/assignments/media-types/application/xml'
    }
    # Add more rules here as needed
]

DATADICTIONARY_DEFAULT_SCHEMA = [
    'id',
    'type',
    'label',
    'notes',
    'type_override'
    ]

# Common date formats for parsing. https://docs.python.org/es/3/library/datetime.html#strftime-and-strptime-format-codes
COMMON_DATE_FORMATS = [
    '%Y-%m-%d',
    '%d-%m-%Y',
    '%m-%d-%Y',
    '%Y/%m/%d',
    '%d/%m/%Y',
    '%m/%d/%Y',
    '%Y-%m-%d %H:%M:%S',  # Date with time
    '%d-%m-%Y %H:%M:%S',  # Date with time
    '%m-%d-%Y %H:%M:%S',  # Date with time
    '%Y/%m/%d %H:%M:%S',  # Date with time
    '%d/%m/%Y %H:%M:%S',  # Date with time
    '%m/%d/%Y %H:%M:%S',  # Date with time
    '%Y-%m-%dT%H:%M:%S',  # ISO 8601 format
    '%Y-%m-%dT%H:%M:%SZ',  # ISO 8601 format with Zulu time indicator
]
# Vocabs
SCHEMINGDCAT_DEFAULT_DATASET_SCHEMA_NAME: typing.Final[str] = "dataset"
SCHEMINGDCAT_INSPIRE_THEMES_VOCAB: typing.Final[str] = "theme"
SCHEMINGDCAT_DCAT_THEMES_VOCAB: typing.Final[list] = ["theme_es", "theme_eu"]
SCHEMINGDCAT_ISO19115_TOPICS_VOCAB: typing.Final[list] = "topic"


# Clean ckan names
URL_REGEX = re.compile(
    r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
)

# Compile the regular expression
INVALID_CHARS = re.compile(r"[^a-zñ0-9_.-]")

# Define a dictionary to map accented characters to their unaccented equivalents except ñ
ACCENT_MAP = str.maketrans({
    "á": "a", "à": "a", "ä": "a", "â": "a", "ã": "a",
    "é": "e", "è": "e", "ë": "e", "ê": "e",
    "í": "i", "ì": "i", "ï": "i", "î": "i",
    "ó": "o", "ò": "o", "ö": "o", "ô": "o", "õ": "o",
    "ú": "u", "ù": "u", "ü": "u", "û": "u",
    "ñ": "ñ",
})

# CKAN tags fields to be searched in the harvester
AUX_TAG_FIELDS = [
    'tag_string',
    'keywords'
]

URL_FIELD_NAMES = {
        'dataset': 
            ['dcat_type', 'theme_es', 'language', 'topic', 'maintainer_url', 'tag_uri', 'contact_uri', 'contact_url', 'publisher_identifier', 'publisher_uri', 'publisher_url', 'publisher_type', 'maintainer_uri', 'maintainer_url', 'author_uri', 'author_url', 'conforms_to', 'theme', 'reference_system', 'spatial_uri', 'representation_type', 'license_id', 'access_rights', 'graphic_overview', 'frequency', 'hvd_category'],
        'resource':
            ['url', 'availability', 'mimetype', 'status', 'resource_relation', 'license', 'rights', 'conforms_to', 'reference_system']
    }

EMAIL_FIELD_NAMES = ['publisher_email', 'maintainer_email', 'author_email', ]