# Azure Direct Upload - Implementación Completa

## Solución al Problema de Timeout

El archivo se sube **directamente a Azure Blob Storage** desde el navegador, sin pasar por el backend de CKAN. Esto evita completamente los timeouts del backend.

## Flujo Completo

### Recursos NUEVOS (sin ID)

```
Usuario selecciona archivo
    ↓
JavaScript: Solicita SAS URL para ubicación temporal
    ↓
Backend: Genera URL con permisos de escritura → temp/uuid/filename
    ↓
JavaScript: Upload directo a Azure (PUT con XHR)
    ↓
Progreso en tiempo real 0% → 100%
    ↓
Upload completo, botón "Save" habilitado
    ↓
Usuario hace click en "Save"
    ↓
JavaScript: Envía azure_blob_path (sin archivo)
    ↓
Backend before_create: Procesa blob_path
    ↓
CKAN: Crea recurso (genera ID)
    ↓
Backend after_create: Mueve blob de temp → resources/resource_id/filename
    ↓
✅ Recurso creado con archivo en Azure
```

**Tiempo de espera en backend**: ~1 segundo (solo mueve blob dentro de Azure, no sube archivo)

### Recursos EXISTENTES (con ID)

```
Usuario selecciona archivo
    ↓
JavaScript: Solicita SAS URL para ubicación final
    ↓
Backend: Genera URL → resources/resource_id/filename
    ↓
JavaScript: Upload directo a Azure
    ↓
Progreso en tiempo real 0% → 100%
    ↓
Usuario hace Save → Solo actualiza metadatos
```

**Tiempo de espera en backend**: ~0 segundos (el archivo ya está en Azure)

## Componentes Implementados

### 1. Backend API (`upload/api.py`)

**Endpoint**: `/api/get-azure-upload-url`

**Funcionalidad**:
- Genera SAS URL con permisos de escritura
- Para recursos nuevos: Crea ubicación temporal `temp/uuid/filename`
- Para recursos existentes: Usa ubicación final `resources/id/filename`
- Token válido por 2 horas

### 2. Hooks de Plugin (`plugin.py`)

**`before_create()`**:
- Intercepta creación de recursos
- Si detecta `azure_blob_path`, configura el recurso para usar ese blob
- Marca el recurso con `_azure_blob_uploaded` y `_azure_temp_path`

**`after_create()`**:
- Si encuentra `_azure_blob_uploaded`, mueve el blob de temp a final
- Usa Azure copy dentro del mismo container (muy rápido)
- Elimina el blob temporal

**`_move_azure_blob_to_final_location()`**:
- Copia blob de `temp/uuid/filename` a `resources/id/filename`
- Espera hasta 30 segundos (normalmente es instantáneo)
- Elimina el blob temporal

### 3. JavaScript Frontend (`multipart_module.html`)

**`simulateAzureDirectUpload()`**:
- Inicia upload para recursos nuevos y existentes
- Solicita SAS URL (con o sin resource_id)
- Llama a `uploadFileToAzure()`

**`uploadFileToAzure()`**:
- Obtiene SAS URL del endpoint
- Sube archivo con XHR PUT
- Guarda `blobPath` en `window.cloudStorageUploads`
- Muestra progreso en tiempo real

**`setupFormSubmitHandler()`**:
- Intercepta submit del formulario
- Si hay upload completado, agrega campos hidden:
  - `azure_blob_path`: Ruta del blob en Azure
  - `azure_upload`: Flag indicando upload directo
- Limpia el input de archivo para no subirlo de nuevo

**`uploadToAzure()`**:
- Maneja el upload real con XMLHttpRequest
- PUT request con headers de Azure
- Tracking de progreso con eventos

## Ventajas de Esta Solución

1. **Sin Timeouts**: El archivo nunca pasa por el backend de CKAN
2. **Rápido**: 
   - Nuevos: ~1s en backend (solo mueve blob)
   - Existentes: ~0s en backend (ya está subido)
3. **Escalable**: Archivos de cualquier tamaño
4. **Progreso Real**: Usuario ve el progreso del upload
5. **Seguro**: SAS tokens temporales con permisos limitados
6. **Confiable**: Si falla, el blob temporal se puede limpiar después

