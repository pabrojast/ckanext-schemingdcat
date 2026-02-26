# Copilot Instructions for ckanext-schemingdcat

## Project Overview

ckanext-schemingdcat is a CKAN extension that enhances metadata management for Linked Open Data (LOD) and INSPIRE standards. It extends ckanext-scheming with DCAT vocabulary support, custom harvesters, and comprehensive metadata schemas for European geospatial data portals.

**Key dependencies**: CKAN 2.9+, ckanext-scheming (release-3.0.0), mjanez/ckanext-dcat (1.2.0-geodcatap), ckanext-spatial (v2.1.1), ckanext-harvest (v1.5.6), ckanext-fluent (for multilingual fields).

## Build, Test, and Lint Commands

```bash
# Run all tests
pytest --ckan-ini=test.ini ckanext/schemingdcat/tests

# Run a single test file
pytest --ckan-ini=test.ini ckanext/schemingdcat/tests/test_plugin.py

# Run a single test by name
pytest --ckan-ini=test.ini ckanext/schemingdcat/tests/test_plugin.py -k "test_name"

# Lint (runs on every push/PR via CI)
flake8 --count --statistics --show-source --max-line-length=127

# Syntax errors only
flake8 . --count --select=E901,E999,F821,F822,F823 --show-source --statistics

# Translation workflow
python setup.py extract_messages
python setup.py update_catalog
python setup.py compile_catalog
```

## Architecture

### Plugin System

Four CKAN plugins registered in `setup.py` entry points:

- **`SchemingDCATPlugin`** (`plugin.py`): Core plugin. Implements IConfigurer, ITemplateHelpers, IFacets, IPackageController, ITranslation, IValidators, IBlueprint, IClick, IMiddleware. Mixes in `Faceted` (from `faceted.py`) and `PackageController` (from `package_controller.py`).
- **`SchemingDCATDatasetsPlugin`**: Extends `SchemingDatasetsPlugin` from ckanext-scheming for datasets.
- **`SchemingDCATGroupsPlugin`**: Extends `SchemingGroupsPlugin` for groups.
- **`SchemingDCATOrganizationsPlugin`**: Extends `SchemingOrganizationsPlugin` for organizations.

### Schema System

Schemas live in `ckanext/schemingdcat/schemas/`, organized by standard:
- `dcat/`, `dcatap/`, `geodcatap/`, `geodcatap_es/`, `unesco/`

Dataset schemas are **YAML**, group/organization schemas are **JSON**. Schemas follow scheming v2 format with custom extensions: `schema_form_groups` for UI grouping, `form_languages` for multilingual support, and custom presets in `*_presets.json`. Codelists (controlled vocabularies) are in `codelists/`.

### Harvester System

All harvesters extend `SchemingDCATHarvester` (in `harvesters/base.py`), which itself extends ckanext-harvest's `HarvesterBase`. The `ISchemingDCATHarvester` interface (`interfaces.py`) provides lifecycle hooks: `before_download`, `after_download`, `before_cleaning`, `after_cleaning`, `after_parsing`, `get_package_dict`, `before_create`/`after_create`, `before_update`/`after_update`.

Harvester types registered as entry points:
- `schemingdcat_ckan_harvester` — remote CKAN instances with schema mapping
- `schemingdcat_xls_harvester` — Excel/Google Sheets
- `schemingdcat_ows_harvester` — OGC Web Services

Field mapping between remote and local schemas uses `lib/field_mapping.py`. Default metadata config and format rules are centralized in `config.py` (`OGC2CKAN_HARVESTER_MD_CONFIG`, `OGC2CKAN_MD_FORMATS`, `CUSTOM_FORMAT_RULES`).

### Frontend

- **Templates**: Jinja2 templates in `templates/`, extending CKAN base. Custom form snippets in `templates/schemingdcat/form_snippets/`, display snippets in `templates/schemingdcat/display_snippets/`.
- **Assets**: JS modules and CSS in `assets/`, managed via `webassets.yml`.
- **Blueprints**: Flask routes in `blueprint.py` (endpoints page, metadata templates, API proxy). Additional views in `views.py`.

### Key Modules

| Module | Purpose |
|---|---|
| `config.py` | All configuration constants, defaults, and harvester metadata templates |
| `helpers.py` | Template helpers registered via ITemplateHelpers (dict `all_helpers`) |
| `validators.py` | Custom validators registered via IValidators (dict `all_validators`) |
| `utils.py` | Shared utilities: facets dict caching, file hashing, JSON parsing |
| `faceted.py` | Faceted search logic mixed into the main plugin |
| `package_controller.py` | IPackageController hooks mixed into the main plugin |
| `spatial_extent.py` | Spatial extent extraction from uploaded resources |
| `upload/` | File upload handling: analyzers, extractors, handlers, API |
| `lib/doi_resolver.py` | DOI metadata resolution |
| `rate_limiter.py` | Rate limiting for blueprint endpoints |

## Key Conventions

### Helper and Validator Registration

Helpers and validators use a module-level dict pattern. Each function decorated or added to `all_helpers` / `all_validators` is auto-registered with CKAN:

```python
# In helpers.py
all_helpers = {}
# Functions are added to all_helpers dict, then returned by get_helpers()

# In validators.py
all_validators = {}
# Same pattern for get_validators()
```

### Configuration Pattern

Runtime config is initialized in `utils.init_config()`, called during plugin startup. Config values from `ckan.ini` are read into `sdct_config` module-level variables. Reference config constants via `ckanext.schemingdcat.config` (imported as `sdct_config`).

### Multilingual Fields

Uses ckanext-fluent for multilingual text. Schema fields use `fluent_text` preset. Validators from `ckanext.fluent.validators` handle language-suffixed fields (e.g., `title_en`, `title_es`). The `form_languages` and `required_language` keys in schema YAML control which languages appear in forms.

### Harvester Field Mapping

Remote-to-local field mapping uses an `extras_` prefix convention (configurable via `field_mapping_extras_prefix` in config). The `FieldMappingValidator` in `lib/field_mapping.py` validates and applies these mappings.

### Adding New Schema Fields

1. Define the field in the appropriate schema YAML/JSON file
2. Add a form snippet in `templates/schemingdcat/form_snippets/` if custom input is needed
3. Add a display snippet in `templates/schemingdcat/display_snippets/` if custom rendering is needed
4. Add validators in `validators.py` and register in `all_validators` if custom validation is needed
5. Add translation strings to `i18n/` catalogs

### Creating Custom Harvesters

1. Extend `SchemingDCATHarvester` from `harvesters/base.py`
2. Implement `info()`, `gather_stage()`, `import_stage()`
3. Register as an entry point in `setup.py` under `[ckan.plugins]`
4. Use `ISchemingDCATHarvester` interface hooks for extensibility
