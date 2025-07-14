"""
Spatial extent extraction utilities for geospatial files.

This module provides functionality to extract spatial extent (bounding box)
from various geospatial file formats including Shapefiles, GeoTIFF, and others.

IMPORTANT: This functionality is designed to work ONLY through the web interface
for form auto-fill purposes. It does NOT interfere with CKAN's API operations
(resource_create, package_create, etc.) as it only runs client-side via JavaScript
when users upload files through the web form.

API Safety:
- No hooks into CKAN's core upload/create actions
- Only activated via frontend JavaScript in upload.html
- Completely separate endpoint (/api/extract-spatial-extent)
- Graceful degradation when spatial libraries are not available
- Silent failure mode to avoid disrupting normal workflows
"""

import json
import logging
import tempfile
import os
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
        'zip': 'zip_shapefile',  # ZIP files containing shapefiles
        'tif': 'geotiff',
        'tiff': 'geotiff',
        'geotiff': 'geotiff',
        'kml': 'kml',
        'gpkg': 'geopackage',
        'geojson': 'geojson',
        'json': 'geojson'  # Assume GeoJSON if JSON
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
    
    def _is_shapefile_zip(self, file_path: str) -> bool:
        """Check if a ZIP file contains a shapefile."""
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                
                # Check if we have the essential shapefile components
                has_shp = any(f.lower().endswith('.shp') for f in file_list)
                has_shx = any(f.lower().endswith('.shx') for f in file_list)
                has_dbf = any(f.lower().endswith('.dbf') for f in file_list)
                
                # A valid shapefile ZIP should have at least .shp, .shx, and .dbf
                return has_shp and has_shx and has_dbf
                
        except Exception as e:
            log.debug(f"Error checking ZIP contents {file_path}: {str(e)}")
            return False
    
    def can_extract_extent(self, file_path: str) -> bool:
        """Check if extent can be extracted from the given file."""
        ext = self._get_file_extension(file_path)
        if ext not in self.SUPPORTED_EXTENSIONS:
            return False
        
        format_type = self.SUPPORTED_EXTENSIONS[ext]
        
        # Special handling for ZIP files - check if they contain shapefiles
        if format_type == 'zip_shapefile':
            return self.available_handlers.get(format_type, False) and self._is_shapefile_zip(file_path)
        
        return self.available_handlers.get(format_type, False)
    
    def _get_file_extension(self, file_path: str) -> str:
        """Get file extension in lowercase."""
        return os.path.splitext(file_path)[1].lower().lstrip('.')
    
    def extract_extent(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Extract spatial extent from a geospatial file.
        
        Args:
            file_path: Path to the geospatial file
            
        Returns:
            GeoJSON Polygon representing the extent in WGS84, or None if extraction fails
        """
        try:
            log.info(f"Starting extent extraction for: {file_path}")
            
            if not os.path.exists(file_path):
                log.info(f"File not found: {file_path}")
                return None
            
            file_size = os.path.getsize(file_path)
            log.info(f"File size: {file_size} bytes")
            
            can_extract = self.can_extract_extent(file_path)
            log.info(f"Can extract extent: {can_extract}")
            
            if not can_extract:
                log.info(f"Cannot extract extent from file: {file_path}")
                ext = self._get_file_extension(file_path)
                log.info(f"File extension: {ext}")
                log.info(f"Supported extensions: {list(self.SUPPORTED_EXTENSIONS.keys())}")
                if ext in self.SUPPORTED_EXTENSIONS:
                    format_type = self.SUPPORTED_EXTENSIONS[ext]
                    log.info(f"Format type: {format_type}")
                    log.info(f"Handler available: {self.available_handlers.get(format_type, False)}")
                return None
            
            ext = self._get_file_extension(file_path)
            format_type = self.SUPPORTED_EXTENSIONS[ext]
            log.info(f"Processing as format type: {format_type}")
            
            if format_type == 'shapefile':
                return self._extract_shapefile_extent(file_path)
            elif format_type == 'zip_shapefile':
                return self._extract_zip_shapefile_extent(file_path)
            elif format_type == 'geotiff':
                return self._extract_raster_extent(file_path)
            elif format_type in ['kml', 'geopackage', 'geojson']:
                return self._extract_vector_extent(file_path)
            else:
                log.info(f"Unsupported format type: {format_type}")
                return None
                
        except Exception as e:
            # Use info level for debugging the 400 error
            log.error(f"Error extracting extent from {file_path}: {str(e)}", exc_info=True)
            return None
    
    def _extract_shapefile_extent(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Extract extent from Shapefile."""
        log.info(f"Extracting extent from shapefile: {file_path}")
        
        if not FIONA_AVAILABLE:
            log.info("Fiona not available for shapefile extraction")
            return None
        
        try:
            log.info(f"Opening shapefile with fiona: {file_path}")
            with fiona.open(file_path) as src:
                log.info(f"Shapefile opened successfully - driver: {src.driver}")
                log.info(f"Shapefile CRS: {src.crs}")
                log.info(f"Shapefile schema: {src.schema}")
                log.info(f"Shapefile feature count: {len(src)}")
                
                bounds = src.bounds
                log.info(f"Raw bounds: {bounds}")
                crs = src.crs
                
                # Transform to WGS84 if needed
                if crs and crs != from_epsg(4326):
                    log.info(f"Transforming bounds from {crs} to WGS84")
                    bounds = self._transform_bounds(bounds, crs, from_epsg(4326))
                    log.info(f"Transformed bounds: {bounds}")
                else:
                    log.info("Bounds already in WGS84 or no CRS info")
                
                result = self._bounds_to_geojson(bounds)
                log.info(f"Final GeoJSON result: {result}")
                return result
                
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
                
                # Transform to WGS84 if needed
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
                
                # Transform to WGS84 if needed
                if crs and crs != from_epsg(4326):
                    bounds = self._transform_bounds(bounds, crs, from_epsg(4326))
                
                return self._bounds_to_geojson(bounds)
                
        except Exception as e:
            log.debug(f"Error reading vector file {file_path}: {str(e)}")
            return None
    
    def _extract_zip_shapefile_extent(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Extract extent from ZIP file containing Shapefile."""
        log.info(f"Extracting extent from ZIP shapefile: {file_path}")
        
        if not FIONA_AVAILABLE:
            log.info("Fiona not available for ZIP shapefile extraction")
            return None
        
        try:
            # Create temporary directory to extract ZIP contents
            with tempfile.TemporaryDirectory() as temp_dir:
                log.info(f"Created temporary directory: {temp_dir}")
                
                # Extract ZIP file
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    file_list = zip_ref.namelist()
                    log.info(f"ZIP contains {len(file_list)} files: {file_list}")
                    zip_ref.extractall(temp_dir)
                    log.info(f"Extracted ZIP contents to: {temp_dir}")
                
                # Look for .shp file in extracted contents
                shp_file = None
                for root, dirs, files in os.walk(temp_dir):
                    log.info(f"Checking directory: {root}, files: {files}")
                    for file in files:
                        if file.lower().endswith('.shp'):
                            shp_file = os.path.join(root, file)
                            log.info(f"Found shapefile: {shp_file}")
                            break
                    if shp_file:
                        break
                
                if not shp_file:
                    log.info(f"No .shp file found in ZIP: {file_path}")
                    return None
                
                # Check if shapefile exists and is readable
                if not os.path.exists(shp_file):
                    log.info(f"Shapefile path does not exist: {shp_file}")
                    return None
                
                shp_size = os.path.getsize(shp_file)
                log.info(f"Shapefile size: {shp_size} bytes")
                
                # Extract extent from the shapefile
                log.info(f"Extracting extent from shapefile: {shp_file}")
                result = self._extract_shapefile_extent(shp_file)
                log.info(f"Shapefile extent extraction result: {result}")
                return result
                
        except Exception as e:
            log.error(f"Error reading ZIP shapefile {file_path}: {str(e)}", exc_info=True)
            return None
    
    def _transform_bounds(self, bounds: Tuple[float, float, float, float], 
                         src_crs: Any, dst_crs: Any) -> Tuple[float, float, float, float]:
        """Transform bounds from source CRS to destination CRS."""
        if not PYPROJ_AVAILABLE:
            log.debug("PyProj not available - returning original bounds")
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
        
        # Create a polygon from the bounds
        coordinates = [[
            [min_x, min_y],  # Bottom-left
            [max_x, min_y],  # Bottom-right
            [max_x, max_y],  # Top-right
            [min_x, max_y],  # Top-left
            [min_x, min_y]   # Close the polygon
        ]]
        
        return {
            "type": "Polygon",
            "coordinates": coordinates
        }
    
    def extract_extent_from_upload(self, upload_file) -> Optional[Dict[str, Any]]:
        """
        Extract extent from an uploaded file.
        
        Args:
            upload_file: File upload object (from request)
            
        Returns:
            GeoJSON Polygon representing the extent, or None if extraction fails
        """
        if not hasattr(upload_file, 'filename') or not upload_file.filename:
            return None
        
        # Create temporary file
        try:
            with tempfile.NamedTemporaryFile(delete=False, 
                                           suffix=os.path.splitext(upload_file.filename)[1]) as tmp_file:
                # Copy upload content to temporary file
                upload_file.seek(0)
                tmp_file.write(upload_file.read())
                tmp_file.flush()
                
                # Extract extent
                extent = self.extract_extent(tmp_file.name)
                
                # Clean up
                os.unlink(tmp_file.name)
                
                return extent
                
        except Exception as e:
            log.debug(f"Error processing upload {upload_file.filename}: {str(e)}")
            return None


# Global instance
extent_extractor = SpatialExtentExtractor()


def extract_spatial_extent(file_path: str) -> Optional[str]:
    """
    Convenience function to extract spatial extent from a file.
    
    Args:
        file_path: Path to the geospatial file
        
    Returns:
        JSON string of the extent geometry, or None if extraction fails
    """
    extent = extent_extractor.extract_extent(file_path)
    return json.dumps(extent) if extent else None


def can_extract_spatial_extent(file_path: str) -> bool:
    """
    Check if spatial extent can be extracted from the given file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if extent extraction is supported for this file type
    """
    return extent_extractor.can_extract_extent(file_path)


def get_spatial_system_status() -> Dict[str, Any]:
    """
    Get the status of the spatial extent extraction system.
    
    Returns:
        Dictionary with system status information
    """
    return {
        'available': any(extent_extractor.available_handlers.values()),
        'handlers': extent_extractor.available_handlers.copy(),
        'supported_extensions': list(extent_extractor.SUPPORTED_EXTENSIONS.keys()),
        'dependencies': {
            'fiona': FIONA_AVAILABLE,
            'rasterio': RASTERIO_AVAILABLE,
            'pyproj': PYPROJ_AVAILABLE
        },
        'api_safe': True,  # This system doesn't interfere with CKAN API
        'mode': 'frontend_only'  # Only works through web interface
    }
