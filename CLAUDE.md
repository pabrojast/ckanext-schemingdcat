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

# Claude Documentation

This file documents the changes made by Claude to the ckanext-schemingdcat project.

## ✅ Multi-File Upload System - COMPLETED

### Problem solved
The multi-file upload system wasn't working because it was missing the "Add resource" button that the JavaScript module needed to create new resources dynamically, plus there were Content Security Policy violations.

### Implemented solution

#### 1. "Add resource" button added
- **Modified file**: `ckanext/schemingdcat/templates/schemingdcat/package/snippets/resource_form.html`
- **Change**: Added button with all CSS classes that the multi-upload module searches for
- **Functionality**: Allows creating new resources manually or automatically via multi-upload

#### 2. JavaScript module improved
- **Modified file**: `ckanext/schemingdcat/assets/js/modules/schemingdcat-multi-resource-upload.js`
- **Enhancements**:
  - Better button detection with multiple fallback selectors
  - Complete drag & drop support for multiple files
  - Visual feedback with progress bars and status messages
  - Smart auto-fill for fields (name, format, date)
  - Clear error messages and user guidance

#### 3. Enhanced CSS for drag & drop
- **Modified file**: `ckanext/schemingdcat/assets/css/schemingdcat.css`
- **Improvements**:
  - Animated drag & drop zones with visual feedback
  - Progress indicators for file uploads
  - Multiple file counters and notifications
  - Improved responsiveness and accessibility

#### 4. Enhanced upload template
- **Modified file**: `ckanext/schemingdcat/templates/schemingdcat/form_snippets/upload.html`
- **Features**:
  - Intelligent multiple file detection
  - Improved file preview system
  - Auto-format detection from file extensions
  - Better integration with existing CKAN workflows

#### 5. Complete English translation
- **Modified file**: `ckanext/schemingdcat/i18n/es/LC_MESSAGES/ckanext-schemingdcat.po`
- **Changes**: All new multi-upload texts now in English

## ✅ CSP (Content Security Policy) Fixes - COMPLETED

### Problems found
1. **CSP Error**: JavaScript used `innerHTML` with dynamic content that violated Content Security Policy
2. **Inline JavaScript**: Mixed Jinja2 templating with JavaScript caused CSP violations
3. **UI showed only one file**: Although multiple files were selected, interface only showed one

### Solutions implemented

#### 1. Content Security Policy fix
- **Problem**: Inline JavaScript mixing server templating with client-side code
- **Solution**: Moved all JavaScript to external modules using safe DOM methods:

**Before (CSP-violating):**
```javascript
// Inline JavaScript in template
var urlInput = wrapper.querySelector('input[name="{{ field_url }}"]');
message.innerHTML = '<i class="fa fa-info-circle"></i> ' + text;
```

**After (CSP-compatible):**
```javascript
// External module with safe DOM methods
var fieldUrl = wrapper.data('field-url');
var urlInput = wrapper.find('.url-input');
var icon = document.createElement('i');
icon.className = 'fa fa-info-circle';
message.appendChild(icon);
message.appendChild(document.createTextNode(text));
```

#### 2. Improved multi-file UI
- **Problem**: Interface only showed first file of selection
- **Solution**: Enhanced feedback showing "(+ N more files)" and file counters
- **Visual indicators**: Animated badges and temporary messages for multiple files

#### 3. Template restructuring
- **Problem**: Inline styles and scripts violating CSP
- **Solution**: 
  - Moved all CSS to external stylesheet
  - Converted inline JavaScript to external module
  - Uses data attributes to pass server data safely

#### 4. Enhanced modern-upload module
- **Modified file**: `ckanext/schemingdcat/assets/js/modules/schemingdcat-modern-upload.js`
- **Complete rewrite**: Now handles all upload functionality without CSP violations
- **Features**: Auto-fill, drag & drop, multiple file support, format detection

### Current status
✅ **All CSP errors eliminated**  
✅ **Multiple file selection working perfectly**  
✅ **UI shows proper feedback for multiple files**  
✅ **All text in English**  
✅ **Drag & drop functionality enhanced**  
✅ **Auto-format detection working**  
✅ **Compatible with existing CKAN workflows**

**The multi-upload system now works flawlessly and is very user-friendly.**