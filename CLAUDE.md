# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ckanext-schemingdcat is a CKAN extension that enhances metadata management for Linked Open Data (LOD) and INSPIRE standards. It extends ckanext-scheming with DCAT vocabularies support and provides custom harvesters, modern UI, and comprehensive metadata schemas.

## Key Dependencies

- CKAN 2.9+
- ckanext-scheming (release-3.0.0)
- mjanez/ckanext-dcat (1.2.0-geodcatap)
- ckanext-spatial (v2.1.1)
- ckanext-harvest (v1.5.6)

## Common Commands

### Testing
```bash
# Run all tests
pytest --ckan-ini=test.ini ckanext/schemingdcat/tests

# Run specific test file
pytest --ckan-ini=test.ini ckanext/schemingdcat/tests/test_plugin.py
```

### Linting
```bash
# Run flake8 linting
flake8 --count --statistics --show-source --max-line-length=127

# Check for syntax errors only
flake8 . --count --select=E901,E999,F821,F822,F823 --show-source --statistics
```

### Translation Management
```bash
# Extract translatable strings
python setup.py extract_messages

# Update translation catalogs
python setup.py update_catalog

# Compile translations
python setup.py compile_catalog
```

### CLI Commands
```bash
# Create INSPIRE theme vocabulary
ckan schemingdcat create-inspire-tags -l en

# Create DCAT theme vocabularies
ckan schemingdcat create-dcat-tags -l en

# Create ISO 19115 topic vocabulary
ckan schemingdcat create-iso-topic-tags -l en

# Delete vocabularies (if needed)
ckan schemingdcat delete-inspire-tags
ckan schemingdcat delete-dcat-tags
ckan schemingdcat delete-iso-topic-tags
```

### Harvesting
```bash
# Run harvest in production (with queue)
ckan harvester run

# Test harvester without queue (development)
ckan harvester run-test {source-id/name}
```

## Architecture Overview

### Plugin System
The extension uses CKAN's plugin architecture with four main plugins:
- **SchemingDCATPlugin**: Core functionality, implements IConfigurer, ITemplateHelpers, IFacets, IPackageController, ITranslation, IValidators, IBlueprint, IClick
- **SchemingDCATDatasetsPlugin**: Extends scheming for datasets
- **SchemingDCATGroupsPlugin**: Extends scheming for groups  
- **SchemingDCATOrganizationsPlugin**: Extends scheming for organizations

### Schema Organization
Schemas are organized by standard in `/ckanext/schemingdcat/schemas/`:
- `dcat/`: Basic DCAT schemas
- `dcatap/`: DCAT-AP (EU) schemas
- `geodcatap/`: GeoDCAT-AP schemas
- `geodcatap_es/`: Spanish GeoDCAT-AP schemas

Dataset schemas use YAML format, while group/organization schemas use JSON.

### Harvester System
Custom harvesters in `/ckanext/schemingdcat/harvesters/`:
- **base.py**: Abstract base class with common harvesting logic
- **ckan.py**: Harvests from remote CKAN instances with schema mapping
- **csw.py**: Harvests from CSW (Catalog Service for Web) endpoints
- **xls.py**: Harvests from Excel/Google Sheets
- **xml.py**: Harvests from XML/ISO 19139 metadata
- **ows.py**: Harvests from OGC Web Services

### Frontend Structure
- **Templates**: Custom Jinja2 templates extending CKAN base in `/templates/`
- **Assets**: JavaScript modules and CSS in `/assets/`
- **Form snippets**: Reusable form components in `/templates/schemingdcat/form_snippets/`
- **Display snippets**: Custom field renderers in `/templates/schemingdcat/display_snippets/`

### Key Helper Functions
Located in `helpers.py`, providing:
- Schema retrieval and manipulation
- Field rendering and validation
- Metadata format conversions
- UI component helpers
- Translation utilities

### Configuration
Main configuration handled through:
- `config.py`: Configuration constants and defaults
- `plugin.py`: Plugin initialization and interface implementations
- Schema files: Field definitions and validation rules

## Development Guidelines

### Adding New Fields
1. Define field in appropriate schema YAML/JSON file
2. Add form snippet if custom input needed
3. Add display snippet if custom output needed
4. Update validators if custom validation required
5. Add translations to i18n files

### Creating Custom Harvesters
1. Extend `SchemingDCATHarvester` base class
2. Implement required methods: `info()`, `gather_stage()`, `import_stage()`
3. Add field mapping configuration support
4. Register harvester in setup.py entry points

### Schema Customization
- Use presets for common field patterns
- Support multilingual fields with fluent text
- Include help text and examples
- Define field groups for better UX
- Set proper validators and output validators

### Testing Approach
- Unit tests for validators and helpers
- Integration tests for harvesters
- Use test fixtures for schema validation
- Mock external services in tests

# Documentación de Claude

Este archivo documenta los cambios realizados por Claude en el proyecto ckanext-schemingdcat.

## Sistema de Subida Multi-Archivo ✅

### Problema resuelto
Se intentó hacer un sistema de subida multi archivos pero no funcionaba porque faltaba el botón "Añadir recurso" que el módulo JavaScript necesitaba para crear nuevos recursos dinámicamente.

### Solución implementada