## Archivos Modificados

1. `/ckanext/schemingdcat/upload/api.py`
   - Nuevo endpoint `get_azure_upload_url_endpoint()`
   - Genera SAS URLs para temp y final locations

2. `/ckanext/schemingdcat/blueprint.py`
   - Registro del endpoint `/api/get-azure-upload-url`

3. `/ckanext/schemingdcat/plugin.py`
   - `before_create()`: Procesa azure_blob_path
   - `after_create()`: Mueve blob de temp a final
   - `_move_azure_blob_to_final_location()`: Lógica de movimiento

4. `/ckanext/schemingdcat/templates/cloudstorage/snippets/multipart_module.html`
   - `simulateAzureDirectUpload()`: Upload inmediato
   - `uploadFileToAzure()`: Lógica de upload
   - `setupFormSubmitHandler()`: Intercepta submit
   - `uploadToAzure()`: XHR upload

5. `/ckanext/schemingdcat/templates/schemingdcat/upload_snippets/upload_script.html`
   - Fix selector URL (no depende de Jinja2)

## Configuración Requerida

```ini
# CKAN configuration file
ckanext.cloudstorage.driver = AZURE_BLOBS
ckanext.cloudstorage.azure_connection_string = DefaultEndpointsProtocol=https;AccountName=...
ckanext.cloudstorage.azure_container_name = resources
ckanext.cloudstorage.azure_direct_upload = true
ckanext.cloudstorage.use_enhanced_upload = true
```

## Testing

### Recurso Nuevo:
1. Crear dataset
2. Agregar recurso
3. Seleccionar archivo
4. Ver: "Uploading to Azure... X%"
5. Ver: "Upload completed successfully!"
6. Click "Save"
7. Recurso creado en ~1 segundo

### Recurso Existente:
1. Editar recurso
2. Seleccionar archivo
3. Ver progreso en tiempo real
4. Click "Save"
5. Actualizado inmediatamente

## Logs

**Frontend (Consola del Navegador)**:
```
[schemingdcat-cloudstorage] Starting Azure Direct Upload
[schemingdcat-cloudstorage] Uploading NEW resource to Azure (temp location)
[schemingdcat-cloudstorage] Got Azure upload URL, starting upload...
[schemingdcat-cloudstorage] Blob path: temp/xxx-xxx/file.csv
[schemingdcat-cloudstorage] Upload completed in 2.3 seconds
```

**Backend (CKAN Log)**:
```
🔷 [AZURE UPLOAD] Processing Azure blob for new resource: temp/xxx/file.csv
✅ [AZURE UPLOAD] Configured resource to use Azure blob: file.csv
🔷 [AZURE UPLOAD] Moving blob from temp/xxx/file.csv to resources/yyy/file.csv
✅ [AZURE UPLOAD] Successfully moved blob to final location
```

## Limpieza de Blobs Temporales

Los blobs temporales se eliminan automáticamente cuando se mueven a la ubicación final. Si por alguna razón falla el proceso:

1. El blob queda en `temp/uuid/filename`
2. Puede crear un cron job para limpiar blobs temporales antiguos (>24 horas)
3. Script de ejemplo:

```python
# cleanup_temp_blobs.py
from azure.storage.blob import BlobServiceClient
from datetime import datetime, timedelta

connection_string = "..."
container_name = "resources"

client = BlobServiceClient.from_connection_string(connection_string)
container = client.get_container_client(container_name)

cutoff = datetime.now() - timedelta(hours=24)

for blob in container.list_blobs(name_starts_with="temp/"):
    if blob.last_modified < cutoff:
        container.delete_blob(blob.name)
        print(f"Deleted temp blob: {blob.name}")
```

## Resumen

Esta implementación elimina completamente el problema de timeouts al subir archivos grandes. El backend de CKAN nunca maneja el archivo real, solo metadatos y una operación de copia rápida dentro de Azure.

- **Recursos nuevos**: Upload directo + movimiento en Azure (~1s backend)
- **Recursos existentes**: Upload directo sin intervención del backend (~0s backend)
- **Sin límite de tamaño**: El navegador sube directamente a Azure
- **Progreso real**: El usuario ve el progreso del upload
