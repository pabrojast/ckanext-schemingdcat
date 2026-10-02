from ckanext.schemingdcat.harvesters.base import SchemingDCATHarvester
from ckanext.schemingdcat.harvesters.ckan import SchemingDCATCKANHarvester

try:
    # The spreadsheet harvester needs gspread and pandas; installations without
    # them (ckan-node) still get the CKAN harvester.
    from ckanext.schemingdcat.harvesters.xls import SchemingDCATXLSHarvester
except ImportError:  # pragma: no cover
    SchemingDCATXLSHarvester = None

__all__ = ['SchemingDCATHarvester', 'SchemingDCATCKANHarvester', 'SchemingDCATXLSHarvester']
