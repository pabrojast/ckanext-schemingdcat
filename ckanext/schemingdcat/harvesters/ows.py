import re
import logging
from urllib.parse import urlparse, urlunparse, urlencode
from owslib.fes import PropertyIsLike, PropertyIsEqualTo, SortBy, SortProperty

from ckan import model

from ckanext.harvest.model import HarvestObject
from ckanext.schemingdcat.lib.ows import CswService
from ckanext.schemingdcat.harvesters.base import SchemingDCATHarvester

log = logging.getLogger(__name__)


# TODO: Adapt to ckanext-harvest code the improved OWS harvester from: https://github.com/mjanez/ckan-ogc/blob/main/ogc2ckan/harvesters/ogc.py
class SchemingDCATOWSHarvester(SchemingDCATHarvester):
    '''
    An expanded Harvester for OWS servers like Geoserver
    '''
    pass