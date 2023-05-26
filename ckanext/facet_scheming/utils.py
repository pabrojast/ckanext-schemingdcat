from ckan.common import config
import ckan.logic as logic
import ckan.plugins as plugins
from ckan.lib import helpers as ckan_helpers
import logging
import os
import hashlib
from threading import Lock

logger = logging.getLogger(__name__)

# No configuro estas variables al principio del todo porque no sé si luego la
# aplicación cargará otras extensiones con información que pueda necesitar.
# Configurándolas con la primera petición me aseguro que todo está en orden y
# funcionando cuando se inicien.

_facets_dict = None
_public_dirs = None
_files_hash = []
_dirs_hash = []

_facets_dict_lock = Lock()
_public_dirs_lock = Lock()


def get_facets_dict():
    global _facets_dict
    if not _facets_dict:
        with _facets_dict_lock:
            if not _facets_dict:
# Lo lógico sería colocar un único if tras el lock, pero en esta parte del código solo se entrará
# la primera vez que se ejecute el código al iniciar la aplicación, por lo que me ha parecido más
# eficiente a largo plazo hacerlo así.
                _facets_dict= {}
    
                schema=logic.get_action('scheming_dataset_schema_show')(
                    {},
                    {'type': 'dataset'}
                    )

                for item in schema['dataset_fields']:
                    _facets_dict[item['field_name']]=item['label']

                for item in schema['resource_fields']:
                    _facets_dict[item['field_name']]=item['label']

    return _facets_dict

def get_public_dirs():
    global _public_dirs

    if not _public_dirs:
        with _public_dirs_lock:
            if not _public_dirs:
                _public_dirs = config.get('extra_public_paths', '').split(',')

    return _public_dirs

def public_file_exists(path):
#    logger.debug("Compruebo si existe {0}".format(path))
    file_hash = hashlib.sha512(path.encode('utf-8')).hexdigest()

    if file_hash in _files_hash:
        return True

    for dir in get_public_dirs():
#        logger.debug("Buscando en {0}".format(os.path.join(dir,path)))
        if os.path.isfile(os.path.join(dir,path)):
            _files_hash.append(file_hash)
            return True

    return False

def public_dir_exists(path):
    dir_hash = hashlib.sha512(path.encode('utf-8')).hexdigest()

    if dir_hash in _dirs_hash:
        return True

    for dir in get_public_dirs():
        if os.path.isdir(os.path.join(dir,path)):
            _dirs_hash.append(dir_hash)
            return True

    return False
        