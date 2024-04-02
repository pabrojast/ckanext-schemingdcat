from datetime import datetime
import logging
import uuid
import os

from owslib.csw import CatalogueServiceWeb
from owslib.fes import PropertyIsEqualTo

from ckanext.spatial.lib.csw_client import CswService

log = logging.getLogger(__name__)


class CswError(Exception):
    pass

class CswService(CswService):
    """
    Represents a CSW (Catalogue Service for the Web) service.

    This class provides methods to interact with a CSW service, such as querying for records.

    Args:
        CswService (CswService): The base class for the CSW service.

    Attributes:
        sortby (str): The sort order for the records.

    """

    def getrecords(self, qtype=None, limit=None, keywords=[],
                   typenames="csw:Record", esn="brief",
                   skip=0, count=10, outputschema="gmd", **kw):
        """
        Get records from the CSW service.

        Args:
            qtype (str, optional): The type of records to query. Defaults to None.
            limit (int, optional): The maximum number of records to retrieve. Defaults to None.
            keywords (list, optional): The keywords to filter the records. Defaults to [].
            typenames (str, optional): The type names of the records. Defaults to "csw:Record".
            esn (str, optional): The element set name. Defaults to "full".
            skip (int, optional): The number of records to skip. Defaults to 0.
            count (int, optional): The number of records to retrieve. Defaults to 10.
            outputschema (str, optional): The output schema for the records. Defaults to "gmd".
            **kw: Additional keyword arguments.

        Returns:
            list: A list of records retrieved from the CSW service.

        Raises:
            CswError: If there is an error getting the records.
            
        Additional Information:
            getrecords2 (OWSLib): Construct and process a GetRecords request in order to retrieve metadata records from a CSW.
            Parameters
            ----------
            - constraints: the list of constraints (OgcExpression from owslib.fes module)
            - sortby: an OGC SortBy object (SortBy from owslib.fes module)
            - typenames: the typeNames to query against (default is csw:Record)
            - esn: the ElementSetName 'full', 'brief' or 'summary' (default is 'summary')
            - outputschema: the outputSchema (default is 'http://www.opengis.net/cat/csw/2.0.2' or 'gmd' if use namespaces[outputschema] )
            - format: the outputFormat (default is 'application/xml')
            - startposition: requests a slice of the result set, starting at this position (default is 0)
            - maxrecords: the maximum number of records to return. No records are returned if 0 (default is 10)
            - cql: common query language text.  Note this overrides bbox, qtype, keywords
            - xml: raw XML request.  Note this overrides all other options
            - resulttype: the resultType 'hits', 'results', 'validate' (default is 'results')
            - distributedsearch: `bool` of whether to trigger distributed search
            - hopcount: number of message hops before search is terminated (default is 1)

        """
        from owslib.csw import namespaces
        constraints = []
        csw = self._ows(**kw)

        if qtype is not None:
           constraints.append(PropertyIsEqualTo("dc:type", qtype))

        kwa = {
            "constraints": constraints,
            "typenames": typenames,
            "esn": esn,
            "startposition": skip,
            "maxrecords": count,
            "outputschema": namespaces[outputschema],
            "sortby": self.sortby
            }

        log.info('Making CSW request: getrecords2 %r', kwa)
        csw.getrecords2(**kwa)

        if csw.exceptionreport:
            err = 'Error getting records: %r' % \
                  csw.exceptionreport.exceptions
            #log.error(err)
            raise CswError(err)

        return [self._xmd(r) for r in list(csw.records.values())]
    
