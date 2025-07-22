# Fix para el problema de limpieza de campos metadata

## 🔍 Problema identificado:

La función `_cleanup_empty_metadata_fields` se ejecutaba **ANTES** de que el job terminara de procesar la metadata, causando que los campos recién extraídos fueran marcados como "vacíos" y limpiados.

### Evidencia del problema:
```json
{
  "spatial_extent": "",
  "file_size_bytes": ["", "", "", ""],
  "data_fields": ["", "", ""],
  "spatial_crs": "",
  "geometry_type": ""
}
```

## ⚠️ Causa raíz:

**Secuencia problemática:**
1. Usuario sube archivo → `after_create` hook se dispara
2. `_cleanup_empty_metadata_fields()` se ejecuta (resource aún no tiene metadata)
3. Función marca campos como vacíos y los limpia
4. Job extrae metadata → actualiza resource con `resource_patch`
5. Job termina exitosamente PERO los campos ya fueron limpiados

## ✅ Solución implementada:

### 1. **Removido cleanup del hook `after_create`**
```python
# ANTES
try:
    # FIRST: Clean up any empty list fields that might have been created
    self._cleanup_empty_metadata_fields(context, resource)
    
    # THEN: Process spatial extent extraction  
    self._process_spatial_extent_extraction_for_resource(context, resource)

# DESPUÉS  
try:
    # FIRST: Process spatial extent extraction
    self._process_spatial_extent_extraction_for_resource(context, resource)
```

### 2. **Removido cleanup del hook `after_update`**
```python
# ANTES
try:
    # FIRST: Clean up any empty list fields that might have been created
    self._cleanup_empty_metadata_fields(context, resource)
    
    # THEN: Process spatial extent extraction
    self._process_spatial_extent_extraction_for_resource(context, resource)

# DESPUÉS
try:
    # FIRST: Process spatial extent extraction  
    self._process_spatial_extent_extraction_for_resource(context, resource)
```

### 3. **Agregado cleanup post-procesamiento en el job**
```python
result = resource_patch_action(context, resource_patch_data)
log.info(f"Resource_patch call completed successfully!")

# NOW: Clean up any empty metadata fields AFTER successful update
log.info(f"🧹 Cleaning up empty metadata fields after successful update")
try:
    _cleanup_empty_metadata_fields_post_processing(resource_id, model)
except Exception as cleanup_error:
    log.warning(f"Error in post-processing cleanup: {cleanup_error}")

return True
```

### 4. **Nueva función de limpieza post-procesamiento**
```python
def _cleanup_empty_metadata_fields_post_processing(resource_id, model):
    """
    Post-processing cleanup AFTER successful metadata extraction.
    Only clears truly empty fields, not fields with meaningful data.
    """
    # Solo limpia campos que están realmente vacíos DESPUÉS de la extracción
    # Trabaja directamente con la base de datos para mayor confiabilidad
```

## 🚀 Secuencia corregida:

**Nueva secuencia exitosa:**
1. Usuario sube archivo → `after_create` hook se dispara
2. Hook inicia procesamiento asíncrono (sin cleanup prematuro)
3. Job descarga y analiza archivo → extrae metadata
4. Job actualiza resource con `resource_patch` → SUCCESS
5. Job ejecuta limpieza post-procesamiento → Solo limpia campos realmente vacíos
6. Job termina → Metadata preservada correctamente

## 🧪 Comportamiento esperado:

Ahora los recursos deberían mostrar:
```json
{
  "spatial_extent": "{'type': 'Polygon', 'coordinates': [...]}",
  "file_size_bytes": 5829,
  "file_created_date": "2025-07-21",
  "content_type_detected": "application/zip",
  "spatial_crs": "EPSG:4326"
}
```

En lugar de:
```json
{
  "spatial_extent": "",
  "file_size_bytes": ["", "", "", ""],
  "spatial_crs": ""
}
```

## ✅ Resultado:
- ✅ Metadata se extrae correctamente
- ✅ Metadata se guarda en la base de datos  
- ✅ Limpieza solo ocurre DESPUÉS del procesamiento exitoso
- ✅ Solo se limpian campos realmente vacíos
- ✅ Campos con datos reales se preservan
