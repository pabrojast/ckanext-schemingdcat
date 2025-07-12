# Spatial Extent Extraction

This feature automatically extracts spatial extent (bounding box) from uploaded geospatial files and populates the `spatial_extent` field in resource metadata.

## Supported File Formats

- **Shapefiles** (.shp) - Requires associated .dbf, .shx files
- **GeoTIFF** (.tif, .tiff) - Raster files with spatial reference
- **KML** (.kml) - Google Earth format
- **GeoPackage** (.gpkg) - OGC standard format
- **GeoJSON** (.geojson, .json) - Web-friendly spatial format

## Requirements

To enable spatial extent extraction, install the spatial dependencies:

```bash
pip install -r spatial-requirements.txt
```

### System Dependencies

The spatial libraries require GDAL to be installed at the system level:

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install gdal-bin libgdal-dev
```

**CentOS/RHEL:**
```bash
sudo yum install gdal gdal-devel
```

**Windows:**
Use conda or OSGeo4W installer.

## How It Works

1. **File Upload**: When uploading a supported spatial file, the system automatically detects it's a spatial format.

2. **Extent Extraction**: The file is processed to extract its spatial extent (bounding box).

3. **Coordinate Transformation**: If the file uses a different coordinate system, it's transformed to WGS84 (EPSG:4326).

4. **Field Population**: The `spatial_extent` field is automatically populated with a GeoJSON Polygon representing the extent.

## Schema Field

The spatial extent field is defined in the schema as:

```yaml
- field_name: spatial_extent
  label:
    en: Spatial extent (auto-extracted)
    es: Extensión espacial (auto-extraída)
    fr: Étendue spatiale (auto-extraite)
  display_property: dcat:spatialResolutionInMeters
  form_snippet: schemingdcat/form_snippets/spatial_extent.html
  display_snippet: schemingdcat/display_snippets/spatial_extent.html
```

## Example Output

The extracted extent is stored as a GeoJSON Polygon:

```json
{
  "type": "Polygon",
  "coordinates": [[
    [-74.0059, 40.7128],
    [-73.9352, 40.7128], 
    [-73.9352, 40.7829],
    [-74.0059, 40.7829],
    [-74.0059, 40.7128]
  ]]
}
```

## Error Handling

- If spatial libraries are not installed, the feature is silently disabled
- Unsupported file types show a warning message
- Processing errors are logged and display user-friendly messages
- The field remains editable for manual input if automatic extraction fails

## User Interface

- **Processing Indicator**: Shows a spinner while extracting extent
- **Success Notification**: Confirms successful extraction
- **Preview Button**: Shows the extent coordinates
- **Map Integration**: Can open the extent in OpenStreetMap
- **Copy Coordinates**: Allows copying the GeoJSON to clipboard

## Integration with Existing Fields

The spatial extent extraction works alongside existing auto-fill features:

- **Format Detection**: Automatically sets format (SHP, GeoTIFF, etc.)
- **MIME Type**: Sets appropriate media type 
- **Character Encoding**: Sets UTF-8 for text-based formats
- **Spatial Extent**: New automatic extent extraction

## API Endpoint

The extraction is handled by a dedicated API endpoint:

```
POST /api/extract-spatial-extent
Content-Type: multipart/form-data

file: [spatial file]
```

Response:
```json
{
  "success": true,
  "extent": {
    "type": "Polygon",
    "coordinates": [...]
  },
  "message": "Spatial extent extracted successfully"
}
```

## Fallback Behavior

If spatial libraries are not available:
- The field is still visible and editable
- No automatic extraction occurs
- Users can manually input spatial extent
- No errors or disruption to normal functionality
