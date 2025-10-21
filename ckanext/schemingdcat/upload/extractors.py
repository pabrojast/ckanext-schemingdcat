# encoding: utf-8
"""
Spatial extent extractors for various geospatial file formats.
"""

import logging
import os
import tempfile
import zipfile
from typing import Optional, Dict, Any, Tuple

log = logging.getLogger(__name__)

try:
    import fiona
    from fiona.crs import from_epsg
    FIONA_AVAILABLE = True
except ImportError:
    FIONA_AVAILABLE = False
    log.warning("Fiona not available - Shapefile extent extraction disabled")

try:
    import rasterio
    from rasterio.warp import transform_bounds
    RASTERIO_AVAILABLE = True
except ImportError:
    RASTERIO_AVAILABLE = False
    log.warning("Rasterio not available - Raster extent extraction disabled")

try:
    from pyproj import Transformer
    PYPROJ_AVAILABLE = True
except ImportError:
    PYPROJ_AVAILABLE = False
    log.warning("PyProj not available - CRS transformation limited")


class SpatialExtentExtractor:
    """Extract spatial extent from geospatial files."""
    
    SUPPORTED_EXTENSIONS = {
        'shp': 'shapefile',
        'zip': 'zip_shapefile',
        'tif': 'geotiff',
        'tiff': 'geotiff',
        'geotiff': 'geotiff',
        'kml': 'kml',
        'gpkg': 'geopackage',
        'geojson': 'geojson',
        'json': 'geojson'
    }
    
    def __init__(self):
        self.available_handlers = self._check_available_handlers()
    
    def _check_available_handlers(self) -> Dict[str, bool]:
        """Check which file format handlers are available."""
        return {
            'shapefile': FIONA_AVAILABLE,
            'zip_shapefile': FIONA_AVAILABLE,
            'geotiff': RASTERIO_AVAILABLE,
            'kml': FIONA_AVAILABLE,
            'geopackage': FIONA_AVAILABLE,
            'geojson': FIONA_AVAILABLE
        }
    
    def _is_potential_spatial_file(self, file_path_or_url):
        """Check if a file could potentially be a spatial file."""
        if file_path_or_url.startswith(('http://', 'https://')):
            filename = file_path_or_url.split('/')[-1].split('?')[0]
        else:
            filename = os.path.basename(file_path_or_url)
        
        ext = self._get_file_extension(filename)
        spatial_extensions = ['shp', 'tif', 'tiff', 'geotiff', 'kml', 'gpkg', 'geojson', 'json', 'zip']
        return ext in spatial_extensions
    
    def _is_shapefile_zip(self, file_path: str) -> bool:
        """Check if a ZIP file contains a shapefile."""
        try:
            if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                return False
                
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                has_shp = any(f.lower().endswith('.shp') for f in file_list)
                has_shx = any(f.lower().endswith('.shx') for f in file_list)
                has_dbf = any(f.lower().endswith('.dbf') for f in file_list)
                return has_shp and has_shx and has_dbf
                
        except Exception:
            return False
    
    def _get_file_extension(self, file_path: str) -> str:
        """Get file extension in lowercase."""
        return os.path.splitext(file_path)[1].lower().lstrip('.')
    
    def can_extract_extent(self, file_path: str, trust_extension: bool = False) -> bool:
        """Check if extent can be extracted from the given file."""
        ext = self._get_file_extension(file_path)
        if ext not in self.SUPPORTED_EXTENSIONS:
            return False
        
        format_type = self.SUPPORTED_EXTENSIONS[ext]
        
        if trust_extension:
            return self.available_handlers.get(format_type, False)
        
        if format_type == 'zip_shapefile':
            handler_available = self.available_handlers.get(format_type, False)
            return handler_available and self._is_shapefile_zip(file_path)
        
        return self.available_handlers.get(format_type, False)
    
    def extract_extent(self, file_path: str, trust_extension: bool = False) -> Optional[Dict[str, Any]]:
        """Extract spatial extent from a geospatial file."""
        try:
            if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                return None
            
            if not self.can_extract_extent(file_path, trust_extension):
                return None
            
            ext = self._get_file_extension(file_path)
            format_type = self.SUPPORTED_EXTENSIONS[ext]
            
            if format_type == 'shapefile':
                return self._extract_shapefile_extent(file_path)
            elif format_type == 'zip_shapefile':
                return self._extract_zip_shapefile_extent(file_path)
            elif format_type == 'geotiff':
                return self._extract_raster_extent(file_path)
            elif format_type in ['kml', 'geopackage', 'geojson']:
                return self._extract_vector_extent(file_path)
            
            return None
                
        except Exception as e:
            log.error(f"Error extracting extent from {file_path}: {str(e)}", exc_info=True)
            return None
    
    def _extract_shapefile_extent(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Extract extent from Shapefile."""
        if not FIONA_AVAILABLE:
            return None
        
        try:
            with fiona.open(file_path) as src:
                bounds = src.bounds
                crs = src.crs
                
                if crs and crs != from_epsg(4326):
                    bounds = self._transform_bounds(bounds, crs, from_epsg(4326))
                
                return self._bounds_to_geojson(bounds)
                
        except Exception as e:
            log.error(f"Error reading shapefile {file_path}: {str(e)}", exc_info=True)
            return None
    
    def _extract_raster_extent(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Extract extent from raster file (GeoTIFF, etc.)."""
        if not RASTERIO_AVAILABLE:
            return None
        
        try:
            with rasterio.open(file_path) as src:
                bounds = src.bounds
                crs = src.crs
                
                if crs and crs.to_epsg() != 4326:
                    bounds = transform_bounds(crs, 'EPSG:4326', *bounds)
                
                return self._bounds_to_geojson(bounds)
                
        except Exception as e:
            log.debug(f"Error reading raster {file_path}: {str(e)}")
            return None
    
    def _extract_vector_extent(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Extract extent from vector files (KML, GeoPackage, GeoJSON)."""
        if not FIONA_AVAILABLE:
            return None
        
        try:
            with fiona.open(file_path) as src:
                bounds = src.bounds
                crs = src.crs
                
                if crs and crs != from_epsg(4326):
                    bounds = self._transform_bounds(bounds, crs, from_epsg(4326))
                
                return self._bounds_to_geojson(bounds)
                
        except Exception as e:
            log.debug(f"Error reading vector file {file_path}: {str(e)}")
            return None
    
    def _extract_zip_shapefile_extent(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Extract extent from ZIP file containing Shapefile."""
        if not FIONA_AVAILABLE:
            return None
            
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            return None
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                shp_file = None
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        if file.lower().endswith('.shp'):
                            shp_file = os.path.join(root, file)
                            break
                    if shp_file:
                        break
                
                if not shp_file:
                    return None
                
                return self._extract_shapefile_extent(shp_file)
                
        except Exception as e:
            log.error(f"Error reading ZIP shapefile {file_path}: {str(e)}", exc_info=True)
            return None
    
    def _transform_bounds(self, bounds: Tuple[float, float, float, float], 
                         src_crs: Any, dst_crs: Any) -> Tuple[float, float, float, float]:
        """Transform bounds from source CRS to destination CRS."""
        if not PYPROJ_AVAILABLE:
            return bounds
        
        try:
            transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True)
            min_x, min_y = transformer.transform(bounds[0], bounds[1])
            max_x, max_y = transformer.transform(bounds[2], bounds[3])
            return (min_x, min_y, max_x, max_y)
        except Exception as e:
            log.debug(f"Error transforming bounds: {str(e)}")
            return bounds
    
    def _bounds_to_geojson(self, bounds: Tuple[float, float, float, float]) -> Dict[str, Any]:
        """Convert bounds tuple to GeoJSON Polygon."""
        min_x, min_y, max_x, max_y = bounds
        
        coordinates = [[
            [min_x, min_y],
            [max_x, min_y],
            [max_x, max_y],
            [min_x, max_y],
            [min_x, min_y]
        ]]
        
        return {
            "type": "Polygon",
            "coordinates": coordinates
        }
    
    def extract_extent_from_upload(self, upload_file) -> Optional[Dict[str, Any]]:
        """Extract extent from an uploaded file."""
        if not hasattr(upload_file, 'filename') or not upload_file.filename:
            return None

        ext = self._get_file_extension(upload_file.filename)
        
        if not self.can_extract_extent(upload_file.filename, trust_extension=True):
            return None

        try:
            upload_file.seek(0)
            file_content = upload_file.read()
            
            if not file_content:
                return None
            
            suffix = f".{ext}" if ext else ""
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                tmp_file.write(file_content)
                tmp_file.flush()
                
                extent = self.extract_extent(tmp_file.name, trust_extension=True)
                
                try:
                    os.unlink(tmp_file.name)
                except OSError:
                    pass
                
                return extent
                
        except Exception as e:
            log.error(f"Error processing upload {upload_file.filename}: {str(e)}", exc_info=True)
            return None

    def extract_extent_from_url(self, url: str, file_format: str = None) -> Optional[Dict[str, Any]]:
        """Extract extent from a file accessible via URL."""
        if not url:
            return None

        try:
            import urllib.request
            import urllib.error
            
            url_path = url.split('?')[0].split('#')[0]
            ext = self._get_file_extension(url_path)
            
            if not ext and file_format:
                ext = file_format.lower()
            
            should_process = (ext == 'zip' or file_format == 'shp' or 
                            self.can_extract_extent(f"dummy.{ext}", trust_extension=True))
            
            if not should_process:
                return None

            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp_file:
                try:
                    req = urllib.request.Request(url)
                    req.add_header('User-Agent', 'CKAN-SchemingDCAT-SpatialExtractor/1.0')
                    
                    with urllib.request.urlopen(req, timeout=30) as response:
                        chunk_size = 8192
                        total_size = 0
                        while True:
                            chunk = response.read(chunk_size)
                            if not chunk:
                                break
                            tmp_file.write(chunk)
                            total_size += len(chunk)
                            if total_size > 100 * 1024 * 1024:
                                return None
                    
                    tmp_file.flush()
                    
                    if total_size == 0:
                        return None
                    
                    extent = self.extract_extent(tmp_file.name, trust_extension=True)
                    return extent
                    
                except urllib.error.URLError as e:
                    log.error(f"Error downloading file from {url}: {str(e)}")
                    return None
                finally:
                    try:
                        os.unlink(tmp_file.name)
                    except OSError:
                        pass
                        
        except Exception as e:
            log.error(f"Error processing URL {url}: {str(e)}", exc_info=True)
            return None

    def extract_extent_from_resource(self, resource_url, resource_format=None) -> Optional[Dict[str, Any]]:
        """Extract spatial extent from a resource based on its URL and format."""
        if resource_format and resource_format.upper() in ['SHP', 'SHAPEFILE']:
            return self.extract_extent_from_url(resource_url)
        
        if self._is_potential_spatial_file(resource_url):
            return self.extract_extent_from_url(resource_url)
        
        ext = self._get_file_extension(resource_url)
        if ext == 'zip':
            return self.extract_extent_from_url(resource_url)
        
        return None


# Global instance
extent_extractor = SpatialExtentExtractor()
