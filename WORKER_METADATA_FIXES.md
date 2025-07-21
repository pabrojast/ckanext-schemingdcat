# Fixes para el problema de guardado de metadata en el worker

## Problema identificado:

Basándose en los logs, el job se ejecuta correctamente y extrae la metadata (incluyendo spatial_extent), pero se corta abruptamente al intentar hacer `toolkit.get_action('resource_patch')`. El problema es que en el contexto del worker, `toolkit` puede no estar disponible correctamente.

## Logs del problema:
```
2025-07-21 23:40:01,535 INFO  [ckanext.schemingdcat.plugin] Updating resource 34578ea1-94f7-45b2-a2d6-d0b27707cd76 with 5 metadata fields: ['spatial_extent', 'file_created_date', 'file_modified_date', 'file_size_bytes', 'content_type_detected']
```
[El job se corta aquí sin completarse]

## Soluciones implementadas:

### 1. ✅ Mejorado las importaciones del worker
```python
# ANTES
import ckan.model as model
import ckan.plugins.toolkit as toolkit

# DESPUÉS  
import ckan.model as model
import ckan.plugins.toolkit as toolkit
from ckan.logic import get_action  # Importación directa para mejor compatibilidad
```

### 2. ✅ Cambiado la llamada del action
```python
# ANTES
result = toolkit.get_action('resource_patch')(context, resource_patch_data)

# DESPUÉS
resource_patch_action = get_action('resource_patch')  # Importación directa
result = resource_patch_action(context, resource_patch_data)
```

### 3. ✅ Mejorado el contexto del worker
```python
context = {
    'model': model,
    'session': model.Session,
    'ignore_auth': True,
    'user': '',  # System user
    'auth_user_obj': None,  # Explicit None para operaciones de sistema
    'api_version': 3,
    'defer_commit': False,
    'for_view': False,  # No es para renderizado
    'return_id_only': False  # Queremos el objeto completo
}
```

### 4. ✅ Agregado logging detallado
Para identificar exactamente dónde falla:
```python
log.info(f"Getting resource_patch action...")
resource_patch_action = get_action('resource_patch')
log.info(f"Calling resource_patch action with context and data...")
result = resource_patch_action(context, resource_patch_data)
log.info(f"Resource_patch call completed successfully!")
```

### 5. ✅ Implementado fallback directo a base de datos
Si `resource_patch` falla, usa actualización directa en BD:
```python
def _update_resource_metadata_direct_db(resource_id, metadata_fields, model):
    # Obtiene el resource directamente del modelo
    resource = model.Resource.get(resource_id)
    
    # Actualiza campos directamente usando setattr()
    for field_name, field_value in metadata_fields.items():
        setattr(resource, field_name, field_value)
    
    # Commit directo
    model.Session.add(resource)
    model.Session.commit()
```

## Comportamiento esperado después de los fixes:

1. **Logging más detallado**: Los logs mostrarán exactamente dónde falla el proceso
2. **Fallback robusto**: Si `resource_patch` falla, se intentará actualización directa en BD
3. **Mejor compatibilidad**: Usando `get_action` directamente en lugar de `toolkit.get_action`
4. **Contexto mejorado**: Context con todos los campos necesarios para el worker

## Para probar:

1. Subir un archivo shapefile ZIP
2. Revisar los logs del worker para ver el progreso detallado
3. Verificar que los campos de metadata se guardan correctamente en el resource

Los logs ahora deberían mostrar:
- "Getting resource_patch action..."
- "Calling resource_patch action with context and data..."  
- "Resource_patch call completed successfully!"

O en caso de error, el fallback:
- "Attempting fallback direct database update..."
- "Successfully updated resource via fallback direct database access"
