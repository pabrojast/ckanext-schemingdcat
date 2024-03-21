import re
import logging
from urllib.parse import urlparse, urlunparse, urlencode
from owslib.fes import PropertyIsLike, PropertyIsEqualTo, SortBy, SortProperty

from ckan import model

from ckanext.harvest.model import HarvestObject
from ckanext.spatial.harvesters.csw import CSWHarvester
from ckanext.schemingdcat.lib.ows import CswService
from ckanext.schemingdcat.harvesters.base import SchemingDCATHarvester

log = logging.getLogger(__name__)


# TODO: Adapt to ckanext-harvest code the improved CSW harvester from: https://github.com/mjanez/ckan-ogc/blob/main/ogc2ckan/harvesters/csw.py
class SchemingDCATCSWHarvester(CSWHarvester, SchemingDCATHarvester):
    '''
    An expanded Harvester for CSW servers
    '''
    
    def info(self):
        return {
            'name': 'schemingdcat_csw',
            'title': 'Scheming DCAT INSPIRE CSW endpoint',
            'description': 'Harvester for CSW INSPIRE-GeoDCAT-AP dataset descriptions ' +
                           'serialized as XML metadata according to the INSPIRE ISO 19139 standard.',
            'about_url': 'https://github.com/mjanez/ckanext-schemingdcat?tab=readme-ov-file#schemingdcat-csw-inspire-harvester'
        }
        
    csw = None
        
    def _set_constraints_keywords(self, constraints):
        self.contraints['keywords'] = [PropertyIsLike("csw:anyText", keyword) for keyword in constraints["keywords"]]
    
    def _set_constraints_mails(self, constraints):
        self.constraints["mails"] = [mail.lower().replace(' ','') for mail in constraints["mails"]]

    def get_original_url(self, harvest_object_id):
        obj = model.Session.query(HarvestObject).\
                                    filter(HarvestObject.id==harvest_object_id).\
                                    first()

        parts = urlparse(obj.source.url)

        params = {
            'SERVICE': 'CSW',
            'VERSION': '2.0.2',
            'REQUEST': 'GetRecordById',
            'OUTPUTSCHEMA': 'http://www.isotc211.org/2005/gmd',
            'OUTPUTFORMAT':'application/xml' ,
            'ID': obj.guid
        }

        url = urlunparse((
            parts.scheme,
            parts.netloc,
            parts.path,
            None,
            urlencode(params),
            None
        ))

        return url

    def output_schema(self):
        return 'gmd'
    
    def _setup_csw_client(self, url):
        self.csw = CswService(url)
        self.csw_url = url
        self.constraints = {}
        
    def validate_config(self, config):
        config_obj = self.get_harvester_basic_info(config)