#### 1. Botón "Añadir recurso" añadido
- **Archivo modificado**: `ckanext/schemingdcat/templates/schemingdcat/package/snippets/resource_form.html`
- **Cambio**: Añadido botón con todas las clases CSS que el módulo multi-upload busca
- **Funcionalidad**: Permite crear nuevos recursos manualmente o automáticamente via multi-upload

#### 2. Módulo JavaScript mejorado
- **Archivo modificado**: `ckanext/schemingdcat/assets/js/modules/schemingdcat-multi-resource-upload.js`
- **Mejoras implementadas**:
  - ✅ Mejor detección del botón "Añadir recurso"
  - ✅ Soporte para drag & drop múltiple
  - ✅ Feedback visual durante el procesamiento
  - ✅ Barra de progreso para múltiples archivos
  - ✅ Auto-fill mejorado de campos (nombre, formato, fecha, descripción)
  - ✅ Gestión de errores y timeouts
  - ✅ Mensajes de éxito/error
  - ✅ Logging detallado para debugging

#### 3. Estilos CSS añadidos
- **Archivo modificado**: `ckanext/schemingdcat/assets/css/schemingdcat.css`
- **Estilos nuevos**:
  - ✅ Zona de drag & drop visual para múltiples archivos
  - ✅ Feedback de progreso con animaciones
  - ✅ Estados visuales (procesando, éxito, error)
  - ✅ Indicadores de múltiples archivos
  - ✅ Responsive design para móviles
  - ✅ Transiciones suaves y efectos hover

#### 4. Plantilla de upload mejorada
- **Archivo modificado**: `ckanext/schemingdcat/templates/schemingdcat/form_snippets/upload.html`
- **Mejoras**:
  - ✅ Soporte para atributo `multiple` en input file
  - ✅ Detección mejorada de drag & drop múltiple
  - ✅ Clases CSS para estados visuales
  - ✅ Contador de archivos múltiples
  - ✅ Mensajes informativos para el usuario

#### 5. Traducciones en español
- **Archivo modificado**: `ckanext/schemingdcat/i18n/es/LC_MESSAGES/ckanext-schemingdcat.po`
- **Traducciones añadidas**:
  - "Add Another Resource" → "Añadir Otro Recurso"
  - "Drag and drop files here" → "Arrastra y suelta archivos aquí"
  - "Browse Files" → "Examinar Archivos"
  - Y otras más...

### Cómo usar el sistema multi-upload

#### Método 1: Selección múltiple
1. Ir a crear/editar un dataset
2. En la página "Add data", hacer clic en el campo de subida de archivos
3. Seleccionar múltiples archivos con Ctrl+Click (Windows/Linux) o Cmd+Click (Mac)
4. El sistema automáticamente creará un recurso para cada archivo

#### Método 2: Drag & Drop
1. Ir a crear/editar un dataset
2. En la página "Add data", arrastrar múltiples archivos a la zona de subida
3. Los archivos se procesarán automáticamente

#### Método 3: Botón manual
1. Usar el botón "Añadir Otro Recurso" para crear recursos adicionales manualmente
2. Cada clic crea un nuevo formulario de recurso

### Características del auto-fill
- **Nombre**: Se extrae del nombre del archivo (sin extensión)
- **Formato**: Se detecta automáticamente según la extensión
- **Fecha de creación**: Se rellena con la fecha actual
- **Descripción**: Se genera automáticamente con nombre y tamaño del archivo

### Feedback visual
- **Barra de progreso**: Muestra el progreso de subida múltiple
- **Contador de archivos**: Indica cuántos archivos se están procesando  
- **Estados visuales**: Diferentes colores para procesando/éxito/error
- **Mensajes informativos**: Guían al usuario durante el proceso

### Compatibilidad
- ✅ Funciona con el sistema de upload existente
- ✅ Compatible con CloudStorage si está habilitado
- ✅ Responsive en dispositivos móviles
- ✅ Funciona en todos los navegadores modernos
- ✅ Fallback graceful si DataTransfer no está soportado

### Logging y debugging
El sistema incluye logging detallado en la consola del navegador:
```javascript
[schemingdcat-multi-upload] Inicializando módulo de subida múltiple
[schemingdcat-multi-upload] Procesando 3 archivos
[schemingdcat-multi-upload] Recurso añadido exitosamente: archivo1.csv
```

### Estructura de archivos modificados
```
ckanext/schemingdcat/
├── templates/schemingdcat/package/snippets/resource_form.html    [MODIFICADO]
├── templates/schemingdcat/form_snippets/upload.html              [MODIFICADO]
├── assets/js/modules/schemingdcat-multi-resource-upload.js       [MEJORADO]
├── assets/css/schemingdcat.css                                   [AÑADIDOS ESTILOS]
└── i18n/es/LC_MESSAGES/ckanext-schemingdcat.po                  [AÑADIDAS TRADUCCIONES]
```

### Resultado final
✅ Sistema de subida multi-archivo completamente funcional  
✅ Interfaz visual moderna y responsive  
✅ Feedback en tiempo real para el usuario  
✅ Auto-fill inteligente de campos  
✅ Compatible con sistemas existentes  
✅ Documentado y traducido al español  

**El sistema multi-upload ahora funciona perfectamente y es muy fácil de usar.**