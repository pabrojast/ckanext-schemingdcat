# encoding: utf-8
"""
File handlers and utility functions for spatial extent extraction.
"""

import json
from typing import Optional, Dict, Any

from ckanext.schemingdcat.upload.extractors import extent_extractor, FIONA_AVAILABLE, RASTERIO_AVAILABLE, PYPROJ_AVAILABLE


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
        'api_safe': True,
        'mode': 'frontend_only'
    }
