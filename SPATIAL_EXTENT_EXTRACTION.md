# Extracción Automática de Extensión Espacial

Esta funcionalidad permite extraer automáticamente la extensión espacial (bounding box) de archivos geoespaciales durante la carga de recursos en CKAN.

## Características

### Formatos Soportados
- **Shapefile** (`.shp`, `.zip` con shapefile)
- **GeoTIFF** (`.tif`, `.tiff`, `.geotiff`)
- **GeoJSON** (`.geojson`, `.json`)
- **KML** (`.kml`)
- **GeoPackage** (`.gpkg`)

### Funcionamiento

1. **Detección Automática**: Cuando se sube un archivo geoespacial a través del formulario web, el sistema detecta automáticamente el tipo de archivo.

2. **Extracción de Extent**: Se extrae la extensión espacial del archivo y se convierte al formato GeoJSON en coordenadas WGS84.

3. **Auto-llenado**: El campo `spatial_extent` se llena automáticamente con el extent extraído.

4. **Edición Manual**: El usuario puede modificar manualmente el extent si es necesario.

## Configuración del Schema

En el archivo `dataset.yaml`, el campo debe configurarse así:

```yaml
- field_name: spatial_extent
  label:
    en: Spatial extent (auto-extracted)
    es: Extensión espacial (auto-extraída)
    fr: Étendue spatiale (auto-extraite)
  display_property: dcat:spatialResolutionInMeters
  form_snippet: schemingdcat/form_snippets/spatial_extent.html
  display_snippet: schemingdcat/display_snippets/spatial_extent.html
  form_placeholder: '{"type": "Polygon", "coordinates": [[[-180, -90], [180, -90], [180, 90], [-180, 90], [-180, -90]]]}'
  help_text:
    en: 'This field will be automatically populated when uploading geospatial files. For direct files (SHP, TIF, GeoJSON, etc.) it fills immediately. For ZIP files (that may contain shapefiles), it fills after creating the dataset. Once generated, you can modify the spatial extent if needed.'
    es: 'Este campo se rellenará automáticamente al subir archivos geoespaciales. Para archivos directos (SHP, TIF, GeoJSON, etc.) se rellena inmediatamente. Para archivos ZIP (que pueden contener shapefiles), se rellena después de crear el dataset. Una vez generado, puede modificar la extensión espacial si es necesario.'
    fr: 'Ce champ sera automatiquement rempli lors du téléchargement de fichiers géospatiaux. Pour les fichiers directs (SHP, TIF, GeoJSON, etc.) il se remplit immédiatement. Pour les fichiers ZIP (qui peuvent contenir des shapefiles), il se remplit après la création du jeu de données. Une fois généré, vous pouvez modifier l''étendue spatiale si nécessaire.'
  help_allow_html: True
  form_group_id: spatial_info
```

## Dependencias

Para usar esta funcionalidad, se requieren las siguientes librerías de Python (opcionales):

```bash
pip install -r spatial-requirements.txt
```

Las dependencias incluyen:
- **Fiona**: Para leer archivos vectoriales (Shapefile, GeoJSON, KML, etc.)
- **Rasterio**: Para leer archivos raster (GeoTIFF)
- **PyProj**: Para transformaciones de coordenadas

## API Endpoint

La funcionalidad expone un endpoint dedicado:

```
POST /api/extract-spatial-extent
```

### Parámetros
- `file`: Archivo multipart/form-data

### Respuesta
```json
{
  "success": true,
  "error": null,
  "extent": {
    "type": "Polygon",
    "coordinates": [[[...], [...], [...], [...], [...]]]
  }
}
```

## Implementación Técnica

### Archivos Modificados

1. **`spatial_extent.py`**: Lógica principal de extracción
2. **`blueprint.py`**: Endpoint API para extracción
3. **`templates/schemingdcat/form_snippets/upload.html`**: JavaScript para auto-extracción
4. **`templates/schemingdcat/form_snippets/spatial_extent.html`**: Campo de formulario mejorado
5. **`helpers.py`**: Helpers para verificar disponibilidad

### Flujo de Trabajo

