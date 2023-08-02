from ckan.common import config
import ckan.logic as logic
from ckanext.scheming_dcat import config as fs_config
import logging
import os
import hashlib
from threading import Lock
from ckanext.dcat.utils import CONTENT_TYPES
import yaml
from yaml.loader import SafeLoader
from pathlib import Path

log = logging.getLogger(__name__)

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
    '''
    Busco las etiquetas de todos los campos definidos en el fichero de scheming
    '''
    global _facets_dict
    if not _facets_dict:
        with _facets_dict_lock:
            if not _facets_dict:
                # Lo lógico sería colocar un único if tras el lock, pero en
                # esta parte del código solo se entrará la primera vez que se
                # ejecute el código al iniciar la aplicación, por lo que me ha
                # parecido más eficiente a largo plazo hacerlo así.
                _facets_dict = {}

                schema = logic.get_action('scheming_dataset_schema_show')(
                    {},
                    {'type': 'dataset'}
                    )

                for item in schema['dataset_fields']:
                    _facets_dict[item['field_name']] = item['label']

                for item in schema['resource_fields']:
                    _facets_dict[item['field_name']] = item['label']

    return _facets_dict


def get_public_dirs():
    global _public_dirs

    if not _public_dirs:
        with _public_dirs_lock:
            if not _public_dirs:
                _public_dirs = config.get('extra_public_paths', '').split(',')

    return _public_dirs


def public_file_exists(path):
    #    log.debug("Compruebo si existe {0}".format(path))
    file_hash = hashlib.sha512(path.encode('utf-8')).hexdigest()

    if file_hash in _files_hash:
        return True

    for dir in get_public_dirs():
        #  log.debug("Buscando en {0}".format(os.path.join(dir,path)))
        if os.path.isfile(os.path.join(dir, path)):
            _files_hash.append(file_hash)
            return True

    return False


def public_dir_exists(path):
    dir_hash = hashlib.sha512(path.encode('utf-8')).hexdigest()

    if dir_hash in _dirs_hash:
        return True

    for dir in get_public_dirs():
        if os.path.isdir(os.path.join(dir, path)):
            _dirs_hash.append(dir_hash)
            return True

    return False

def init_config():
    fs_config.linkeddata_links = _load_yaml('linkeddata_links.yaml')
    fs_config.geometadata_links = _load_yaml('geometadata_links.yaml')

def _load_yaml(file):
    source_path = Path(__file__).resolve(True)
    respuesta = {}
    try:
        p = source_path.parent.joinpath('config',file)
        with open(p,'r') as f:
            respuesta=yaml.load(f, Loader=SafeLoader )
    except FileNotFoundError:
        log.error("El fichero {0} no existe".format(file))
    except Exception as e:
        log.error("No ha sido posible leer la configuración de {0}: {1}".format(file, e))
    return respuesta


def get_linked_data(id):
    if fs_config.debug:
        linkeddata_links = _load_yaml('linkeddata_links.yaml')
    else:
        linkeddata_links = fs_config.linkeddata_links

    data=[]
    for name in CONTENT_TYPES:
        data.append({
            'name': name,
            'display_name': linkeddata_links.get(name,{}).get('display_name',CONTENT_TYPES[name]),
            'image_display_url': linkeddata_links.get(name,{}).get('image_display_url', None),
            'description': linkeddata_links.get(name,{}).get('description','Tipos '+ CONTENT_TYPES[name]),
            'description_url': linkeddata_links.get(name,{}).get('description_url', None),
            'endpoint_data':{
                '_id': id,
                '_format': name,
                }
        })

    return data

def get_geospatial_metadata():
    if fs_config.debug:
        geometadata_links = _load_yaml('geometadata_links.yaml')
    else:
        geometadata_links = fs_config.geometadata_links
    data=[]
    for item in geometadata_links.get('csw_formats',{}):
        data.append({
            'name': item['name'],
            'display_name': item['display_name'],
            'image_display_url': item['image_display_url'],
            'description': item['description'],
            'description_url': item['description_url'],
            'url': geometadata_links['csw_url'].format(schema=item['outputSchema'],id='{id}')
        })

    return data
