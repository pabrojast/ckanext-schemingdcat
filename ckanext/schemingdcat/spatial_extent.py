# encoding: utf-8
"""
Backward compatibility module for spatial_extent.

This module has been refactored into the upload package for better organization:
- ckanext.schemingdcat.upload.extractors - Spatial extent extraction classes
- ckanext.schemingdcat.upload.handlers - Utility functions and status
- ckanext.schemingdcat.upload.analyzers - File analysis and metadata extraction
- ckanext.schemingdcat.upload.api - API endpoints

All imports are forwarded to maintain backward compatibility with existing code.
"""

# Forward all imports from the new modular structure
from ckanext.schemingdcat.upload.extractors import (
    SpatialExtentExtractor,
    extent_extractor,
    FIONA_AVAILABLE,
    RASTERIO_AVAILABLE,
    PYPROJ_AVAILABLE
)
from ckanext.schemingdcat.upload.handlers import (
    extract_spatial_extent,
    can_extract_spatial_extent,
    get_spatial_system_status
)
from ckanext.schemingdcat.upload.analyzers import (
    FileAnalyzer,
    analyze_file_comprehensive,
    analyze_upload_file
)

__all__ = [
    'SpatialExtentExtractor',
    'extent_extractor',
    'FIONA_AVAILABLE',
    'RASTERIO_AVAILABLE',
    'PYPROJ_AVAILABLE',
    'extract_spatial_extent',
    'can_extract_spatial_extent',
    'get_spatial_system_status',
    'FileAnalyzer',
    'analyze_file_comprehensive',
    'analyze_upload_file',
]
