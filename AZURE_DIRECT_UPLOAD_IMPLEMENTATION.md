# Implementación de Upload Directo a Azure Blob Storage

## Problema Identificado

Cuando el usuario seleccionaba un archivo, veía el mensaje "Connecting to Azure Blob Storage..." y se quedaba esperando indefinidamente. Esto ocurría porque:

1. **Mensaje Engañoso**: El mensaje daba la impresión de que la carga estaba en progreso, cuando en realidad solo esperaba que el usuario hiciera click en "Save"
2. **Sin Upload Automático**: El archivo no se subía hasta que el usuario presionaba "Save", lo que podía causar timeouts en el backend
3. **Resource ID Missing**: Para recursos nuevos, no existía el ID del recurso, causando error "Resource ID not found"

## Solución Implementada

Se implementó un sistema de **upload directo a Azure Blob Storage** con diferente comportamiento según si es un recurso nuevo o existente.

### Flujo para Recursos NUEVOS

```
Usuario selecciona archivo
    ↓
Mensaje: "File ready. Click Save to upload to Azure"
    ↓
Usuario hace click en "Save"
    ↓
CKAN crea el recurso (genera ID)
    ↓
CloudStorage sube automáticamente a Azure
```

**Razón**: Para recursos nuevos, primero necesitamos que CKAN cree el recurso y genere un ID. Luego CloudStorage maneja el upload automáticamente.

### Flujo para Recursos EXISTENTES

```
Usuario selecciona archivo
    ↓
Solicita SAS URL → /api/get-azure-upload-url
    ↓
Upload directo a Azure con XHR PUT
    ↓
Progreso 0% → 100% en tiempo real
    ↓
Upload completo, desbloquea "Save"
    ↓
Usuario hace click en "Save" (solo actualiza metadatos)
```

**Razón**: Para recursos existentes, ya tenemos el ID, así que podemos subir directamente a Azure sin esperar.

### Cambios Realizados

#### 1. Nuevo Endpoint API (`upload/api.py`)
- **Función**: `get_azure_upload_url_endpoint()`
- **Ruta**: `/api/get-azure-upload-url`
- **Funcionalidad**: Genera una URL SAS (Shared Access Signature) de Azure con permisos de escritura

**Request**:
```json
{
  "resource_id": "xxx-xxx-xxx",
  "filename": "archivo.csv",
  "content_type": "text/csv"
}
```

**Response**:
```json
{
  "success": true,
  "upload_url": "https://storage.blob.core.windows.net/...",
  "blob_path": "resources/xxx/archivo.csv",
  "expires_at": "2025-10-21T20:00:00Z",
  "content_type": "text/csv"
}
```

#### 2. Registro del Endpoint (`blueprint.py`)
- Se agregó la ruta `/api/get-azure-upload-url` al blueprint de schemingdcat

#### 3. JavaScript de Upload Directo (`multipart_module.html`)

**Función `simulateAzureDirectUpload()`**: 
- Detecta si es recurso nuevo o existente
- Para nuevos: Muestra mensaje "ready" y permite submit normal
- Para existentes: Inicia upload directo a Azure

**Función `uploadFileToAzure()`**: 
- Obtiene SAS URL del backend
- Sube archivo a Azure con XHR
- Muestra progreso en tiempo real

**Función `uploadToAzure()`**: 
- Maneja el upload real a Azure
- PUT request con headers de Azure
- Tracking de progreso
- Manejo de errores

**Función `setupFormSubmitHandler()`**:
- Intercepta submit del formulario
- Para recursos nuevos con archivos pendientes, permite submit normal
- CKAN/CloudStorage se encarga del upload después de crear el recurso

#### 4. Corrección del Selector de URL (`upload_script.html`)
- Reemplazó selector que dependía de Jinja2 (`{{ field_url }}`) por selectores JavaScript genéricos

### Ventajas

1. **Sin Timeouts**: El archivo va directo a Azure sin pasar por el backend de CKAN
2. **Progreso Real**: Muestra progreso real del upload (no simulado) para recursos existentes
3. **Mejor UX**: 
   - Recursos nuevos: Mensaje claro que indica que debe hacer click en Save
   - Recursos existentes: Upload inmediato con progreso visual
