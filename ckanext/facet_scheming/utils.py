

from ckan.common import config
import ckan.logic as logic
import ckan.plugins as plugins
from ckan.lib import helpers as ckan_helpers
import logging
import os

logger = logging.getLogger(__name__)

_facets_dict=None
_public_dirs = None


def get_facets_dict():
    global _facets_dict
    if not _facets_dict:
        _facets_dict= {}

        schema=logic.get_action('scheming_dataset_schema_show')({}, {'type': 'dataset'})

        for item in schema['dataset_fields']:
            _facets_dict[item['field_name']]=item['label']
        for item in schema['resource_fields']:
            _facets_dict[item['field_name']]=item['label']

    return _facets_dict

def _get_public_dirs():

    public_dirs = config.get('extra_public_paths', '').split(',')
            
    logger.debug("Directorios públicos: {0}".format(public_dirs))
    return public_dirs

def get_public_dirs():
    global _public_dirs

    if not _public_dirs:
        _public_dirs=_get_public_dirs()
        
    return _public_dirs

def public_file_exists(path):
    logger.debug("Compruebo si existe {0}".format(path))
    for dir in get_public_dirs():
        logger.debug("Buscando en {0}".format(os.path.join(dir,path)))
        if os.path.isfile(os.path.join(dir,path)):
            logger.debug("Existe {0}".format(os.path.join(dir,path)))
            return True
        
    return False

def public_dir_exists(path):
    logger.debug("Compruebo si existe el directorio {0}".format(path))
    for dir in get_public_dirs():
        logger.debug("Buscando en {0}".format(os.path.join(dir,path)))
        if os.path.isdir(os.path.join(dir,path)):
            logger.debug("Existe {0}".format(os.path.join(dir,path)))
            return True
        
    return False
        