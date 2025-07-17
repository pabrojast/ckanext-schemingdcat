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
            # First check if file exists and has size
            if not os.path.exists(file_path):
                log.debug(f"ZIP file does not exist: {file_path}")
                return False
            
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                log.debug(f"ZIP file has zero size: {file_path}")
                return False
                
            log.info(f"Checking ZIP contents for shapefile components in: {file_path} (size: {file_size} bytes)")
            
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                log.info(f"ZIP contains {len(file_list)} files")
                
                # Check if we have the essential shapefile components
                has_shp = any(f.lower().endswith('.shp') for f in file_list)
                has_shx = any(f.lower().endswith('.shx') for f in file_list)
                has_dbf = any(f.lower().endswith('.dbf') for f in file_list)
                
                # Log detailed information
                log.info(f"Shapefile components check - .shp: {has_shp}, .shx: {has_shx}, .dbf: {has_dbf}")
                
                # A valid shapefile ZIP should have at least .shp, .shx, and .dbf
                return has_shp and has_shx and has_dbf
                
        except zipfile.BadZipFile as e:
            log.info(f"Bad ZIP file {file_path}: {str(e)}")
            return False
        except Exception as e:
            log.info(f"Error checking ZIP contents {file_path}: {str(e)}")
            return False
    
    def can_extract_extent(self, file_path: str, trust_extension: bool = False) -> bool:
        """
        Check if extent can be extracted from the given file.
        
        Args:
            file_path: Path to the file to check
            trust_extension: If True, trust the file extension without further validation
                            (useful for uploaded files that may not be accessible yet)
        """
        ext = self._get_file_extension(file_path)
        if ext not in self.SUPPORTED_EXTENSIONS:
            log.info(f"Unsupported extension: {ext}")
            return False
        
        format_type = self.SUPPORTED_EXTENSIONS[ext]
        log.info(f"Format type for {ext}: {format_type}")
        
        # If we're trusting the extension (for uploaded files), skip validation
        if trust_extension:
            log.info(f"Trusting file extension without validation: {ext}")
            return self.available_handlers.get(format_type, False)
        
        # Special handling for ZIP files - check if they contain shapefiles
        if format_type == 'zip_shapefile':
            handler_available = self.available_handlers.get(format_type, False)
            is_shapefile_zip = self._is_shapefile_zip(file_path) if handler_available else False
            log.info(f"ZIP file validation - handler available: {handler_available}, is shapefile ZIP: {is_shapefile_zip}")
            return handler_available and is_shapefile_zip
        
        return self.available_handlers.get(format_type, False)
    
    def _get_file_extension(self, file_path: str) -> str:
        """Get file extension in lowercase."""
        return os.path.splitext(file_path)[1].lower().lstrip('.')
    
    def extract_extent(self, file_path: str, trust_extension: bool = False) -> Optional[Dict[str, Any]]:
        """
        Extract spatial extent from a geospatial file.
        
        Args:
            file_path: Path to the geospatial file
            trust_extension: If True, trust the file extension without further validation
                            (useful for uploaded files that may not be accessible yet)
            
        Returns:
            GeoJSON Polygon representing the extent in WGS84, or None if extraction fails
        """
        try:
            log.info(f"Starting extent extraction for: {file_path} (trust_extension: {trust_extension})")
            
            if not os.path.exists(file_path):
                log.info(f"File not found: {file_path}")
                return None
            
            file_size = os.path.getsize(file_path)
            log.info(f"File size: {file_size} bytes")
            
            if file_size == 0:
                log.info(f"File has zero size: {file_path}")
                return None
            
            can_extract = self.can_extract_extent(file_path, trust_extension)
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
            
        # Verify the file exists and has content
        if not os.path.exists(file_path):
            log.info(f"ZIP file not found: {file_path}")
            return None
            
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            log.info(f"ZIP file is empty (0 bytes): {file_path}")
            return None
            
        log.info(f"Processing ZIP file: {file_path}, size: {file_size} bytes")
        
        try:
            # Validate ZIP file
            try:
                with zipfile.ZipFile(file_path, 'r') as zip_check:
                    zip_check.testzip()  # Test the integrity of the zip file
                    file_list = zip_check.namelist()
                    log.info(f"ZIP validation passed. Contains {len(file_list)} files.")
            except zipfile.BadZipFile as e:
                log.info(f"Invalid ZIP file format: {str(e)}")
                return None
            except Exception as e:
                log.info(f"Error testing ZIP file: {str(e)}")
                return None
                
            # Create temporary directory to extract ZIP contents
            with tempfile.TemporaryDirectory() as temp_dir:
                log.info(f"Created temporary directory: {temp_dir}")
                
                # Extract ZIP file
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    file_list = zip_ref.namelist()
                    log.info(f"ZIP contains {len(file_list)} files: {file_list}")
                    
                    # Check for common shapefile components
                    shp_files = [f for f in file_list if f.lower().endswith('.shp')]
                    shx_files = [f for f in file_list if f.lower().endswith('.shx')]
                    dbf_files = [f for f in file_list if f.lower().endswith('.dbf')]
                    
                    log.info(f"Found shapefile components - SHP: {len(shp_files)}, SHX: {len(shx_files)}, DBF: {len(dbf_files)}")
                    
                    # Extract all files
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
                
                # Ensure the associated .shx and .dbf files exist
                shp_base = os.path.splitext(shp_file)[0]
                shx_file = shp_base + '.shx'
                dbf_file = shp_base + '.dbf'
                
                if not os.path.exists(shx_file):
                    log.info(f".shx file missing: {shx_file}")
                    return None
                    
                if not os.path.exists(dbf_file):
                    log.info(f".dbf file missing: {dbf_file}")
                    return None
                
                # Extract extent from the shapefile
                log.info(f"Extracting extent from shapefile: {shp_file}")
                result = self._extract_shapefile_extent(shp_file)
                log.info(f"Shapefile extent extraction result: {result}")
                return result
                
        except zipfile.BadZipFile as e:
            log.info(f"Bad ZIP file {file_path}: {str(e)}")
            return None
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
            log.info("No filename in upload file")
            return None

        log.info(f"Processing upload file: {upload_file.filename}")
        
        # Get file extension
        ext = self._get_file_extension(upload_file.filename)
        log.info(f"File extension: {ext}")
        
        # Check if we can extract extent from this file type
        if not self.can_extract_extent(upload_file.filename, trust_extension=True):
            log.info(f"Cannot extract extent from file type: {ext}")
            return None

        # Create temporary file
        try:
            # Get file content
            upload_file.seek(0)
            file_content = upload_file.read()
            
            if not file_content:
                log.info("Upload file is empty")
                return None
            
            log.info(f"File content size: {len(file_content)} bytes")
            
            # Create temporary file with proper extension
            suffix = f".{ext}" if ext else ""
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                tmp_file.write(file_content)
                tmp_file.flush()
                
                log.info(f"Created temporary file: {tmp_file.name}")
                
                # Extract extent
                extent = self.extract_extent(tmp_file.name, trust_extension=True)
                
                # Clean up
                try:
                    os.unlink(tmp_file.name)
                    log.info(f"Cleaned up temporary file: {tmp_file.name}")
                except OSError as e:
                    log.warning(f"Could not delete temporary file {tmp_file.name}: {e}")
                
                return extent
                
        except Exception as e:
            log.error(f"Error processing upload {upload_file.filename}: {str(e)}", exc_info=True)
            return None


# Global instance
extent_extractor = SpatialExtentExtractor()


def extract_spatial_extent(file_path: str, trust_extension: bool = False) -> Optional[str]:
    """
    Convenience function to extract spatial extent from a file.
    
    Args:
        file_path: Path to the geospatial file
        trust_extension: If True, trust the file extension without validating content
        
    Returns:
        JSON string of the extent geometry, or None if extraction fails
    """
    extent = extent_extractor.extract_extent(file_path, trust_extension=trust_extension)
    return json.dumps(extent) if extent else None


def can_extract_spatial_extent(file_path: str, trust_extension: bool = False) -> bool:
    """
    Check if spatial extent can be extracted from the given file.
    
    Args:
        file_path: Path to the file
        trust_extension: If True, trust the file extension without validating content
        
    Returns:
        True if extent extraction is supported for this file type
    """
    return extent_extractor.can_extract_extent(file_path, trust_extension=trust_extension)


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