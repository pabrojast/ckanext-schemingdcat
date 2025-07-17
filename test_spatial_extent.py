#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for spatial extent extraction functionality.

This script tests the spatial extent extraction system to ensure it works correctly
with different geospatial file formats.
"""

import sys
import os
import json
import tempfile
import zipfile
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from ckanext.schemingdcat.spatial_extent import SpatialExtentExtractor, get_spatial_system_status
    print("✅ Successfully imported spatial extent modules")
except ImportError as e:
    print(f"❌ Failed to import spatial extent modules: {e}")
    sys.exit(1)

def test_system_status():
    """Test the spatial system status."""
    print("\n🔍 Testing system status...")
    
    status = get_spatial_system_status()
    print(f"System available: {status['available']}")
    print(f"Available handlers: {status['handlers']}")
    print(f"Supported extensions: {status['supported_extensions']}")
    print(f"Dependencies: {status['dependencies']}")
    
    return status['available']

def test_can_extract():
    """Test the can_extract functionality."""
    print("\n🔍 Testing can_extract functionality...")
    
    extractor = SpatialExtentExtractor()
    
    # Test with different file extensions
    test_files = [
        'test.shp',
        'test.tif', 
        'test.geojson',
        'test.kml',
        'test.gpkg',
        'test.zip',
        'test.txt',  # Should not be supported
        'test.csv'   # Should not be supported
    ]
    
    for filename in test_files:
        can_extract = extractor.can_extract_extent(filename, trust_extension=True)
        status = "✅" if can_extract else "❌"
        print(f"{status} {filename}: {can_extract}")

def create_sample_geojson():
    """Create a sample GeoJSON file for testing."""
    sample_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-74.0059, 40.7128],  # New York area
                            [-74.0059, 40.7589],
                            [-73.9441, 40.7589],
                            [-73.9441, 40.7128],
                            [-74.0059, 40.7128]
                        ]
                    ]
                }
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.geojson', delete=False) as f:
        json.dump(sample_geojson, f)
        return f.name

def test_geojson_extraction():
    """Test extraction from a GeoJSON file."""
    print("\n🔍 Testing GeoJSON extraction...")
    
    extractor = SpatialExtentExtractor()
    geojson_file = None
    
    try:
        # Create sample GeoJSON
        geojson_file = create_sample_geojson()
        print(f"Created test file: {geojson_file}")
        
        # Test extraction
        extent = extractor.extract_extent(geojson_file)
        
        if extent:
            print("✅ Successfully extracted extent:")
            print(json.dumps(extent, indent=2))
            
            # Verify it's a valid GeoJSON polygon
            if extent.get('type') == 'Polygon' and 'coordinates' in extent:
                print("✅ Valid GeoJSON Polygon format")
            else:
                print("❌ Invalid GeoJSON format")
                
        else:
            print("❌ Failed to extract extent")
            
    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        
    finally:
        # Clean up
        if geojson_file and os.path.exists(geojson_file):
            os.unlink(geojson_file)
            print(f"Cleaned up test file: {geojson_file}")

def create_sample_shapefile_zip():
    """Create a sample ZIP file with minimal shapefile components."""
    print("\n🔍 Creating sample Shapefile ZIP...")
    
    # Create a minimal shapefile structure
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as zip_file:
        with zipfile.ZipFile(zip_file.name, 'w') as zf:
            # Add minimal shapefile components (empty but valid structure)
            zf.writestr('test.shp', b'')  # Empty shapefile
            zf.writestr('test.shx', b'')  # Empty shape index
            zf.writestr('test.dbf', b'')  # Empty attribute table
            zf.writestr('test.prj', b'')  # Empty projection file
            
        return zip_file.name

def test_shapefile_zip_detection():
    """Test detection of shapefile ZIP files."""
    print("\n🔍 Testing Shapefile ZIP detection...")
    
    extractor = SpatialExtentExtractor()
    zip_file = None
    
    try:
        # Create sample ZIP
        zip_file = create_sample_shapefile_zip()
        print(f"Created test ZIP: {zip_file}")
        
        # Test if it's detected as a shapefile ZIP
        is_shapefile_zip = extractor._is_shapefile_zip(zip_file)
        
        if is_shapefile_zip:
            print("✅ Correctly detected as shapefile ZIP")
        else:
            print("❌ Not detected as shapefile ZIP")
            
        # Test can_extract
        can_extract = extractor.can_extract_extent(zip_file)
        print(f"Can extract extent: {can_extract}")
        
    except Exception as e:
        print(f"❌ Error during ZIP test: {e}")
        
    finally:
        # Clean up
        if zip_file and os.path.exists(zip_file):
            os.unlink(zip_file)
            print(f"Cleaned up test ZIP: {zip_file}")

def main():
    """Run all tests."""
    print("🚀 Starting Spatial Extent Extraction Tests")
    print("=" * 50)
    
    # Test 1: System status
    is_available = test_system_status()
    
    # Test 2: Can extract functionality
    test_can_extract()
    
    if is_available:
        # Test 3: GeoJSON extraction (if fiona is available)
        if get_spatial_system_status()['dependencies'].get('fiona', False):
            test_geojson_extraction()
        else:
            print("\n⚠️ Skipping GeoJSON test - Fiona not available")
            
        # Test 4: Shapefile ZIP detection
        test_shapefile_zip_detection()
    else:
        print("\n⚠️ Skipping extraction tests - Spatial libraries not available")
    
    print("\n" + "=" * 50)
    print("🏁 Tests completed!")
    
    if is_available:
        print("✅ Spatial extent extraction is ready to use!")
    else:
        print("⚠️ To enable spatial extent extraction, install dependencies:")
        print("   pip install -r spatial-requirements.txt")

if __name__ == '__main__':
    main()
