# Solución: Extracción de Extensión Espacial Post-Creación de RECURSOS

## Problema Identificado

El sistema estaba intentando extraer la extensión espacial de archivos ZIP **durante** la selección del archivo (antes de que se haya creado el dataset), causando errores del tipo:

```
2025-07-19 01:22:35,067 INFO  [ckanext.schemingdcat.spatial_extent] Cannot extract extent from file type: zip
2025-07-19 01:22:35,071 INFO  [ckan.config.middleware.flask_app]  400 /api/extract-spatial-extent render time 1.083 seconds
```

Además, había errores conceptuales en la implementación inicial:
- Usaba hooks de **datasets** en lugar de **recursos**
- No consideraba que los **ZIP se marcan con formato "SHP"** en el formulario

## Solución Implementada

### 1. Hook Post-Creación en IResourceController

**Archivo modificado:** `ckanext/schemingdcat/plugin.py`

Se implementaron nuevos métodos en la clase `SchemingDCATDatasetsPlugin` usando `IResourceController`:

- **`after_create()`**: Hook que se ejecuta después de crear un RECURSO
- **`after_update()`**: Hook que se ejecuta después de actualizar un RECURSO  
- **`_process_spatial_extent_extraction_for_resource()`**: Procesa la extracción para un recurso específico
- **`_is_potential_spatial_resource()`**: Identifica recursos espaciales (**CLAVE**: detecta formato "SHP")
- **`_extract_spatial_extent_from_resource()`**: Extrae la extensión espacial de un recurso
- **`_update_dataset_spatial_extent()`**: Actualiza el campo `spatial_extent` del dataset padre

### 2. Detección Correcta de Formatos

**IMPORTANTE**: Los archivos ZIP que contienen shapefiles se marcan con **formato "SHP"**, no "ZIP":

```python
def _is_potential_spatial_resource(self, resource):
    # CLAVE: Los ZIP se marcan como "SHP"
    resource_format = resource.get('format', '').lower()
    spatial_formats = ['shp', 'shapefile', 'zip', 'tif', 'tiff', 'geotiff', ...]
    
    # Un ZIP con shapefile tendrá format='SHP'
    if resource_format in spatial_formats:
        return True
```

### 3. Modificación del JavaScript Frontend

**Archivo modificado:** `ckanext/schemingdcat/templates/schemingdcat/form_snippets/upload.html`

Los archivos ZIP ya **no** se procesan inmediatamente durante la selección.

### 4. Limpieza del PackageController

**Archivo modificado:** `ckanext/schemingdcat/package_controller.py`

Se removió la implementación incorrecta que usaba hooks de datasets.

## Flujo de Funcionamiento CORREGIDO

### Para Archivos ZIP (que contienen shapefiles):

1. **Usuario sube archivo ZIP** y marca formato como "SHP"
2. **Se crea el recurso** normalmente
3. **Hook `after_create` de IResourceController se ejecuta:**
   - Detecta que es un recurso con formato "SHP" 
   - Verifica que el dataset padre no tenga extensión espacial
   - Extrae extensión espacial del archivo ya subido en cloud storage
   - Actualiza el campo `spatial_extent` del dataset padre
4. **Dataset queda con extensión espacial extraída**

### Para Otros Archivos Geoespaciales:

1. **Usuario selecciona archivo** (TIF, GeoJSON, etc.)
2. **Se extrae inmediatamente** la extensión espacial (flujo actual)
3. **Se crea el recurso** con la extensión ya disponible en el dataset

## Diferencias Clave vs Implementación Anterior

| Aspecto | ❌ Anterior (Incorrecto) | ✅ Actual (Correcto) |
|---------|-------------------------|----------------------|
| **Hook usado** | `IPackageController` (datasets) | `IResourceController` (recursos) |
| **Cuándo se ejecuta** | Al crear/actualizar dataset | Al crear/actualizar RECURSO |
| **Detección ZIP** | Buscaba formato "ZIP" | Detecta formato "SHP" |
| **Scope** | Procesa todos los recursos del dataset | Procesa recurso individual |

## Ventajas de la Solución Corregida

1. **✅ Soluciona el error 400**: Los archivos ZIP no se procesan antes de estar subidos
2. **✅ Enfoque correcto**: Usa hooks de recursos, no de datasets
3. **✅ Detección precisa**: Reconoce que ZIP se marca como "SHP"
4. **✅ Granular**: Procesa recursos individuales cuando se crean/actualizan
5. **✅ Automático**: No requiere intervención manual del usuario
6. **✅ Retrocompatible**: No rompe funcionalidad existente

## Archivos Modificados

1. `ckanext/schemingdcat/plugin.py` - Hook IResourceController (PRINCIPAL)
2. `ckanext/schemingdcat/package_controller.py` - Limpieza de código incorrecto
3. `ckanext/schemingdcat/templates/schemingdcat/form_snippets/upload.html` - JavaScript
4. `test_post_creation_spatial_extraction.py` - Script de pruebas actualizado

## Cómo Probar Correctamente

1. **Reiniciar servidor CKAN** para aplicar cambios
2. **Crear nuevo dataset** 
3. **Agregar recurso con archivo ZIP** que contenga shapefiles
4. **IMPORTANTE: Marcar formato como "SHP"** (no "ZIP")
5. **Guardar recurso** 
6. **Verificar** que el campo `spatial_extent` del dataset se llene automáticamente
7. **Revisar logs** para confirmar la extracción

## Logs Esperados (Corregidos)

```
INFO [ckanext.schemingdcat.plugin] Processing spatial resource resource-123 with format SHP
INFO [ckanext.schemingdcat.plugin] Attempting to extract spatial extent from resource: https://storage.azure.com/shapefile.zip (format: SHP)
INFO [ckanext.schemingdcat.spatial_extent] Processing resource: https://storage.azure.com/shapefile.zip (format: SHP)
INFO [ckanext.schemingdcat.plugin] Successfully extracted spatial extent from resource resource-123
INFO [ckanext.schemingdcat.plugin] Updated spatial_extent for dataset dataset-456
```

## Flujo Técnico Detallado

```
1. Usuario sube ZIP → Marca formato "SHP" → Guarda recurso
2. CKAN llama IResourceController.after_create()
3. Plugin detecta format='SHP' como spatial
4. Plugin extrae extent del archivo ya en storage
5. Plugin actualiza dataset padre con spatial_extent
6. ✅ Proceso completado
```

## Ejecutar Pruebas

```bash
python test_post_creation_spatial_extraction.py
```

Este script valida:
- Detección correcta de formato "SHP" para ZIP
- Hooks de IResourceController funcionando
- Lógica de extracción espacial
- Procesamiento de recursos individuales

---

**Resultado:** La extracción de extensión espacial ahora funciona correctamente usando **IResourceController** para procesar **recursos individuales** cuando se **crean o actualizan**, reconociendo que los **ZIP se marcan como formato "SHP"**. 