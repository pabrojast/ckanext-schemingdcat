# encoding: utf-8
"""
Upload module for ckanext-schemingdcat.

This module provides functionality for handling file uploads and extracting
spatial extent and metadata from geospatial files.

IMPORTANT: This functionality is designed to work ONLY through the web interface
for form auto-fill purposes. It does NOT interfere with CKAN's API operations.
"""

from ckanext.schemingdcat.upload.extractors import (
    SpatialExtentExtractor, 
    extent_extractor,
    MemberStateDetector,
    member_state_detector
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
    'MemberStateDetector',
    'member_state_detector',
    'extract_spatial_extent',
    'can_extract_spatial_extent',
    'get_spatial_system_status',
    'FileAnalyzer',
    'analyze_file_comprehensive',
    'analyze_upload_file',
]
