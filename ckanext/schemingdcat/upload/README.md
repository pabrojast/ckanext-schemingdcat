# Upload Module

This module provides functionality for handling file uploads and extracting spatial extent and metadata from geospatial files in ckanext-schemingdcat.

## Module Structure

The upload functionality has been refactored into several focused modules for better maintainability:

### `extractors.py`
Core spatial extent extraction functionality.
- `SpatialExtentExtractor`: Main class for extracting spatial extents from various geospatial file formats
- `extent_extractor`: Global instance of SpatialExtentExtractor
- Supports: Shapefiles, GeoTIFF, KML, GeoPackage, GeoJSON, ZIP files containing shapefiles

### `handlers.py`
Utility functions and system status handlers.
- `extract_spatial_extent()`: Convenience function to extract extent as JSON string
- `can_extract_spatial_extent()`: Check if extent can be extracted from a file
- `get_spatial_system_status()`: Get status of spatial extraction system and dependencies

### `analyzers.py`
File analysis and metadata extraction.
- `FileAnalyzer`: Comprehensive file analyzer that extracts metadata from various file types
- `analyze_file_comprehensive()`: Analyze file and extract all available metadata
- `analyze_upload_file()`: Analyze uploaded file from form submission

### `api.py`
API endpoints for spatial extent extraction.
- `extract_spatial_extent_endpoint()`: Handle direct file uploads and URL processing
- `extract_spatial_extent_from_resource_endpoint()`: Handle post-upload resource processing

## Usage

```python
# Import from the upload module
from ckanext.schemingdcat.upload import extent_extractor, FileAnalyzer

# Extract spatial extent from file
extent = extent_extractor.extract_extent('/path/to/shapefile.shp')

# Analyze file comprehensively
analyzer = FileAnalyzer()
metadata = analyzer.analyze_file('/path/to/file.tif')

# Check system status
from ckanext.schemingdcat.upload import get_spatial_system_status
status = get_spatial_system_status()
```

## Backward Compatibility

For backward compatibility, the original `spatial_extent.py` module still exists and forwards all imports to the new upload package structure. Existing code using:

```python
from ckanext.schemingdcat.spatial_extent import extent_extractor
```

will continue to work without modification.

## Frontend Components

The upload functionality also includes JavaScript modules for the web interface:

- **`schemingdcat-modern-upload.js`**: Modern drag-and-drop upload interface with file preview and auto-fill
- **`schemingdcat-multi-resource-upload.js`**: Multiple file upload handling for resources

These JavaScript modules work together with the Python API endpoints to provide a seamless upload experience.

## Dependencies

Optional dependencies for full functionality:
- **fiona**: Required for Shapefile, KML, GeoPackage, GeoJSON support
- **rasterio**: Required for GeoTIFF and other raster formats
- **pyproj**: Required for coordinate reference system transformations
- **pandas**: Required for tabular file analysis (CSV, Excel)
- **PyPDF2**: Required for PDF metadata extraction

The module gracefully degrades when dependencies are not available.

## Design Philosophy

This module is designed to work **ONLY** through the web interface for form auto-fill purposes. It does NOT interfere with CKAN's core API operations as it only runs client-side via JavaScript when users upload files through the web form.

### API Safety
- No hooks into CKAN's core upload/create actions
- Only activated via frontend JavaScript
- Completely separate endpoint (`/api/extract-spatial-extent`)
- Graceful degradation when spatial libraries are not available
- Silent failure mode to avoid disrupting normal workflows
