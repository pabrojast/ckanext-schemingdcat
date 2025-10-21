# Implementación de Upload Directo a Azure Blob Storage

## Problema Identificado

Cuando el usuario seleccionaba un archivo, veía el mensaje "Connecting to Azure Blob Storage..." y se quedaba esperando indefinidamente. Esto ocurría porque:

1. **Mensaje Engañoso**: El mensaje daba la impresión de que la carga estaba en progreso, cuando en realidad solo esperaba que el usuario hiciera click en "Save"
2. **Sin Upload Automático**: El archivo no se subía hasta que el usuario presionaba "Save", lo que podía causar timeouts en el backend
3. **Selector Problemático**: Había una referencia a variable Jinja2 que podría causar errores

## Solución Implementada

Se implementó un sistema de **upload directo a Azure Blob Storage** que sube el archivo automáticamente cuando el usuario lo selecciona.

### Cambios Realizados

#### 1. Nuevo Endpoint API (`upload/api.py`)
- **Función**: `get_azure_upload_url_endpoint()`
- **Ruta**: `/api/get-azure-upload-url`
- **Funcionalidad**: Genera una URL SAS (Shared Access Signature) de Azure con permisos de escritura para que el navegador pueda subir archivos directamente

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

**Función `simulateAzureDirectUpload()`**: Implementa el flujo completo de upload directo a Azure:

1. **Solicita URL SAS**: Llama al endpoint `/api/get-azure-upload-url` para obtener una URL temporal con permisos de escritura
2. **Upload Directo**: Sube el archivo directamente a Azure usando XMLHttpRequest con método PUT
3. **Progreso en Tiempo Real**: Actualiza la barra de progreso mientras se sube el archivo (0-100%)
4. **Desbloqueo de Botón**: Al terminar, desbloquea el botón "Save" para que el usuario guarde los metadatos

**Función `uploadToAzure()`**: Maneja el upload real a Azure:
- Usa XMLHttpRequest con método PUT
- Establece headers requeridos por Azure (`x-ms-blob-type: BlockBlob`)
- Rastrea progreso del upload en tiempo real
- Maneja errores de red y timeouts

#### 4. Corrección del Selector de URL (`upload_script.html`)
- Reemplazó selector que dependía de Jinja2 (`{{ field_url }}`) por selectores JavaScript genéricos más robustos
- Ahora busca el campo URL de forma dinámica sin depender de variables del template

### Flujo de Upload

```
Usuario selecciona archivo
    ↓
JavaScript: handleFileUpload()
    ↓
JavaScript: simulateAzureDirectUpload()
    ↓
[1] Solicita SAS URL → /api/get-azure-upload-url
    ↓
[2] Recibe URL con token temporal (válido 2 horas)
    ↓
[3] Upload directo a Azure con XHR PUT
    ↓
[4] Actualiza progreso 0% → 100%
    ↓
[5] Upload completo, desbloquea botón "Save"
    ↓
Usuario hace click en "Save"
    ↓
CKAN guarda metadatos del recurso
```

### Ventajas

1. **Sin Timeouts**: El archivo se sube directamente a Azure sin pasar por el backend de CKAN, evitando timeouts
2. **Progreso Real**: Muestra el progreso real del upload (no simulado)
3. **Mejor UX**: El usuario ve inmediatamente que la carga está ocurriendo
4. **Escalable**: No sobrecarga el servidor de CKAN con transferencias de archivos grandes
5. **Seguro**: Usa SAS tokens temporales (2 horas) con permisos solo de escritura

### Requisitos

- ckanext-cloudstorage configurado con Azure Blob Storage
- Configuración en CKAN:
  ```ini
  ckanext.cloudstorage.driver = AZURE_BLOBS
  ckanext.cloudstorage.azure_direct_upload = true
  ckanext.cloudstorage.use_enhanced_upload = true
  ```

### Comportamiento para Non-Azure Storage

Si Azure direct upload no está configurado, la función `simulateStandardUpload()` simplemente muestra "File ready. Click Save to upload" y el archivo se sube mediante el flujo normal de CKAN cuando el usuario hace click en Save.

### Archivos Modificados

1. `/ckanext/schemingdcat/upload/api.py` - Nuevo endpoint para SAS URLs
2. `/ckanext/schemingdcat/blueprint.py` - Registro del endpoint
3. `/ckanext/schemingdcat/templates/cloudstorage/snippets/multipart_module.html` - Lógica de upload directo
4. `/ckanext/schemingdcat/templates/schemingdcat/upload_snippets/upload_script.html` - Fix selector URL

### Testing

Para probar:
1. Configura Azure Blob Storage en CKAN
2. Activa `ckanext.cloudstorage.azure_direct_upload = true`
3. Crea o edita un recurso
4. Selecciona un archivo
5. Deberías ver:
   - "Requesting Azure upload URL..."
   - "Uploading to Azure Blob Storage... X%"
   - "Upload completed successfully!"
6. El botón "Save" se habilitará automáticamente
7. Haz click en "Save" para guardar los metadatos

### Logs para Debug

El sistema genera logs en la consola del navegador:
- `[schemingdcat-cloudstorage] Starting Azure Direct Upload`
- `[schemingdcat-cloudstorage] Got Azure upload URL, starting upload...`
- `[schemingdcat-cloudstorage] Upload completed in X.X seconds`

En caso de error:
- `[schemingdcat-cloudstorage] Upload error: [mensaje]`
