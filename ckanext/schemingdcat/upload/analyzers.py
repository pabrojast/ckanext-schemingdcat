# encoding: utf-8
"""
File analyzers for extracting comprehensive metadata from various file formats.
"""

import json
import logging
import os
import tempfile
from typing import Dict, Any

from ckanext.schemingdcat.upload.extractors import extent_extractor, FIONA_AVAILABLE, RASTERIO_AVAILABLE

log = logging.getLogger(__name__)


class FileAnalyzer:
    """
    Comprehensive file analyzer that extracts various metadata from uploaded files.
    
    This class provides functionality to extract:
    - Spatial information (extent, CRS, resolution, features)
    - Data information (fields, statistics, domains)
    - Technical information (file size, compression, integrity)
    - Content-specific information (pages, sheets, text content)
    """
    
    def __init__(self):
        self.extent_extractor = extent_extractor
        
    def analyze_file(self, file_path: str, trust_extension: bool = False) -> Dict[str, Any]:
        """
        Analyze a file and extract comprehensive metadata.
        
        Args:
            file_path: Path to the file to analyze
            trust_extension: Whether to trust the file extension
            
        Returns:
            Dictionary containing all extracted metadata
        """
        metadata = {}
        
        try:
            if not os.path.exists(file_path):
                return metadata
                
            file_stats = os.stat(file_path)
            metadata['file_size_bytes'] = str(file_stats.st_size)
            metadata['file_created_date'] = self._format_date(file_stats.st_ctime)
            metadata['file_modified_date'] = self._format_date(file_stats.st_mtime)
            
            ext = os.path.splitext(file_path)[1].lower().strip('.')
            metadata['content_type_detected'] = self._get_content_type(ext)
            
            try:
                if self.extent_extractor.can_extract_extent(file_path, trust_extension):
                    extent = self.extent_extractor.extract_extent(file_path, trust_extension)
                    if extent:
                        metadata['spatial_extent'] = json.dumps(extent)
                        
                    if ext in ['shp', 'gpkg', 'geojson', 'kml', 'gml']:
                        self._extract_vector_metadata(file_path, metadata)
                    elif ext in ['tif', 'tiff', 'geotiff']:
                        self._extract_raster_metadata(file_path, metadata)
            except Exception as e:
                log.warning(f"Could not extract spatial metadata: {str(e)}")
            
            if ext in ['csv', 'xls', 'xlsx']:
                self._extract_tabular_metadata(file_path, metadata)
                
            if ext == 'pdf':
                self._extract_pdf_metadata(file_path, metadata)
                    
            return metadata
            
        except Exception as e:
            log.error(f"Error analyzing file {file_path}: {str(e)}")
            return metadata
    
    def _format_date(self, timestamp: float) -> str:
        """Format timestamp as ISO date string."""
        import datetime
        return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
    
    def _get_content_type(self, ext: str) -> str:
        """Get content type based on file extension."""
        content_types = {
            'csv': 'CSV',
            'xls': 'Excel',
            'xlsx': 'Excel',
            'pdf': 'PDF',
            'txt': 'Text',
            'json': 'JSON',
            'geojson': 'GeoJSON',
            'xml': 'XML',
            'shp': 'Shapefile',
            'tif': 'GeoTIFF',
            'tiff': 'GeoTIFF',
            'gpkg': 'GeoPackage',
            'kml': 'KML',
            'kmz': 'KMZ',
            'gml': 'GML'
        }
        return content_types.get(ext, ext.upper() if ext else 'Unknown')
    
    def _extract_vector_metadata(self, file_path: str, metadata: Dict[str, Any]):
        """Extract metadata from vector files."""
        if not FIONA_AVAILABLE:
            return
            
        try:
            import fiona
            with fiona.open(file_path) as src:
                metadata['feature_count'] = str(len(src))
                metadata['geometry_type'] = src.schema['geometry']
                
                if src.crs:
                    metadata['spatial_crs'] = str(src.crs.get('init', ''))
                    
                fields = []
                for name, dtype in src.schema['properties'].items():
                    fields.append({'name': name, 'type': dtype})
                metadata['data_fields'] = json.dumps(fields)
                
        except Exception as e:
            log.warning(f"Could not extract vector metadata: {str(e)}")
    
    def _extract_raster_metadata(self, file_path: str, metadata: Dict[str, Any]):
        """Extract metadata from raster files."""
        if not RASTERIO_AVAILABLE:
            return
            
        try:
            import rasterio
            with rasterio.open(file_path) as src:
                metadata['spatial_crs'] = str(src.crs)
                metadata['spatial_resolution'] = f"{src.res[0]}m x {src.res[1]}m"
                
                bands = []
                for i in range(1, src.count + 1):
                    bands.append({
                        'band': i,
                        'dtype': str(src.dtypes[i-1])
                    })
                metadata['data_fields'] = json.dumps(bands)
                
        except Exception as e:
            log.warning(f"Could not extract raster metadata: {str(e)}")
    
    def _extract_tabular_metadata(self, file_path: str, metadata: Dict[str, Any]):
        """Extract metadata from tabular files (CSV, Excel)."""
        try:
            import pandas as pd

            ext = os.path.splitext(file_path)[1].lower().strip('.')
            if ext == 'csv':
                df = pd.read_csv(file_path, nrows=1000)
            elif ext in ['xls', 'xlsx']:
                df = pd.read_excel(file_path, nrows=1000)
                xl_file = pd.ExcelFile(file_path)
                metadata['spreadsheet_sheets'] = str(len(xl_file.sheet_names))

            fields = []
            for col in df.columns:
                fields.append({
                    'name': col,
                    'type': str(df[col].dtype)
                })
            metadata['data_fields'] = json.dumps(fields)

            stats = {
                'row_count': len(df),
                'column_count': len(df.columns)
            }
            metadata['data_statistics'] = json.dumps(stats)

            # Tabular spatial extent: only emit when no other extractor has
            # already produced one (vector/raster paths win). Computes the
            # bbox by streaming the whole file, not the 1000-row sample.
            if 'spatial_extent' not in metadata:
                self._extract_tabular_spatial_extent(file_path, ext, metadata)

        except Exception as e:
            log.warning(f"Could not extract tabular metadata: {str(e)}")

    # Column-name patterns we accept as latitude / longitude. Matched after
    # lowercasing and stripping non-alphanumerics, so "Lat (DD)", "lat_dd",
    # "LATITUDE" and "latitud" all collapse to the same form.
    _LAT_COLUMN_NAMES = {
        'lat', 'latitude', 'latitud', 'latitudes',
        'latdd', 'latitudedd', 'latdeg', 'latitudedeg',
        'latdecimal', 'latitudedecimal',
        'ycoord', 'ycoordinate', 'ylat', 'latitudey',
    }
    _LON_COLUMN_NAMES = {
        'lon', 'long', 'lng', 'longitude', 'longitud', 'longitudes',
        'londd', 'longdd', 'lngdd', 'longitudedd',
        'londeg', 'longdeg', 'longitudedeg',
        'londecimal', 'longdecimal', 'longitudedecimal',
        'xcoord', 'xcoordinate', 'xlon', 'longitudex',
    }

    @classmethod
    def _normalise_column_name(cls, name):
        return ''.join(c for c in str(name).strip().lower() if c.isalnum())

    @classmethod
    def _detect_latlon_columns(cls, columns):
        """Return (lat_col, lon_col) or (None, None) if not found.

        Strict matching by name only — we deliberately do *not* fall back
        to bare 'x' / 'y' because those collide with too many unrelated
        datasets. If multiple matches exist, the first column wins.
        """
        lat_col = None
        lon_col = None
        for col in columns:
            norm = cls._normalise_column_name(col)
            if lat_col is None and norm in cls._LAT_COLUMN_NAMES:
                lat_col = col
            elif lon_col is None and norm in cls._LON_COLUMN_NAMES:
                lon_col = col
            if lat_col is not None and lon_col is not None:
                break
        return lat_col, lon_col

    def _extract_tabular_spatial_extent(self, file_path: str, ext: str,
                                        metadata: Dict[str, Any]):
        """Build a polygon GeoJSON bbox from lat/lon columns if present.

        Strategy:
        1. Read column headers first (cheap) to decide whether the file
           even has lat/lon columns.
        2. If yes, stream the file in chunks so we cover every row without
           buffering the whole table in RAM.
        3. Validate each value: skip NaN, require lat ∈ [-90, 90] and
           lon ∈ [-180, 180]. If after streaming we have <2 valid rows we
           abort silently — the bbox would be a degenerate point/line.
        """
        try:
            import pandas as pd
        except Exception:
            return

        try:
            if ext == 'csv':
                headers = pd.read_csv(file_path, nrows=0).columns
            elif ext in ('xls', 'xlsx'):
                headers = pd.read_excel(file_path, nrows=0).columns
            else:
                return
        except Exception as header_err:
            log.warning(
                f"Could not read headers for lat/lon detection: {header_err}"
            )
            return

        lat_col, lon_col = self._detect_latlon_columns(headers)
        if lat_col is None or lon_col is None:
            return

        min_lat = min_lon = float('inf')
        max_lat = max_lon = float('-inf')
        count = 0

        try:
            if ext == 'csv':
                iterator = pd.read_csv(
                    file_path,
                    usecols=[lat_col, lon_col],
                    chunksize=20000,
                    iterator=True,
                )
            else:
                # Excel can't stream — read once, full sheet.
                single = pd.read_excel(file_path, usecols=[lat_col, lon_col])
                iterator = [single]
        except Exception as read_err:
            log.warning(
                f"Could not stream lat/lon columns "
                f"({lat_col!r}, {lon_col!r}): {read_err}"
            )
            return

        try:
            for chunk in iterator:
                lats = pd.to_numeric(chunk[lat_col], errors='coerce')
                lons = pd.to_numeric(chunk[lon_col], errors='coerce')
                mask = (
                    lats.between(-90, 90)
                    & lons.between(-180, 180)
                    & lats.notna()
                    & lons.notna()
                )
                if not mask.any():
                    continue
                lats = lats[mask]
                lons = lons[mask]
                min_lat = min(min_lat, float(lats.min()))
                max_lat = max(max_lat, float(lats.max()))
                min_lon = min(min_lon, float(lons.min()))
                max_lon = max(max_lon, float(lons.max()))
                count += int(mask.sum())
        except Exception as iter_err:
            log.warning(
                f"Error scanning lat/lon values in {file_path}: {iter_err}"
            )
            return

        if count < 2 or min_lat == float('inf'):
            log.info(
                f"lat/lon columns found ({lat_col!r}, {lon_col!r}) but "
                f"insufficient valid rows for bbox (count={count})"
            )
            return

        if min_lat == max_lat and min_lon == max_lon:
            # All points coincide — emit a Point instead of a degenerate
            # polygon so the spatial index still picks it up.
            geom = {'type': 'Point', 'coordinates': [min_lon, min_lat]}
        else:
            geom = {
                'type': 'Polygon',
                'coordinates': [[
                    [min_lon, min_lat],
                    [max_lon, min_lat],
                    [max_lon, max_lat],
                    [min_lon, max_lat],
                    [min_lon, min_lat],
                ]],
            }

        metadata['spatial_extent'] = json.dumps(geom)
        metadata.setdefault('spatial_crs', 'EPSG:4326')
        log.info(
            f"Derived spatial_extent from CSV lat/lon columns "
            f"({lat_col!r}, {lon_col!r}): {count} points, "
            f"bbox=[{min_lon:.4f},{min_lat:.4f},{max_lon:.4f},{max_lat:.4f}]"
        )
    
    def _extract_pdf_metadata(self, file_path: str, metadata: Dict[str, Any]):
        """Extract metadata from PDF files."""
        try:
            import PyPDF2
            
            with open(file_path, 'rb') as f:
                pdf = PyPDF2.PdfReader(f)
                metadata['document_pages'] = str(len(pdf.pages))
                
                if pdf.metadata:
                    pdf_info = {}
                    for key, value in pdf.metadata.items():
                        if value:
                            pdf_info[key] = str(value)
                    if pdf_info:
                        metadata['text_content_info'] = json.dumps(pdf_info)
                        
        except Exception as e:
            log.warning(f"Could not extract PDF metadata: {str(e)}")


def analyze_file_comprehensive(file_path: str) -> Dict[str, Any]:
    """
    Analyze a file comprehensively and extract all available metadata.
    
    Args:
        file_path: Path to the file to analyze
        
    Returns:
        Dictionary containing extracted metadata
    """
    analyzer = FileAnalyzer()
    return analyzer.analyze_file(file_path, trust_extension=True)


def analyze_upload_file(file_upload) -> Dict[str, Any]:
    """
    Analyze an uploaded file from a form submission.
    
    Args:
        file_upload: FileStorage object from Flask/Werkzeug
        
    Returns:
        Dictionary containing extracted metadata
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_upload.filename)[1]) as tmp_file:
        file_upload.save(tmp_file.name)
        tmp_file.flush()
        
        try:
            analyzer = FileAnalyzer()
            metadata = analyzer.analyze_file(tmp_file.name, trust_extension=True)
            metadata['original_filename'] = file_upload.filename
            return metadata
            
        finally:
            try:
                os.unlink(tmp_file.name)
            except Exception:
                pass