#### Para archivos directos (SHP, TIF, GeoJSON, etc.)
1. **Upload de Archivo**: El usuario selecciona un archivo geoespacial
2. **Detección**: JavaScript detecta que es un archivo espacial
3. **Extracción**: Se envía el archivo al endpoint `/api/extract-spatial-extent`
4. **Procesamiento**: El servidor extrae el extent usando las librerías apropiadas
5. **Auto-llenado**: El campo `spatial_extent` se llena automáticamente
6. **Feedback**: Se muestra un mensaje de éxito o error al usuario

#### Para archivos ZIP (que pueden contener shapefiles)
1. **Upload de Archivo**: El usuario selecciona un archivo ZIP
2. **Creación del Dataset**: El dataset y recursos se crean normalmente
3. **Procesamiento Post-Creación**: Automáticamente después de crear el dataset:
   - Se detecta que hay recursos ZIP con formato spatial
   - Se extrae la extensión espacial del archivo ya subido
   - Se actualiza el campo `spatial_extent` del dataset
4. **Resultado**: El dataset queda con la extensión espacial extraída

### Características de Seguridad

- **Solo Frontend**: La extracción solo funciona a través de la interfaz web
- **No afecta API**: No interfiere con las operaciones de API de CKAN
- **Degradación Elegante**: Si las librerías no están disponibles, el sistema funciona normalmente sin extracción
- **Archivos Temporales**: Los archivos se procesan usando archivos temporales que se eliminan automáticamente

## Uso

1. **Crear/Editar Dataset**: Ve al formulario de creación o edición de dataset
2. **Agregar Recurso**: Agrega un nuevo recurso
3. **Subir Archivo Geoespacial**: Selecciona un archivo SHP, TIF, GeoJSON, etc.
4. **Extracción Automática**: El campo `spatial_extent` se llenará automáticamente (si no hay datos manuales)
5. **Verificar/Editar**: Revisa el extent extraído y modifica si es necesario
6. **Guardar**: Guarda el dataset con el extent extraído

### Protección de Datos Manuales

**🛡️ El sistema respeta los datos manuales**: Si un usuario ya ha ingresado información en el campo `spatial_extent`, la extracción automática **NO se ejecutará** para evitar sobrescribir el trabajo manual.

**Casos protegidos:**
- ✅ Dataset existente con `spatial_extent` ya definido
- ✅ Usuario editando el campo `spatial_extent` en el formulario
- ✅ Datos manuales guardados en la sesión del usuario
- ✅ Llamadas API que incluyen `spatial_extent` predefinido
- ✅ Scripts que pasan datos manuales al crear/actualizar datasets

**Casos donde se permite extracción automática:**
- ⚪ Datasets nuevos sin `spatial_extent`
- ⚪ Campo `spatial_extent` vacío o con solo espacios en blanco
- ⚪ Usuario no ha modificado manualmente el campo

## Mensajes del Sistema

El sistema proporciona feedback visual:
- ✅ **Éxito**: "Spatial extent extracted successfully from file."
- ⚠️ **Advertencia**: "Could not extract spatial extent from this file. You can manually enter the spatial extent if needed."
- ℹ️ **Info**: "Error extracting spatial extent. You can manually enter the spatial extent if needed."

## Compatibilidad

- **CKAN**: Compatible con CKAN 2.9+
- **Navegadores**: Requiere soporte para JavaScript ES6+
- **Formatos**: Soporta los formatos geoespaciales más comunes
- **CRS**: Convierte automáticamente a WGS84 (EPSG:4326)

## Troubleshooting

### Problemas Comunes

1. **No se extrae el extent**:
   - Verificar que las dependencias espaciales estén instaladas
   - Comprobar que el archivo sea un formato soportado
   - Revisar los logs del servidor

2. **Error en archivos ZIP**:
   - Asegurar que el ZIP contenga todos los archivos necesarios del Shapefile (.shp, .shx, .dbf)
   - Verificar que el ZIP no esté corrupto

3. **Problemas de CRS**:
   - El sistema automáticamente transforma a WGS84
   - Si hay problemas, PyProj debe estar instalado

### Logs

Los mensajes de debug se registran en el log de CKAN:
```python
logger = logging.getLogger(__name__)
```

Para activar logs detallados:
```ini
[logger_ckanext.schemingdcat.spatial_extent]
level = DEBUG
handlers = console
qualname = ckanext.schemingdcat.spatial_extent
```
