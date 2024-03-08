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

# Default DCAT metadata configuration
OGC2CKAN_HARVESTER_MD_CONFIG = {
    'access_rights': 'http://inspire.ec.europa.eu/metadata-codelist/LimitationsOnPublicAccess/noLimitations',
    'conformance': [
        'http://inspire.ec.europa.eu/documents/inspire-metadata-regulation','http://inspire.ec.europa.eu/documents/commission-regulation-eu-no-13122014-10-december-2014-amending-regulation-eu-no-10892010-0'
    ],
    'author': 'ckan-ogc',
    'author_email': 'admin@localhost',
    'author_url': '{ckan_instance}/organization/test',
    'author_uri': '{ckan_instance}/organization/test',
    'contact_name': 'ckan-ogc',
    'contact_email': 'admin@localhost',
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
    'lineage_process_steps': 'ckan-ogc lineage process steps.',
    'maintainer': 'ckan-ogc',
    'maintainer_email': 'admin@localhost',
    'maintainer_url': '{ckan_instance}/organization/test',
    'maintainer_uri': '{ckan_instance}/organization/test',
    'metadata_profile': [
        "http://semiceu.github.io/GeoDCAT-AP/releases/2.0.0","http://inspire.ec.europa.eu/document-tags/metadata"
    ],
    'provenance': 'ckan-ogc provenance statement.',
    'publisher_name': 'ckan-ogc',
    'publisher_email': 'admin@localhost',
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
    'spatial': None,
    'spatial_uri': 'http://datos.gob.es/recurso/sector-publico/territorio/Pais/España',
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