4. **Escalable**: No sobrecarga el servidor con transferencias de archivos grandes
5. **Seguro**: Usa SAS tokens temporales (2 horas) con permisos solo de escritura

### Comportamiento Detallado

#### Recursos Nuevos
- Usuario selecciona archivo → Muestra "File ready. Click Save to upload to Azure"
- El botón Save NO se bloquea
- Usuario hace click en Save → Formulario se envía con archivo
- CKAN crea recurso → CloudStorage detecta el archivo y lo sube a Azure automáticamente
- Upload usa el mecanismo estándar de CloudStorage (multipart si es grande)

#### Recursos Existentes  
- Usuario selecciona archivo → "Requesting Azure upload URL..."
- Obtiene SAS URL → "Uploading to Azure Blob Storage... X%"
- Progreso en tiempo real 0-100%
- Upload completo → "Upload completed successfully!"
- Botón Save se habilita automáticamente
- Usuario hace click en Save → Solo actualiza metadatos

#### Sin Azure Direct Upload Configurado
- Comportamiento estándar: "File ready. Click Save to upload"
- Upload se hace mediante el flujo normal de CKAN

### Requisitos

- ckanext-cloudstorage configurado con Azure Blob Storage
- Configuración en CKAN:
  ```ini
  ckanext.cloudstorage.driver = AZURE_BLOBS
  ckanext.cloudstorage.azure_direct_upload = true
  ckanext.cloudstorage.use_enhanced_upload = true
  ckanext.cloudstorage.azure_connection_string = [your_connection_string]
  ckanext.cloudstorage.azure_container_name = [your_container]
  ```

### Archivos Modificados

1. `/ckanext/schemingdcat/upload/api.py` - Nuevo endpoint para SAS URLs
2. `/ckanext/schemingdcat/blueprint.py` - Registro del endpoint
3. `/ckanext/schemingdcat/templates/cloudstorage/snippets/multipart_module.html` - Lógica de upload directo
4. `/ckanext/schemingdcat/templates/schemingdcat/upload_snippets/upload_script.html` - Fix selector URL

### Testing

#### Probar con Recurso Nuevo:
1. Configura Azure Blob Storage en CKAN
2. Activa `ckanext.cloudstorage.azure_direct_upload = true`
3. Crea un nuevo dataset
4. Agrega un nuevo recurso
5. Selecciona un archivo
6. Deberías ver: "File ready. Click Save to upload to Azure"
7. Haz click en "Save"
8. CKAN creará el recurso y CloudStorage subirá el archivo a Azure

#### Probar con Recurso Existente:
1. Edita un recurso existente
2. Selecciona un archivo
3. Deberías ver:
   - "Requesting Azure upload URL..."
   - "Uploading to Azure Blob Storage... X%"
   - "Upload completed successfully!"
4. Haz click en "Save" para actualizar metadatos

### Logs para Debug

El sistema genera logs en la consola del navegador:

**Recursos nuevos**:
- `[schemingdcat-cloudstorage] Starting Azure Direct Upload`
- `[schemingdcat-cloudstorage] New resource - will upload when form is saved`

**Recursos existentes**:
- `[schemingdcat-cloudstorage] Uploading existing resource to Azure, ID: xxx`
- `[schemingdcat-cloudstorage] Got Azure upload URL, starting upload...`
- `[schemingdcat-cloudstorage] Upload completed in X.X seconds`

**Errores**:
- `[schemingdcat-cloudstorage] Upload error: [mensaje]`

### Notas Importantes

1. **Para recursos nuevos**, el upload directo a Azure NO ocurre inmediatamente al seleccionar el archivo, sino cuando se guarda el formulario. Esto es correcto porque necesitamos que CKAN genere el resource_id primero.

2. **CloudStorage se encarga del upload** para recursos nuevos usando su mecanismo estándar (que puede ser multipart para archivos grandes).

3. **Para recursos existentes**, el upload es inmediato y directo a Azure, evitando completamente el backend de CKAN.

4. Si el upload directo falla por cualquier razón, el sistema fallback al método estándar de CKAN.

