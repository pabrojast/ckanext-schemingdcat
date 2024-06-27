# Changelog

## [Unreleased](https://github.com/ckan/ckanext-dcat/compare/v3.2.1...HEAD)

## [v3.2.0](https://github.com/mjanez/ckanext-schemingdcat/compare/v3.2.1...v3.2.0) - 2024-05-17
* Enhance harvester, field mapping validation lib and harvest templates #81

## [v3.2.0](https://github.com/mjanez/ckanext-schemingdcat/compare/v3.1.0...v3.2.0) - 2024-05-17
* Improve schemas, theming, validators and remote sheets harvester by @mjanez in https://github.com/mjanez/ckanext-schemingdcat/pull/68
  - Improved the package_item template for better UI presentation.
  - Replaced status_show with package_list for CKAN API endpoint to enhance data retrieval.
  - Updated styles for better user interface experience.
  - Added schemingdcat_spatial_uri_validator to obtain spatial data from spatial URI.
  - Improved schemingdcat_harvester schema for better data harvesting.
  - Updated README for harvesters with more detailed instructions.
  - Updated form placeholders with correct abbreviations for better user understanding.
  - Refactored interfaces and improved docstrings for better code readability and maintainability.
  - Added data-icons for provinces and province images based on autonomies for better data representation.
  - Updated schemingdcat_spatial_uri_validator to handle missing spatial bbox, preventing potential errors.
  - Added temporal_start and temporal_end fields to DATE_FIELDS for better date range representation.
  - Improved spatial_uri form_snippet for better user interaction.
* Refactor contact_info and publisher_info snippets for improved readability and maintainability by @mjanez in https://github.com/mjanez/ckanext-schemingdcat/pull/69
* Fix schemingdcat_prettify_url_name by @mjanez in https://github.com/mjanez/ckanext-schemingdcat/pull/70
* Fix icon class for university publisher type by @mjanez in https://github.com/mjanez/ckanext-schemingdcat/pull/71
* Update sorted_choices to False for spatial_uri in geodcatap_es schema by @mjanez in https://github.com/mjanez/ckanext-schemingdcat/pull/72
* Comprehensive Update to Harvesters, CSS, and More by @mjanez in https://github.com/mjanez/ckanext-schemingdcat/pull/73
* Add metadata templates by @mjanez in https://github.com/mjanez/ckanext-schemingdcat/pull/74
* Update metadata template rendering in header and index templates by @mjanez in https://github.com/mjanez/ckanext-schemingdcat/pull/75
* Fix contact/publisher info snippets to avoid errors with emails by @mjanez in https://github.com/mjanez/ckanext-schemingdcat/pull/76

## [v3.1.0](https://github.com/mjanez/ckanext-schemingdcat/compare/v3.0.0...v3.1.0) - 2024-05-17

* Improve schemas by @mjanez in https://github.com/mjanez/ckanext-schemingdcat/pull/53
  * [Add high-value dataset category field](https://github.com/mjanez/ckanext-schemingdcat/commit/cf42f5bba6863432697222f6ab96e3a1f194252a)
  * [Improve created/modified dates](https://github.com/mjanez/ckanext-schemingdcat/commit/1ccaa1936f0449fccc04acf9dff736558ffe6518)
  * [Add fluent to all schemas](https://github.com/mjanez/ckanext-schemingdcat/commit/1ccaa1936f0449fccc04acf9dff736558ffe6518)
* Schema - Improve languages codelist https://github.com/mjanez/ckanext-schemingdcat/issues/35
* Improve schemas (dcat_type) by @mjanez in https://github.com/mjanez/ckanext-schemingdcat/pull/54
* Improve package_form and resource_form by @mjanez in https://github.com/mjanez/ckanext-schemingdcat/pull/55

## [v3.0.0](https://github.com/mjanez/ckanext-schemingdcat/compare/v2.1.0...v3.0.0) - 2024-04

* Feature/modern theme lod csw endpoints by @mjanez in https://github.com/mjanez/ckanext-scheming_dcat/pull/25
* Fix sd_config.endpoints by @mjanez in https://github.com/mjanez/ckanext-scheming_dcat/pull/26
* Feature/modern theme lod csw endpoints by @mjanez in https://github.com/mjanez/ckanext-scheming_dcat/pull/27
* Improve endpoints and README by @mjanez in https://github.com/mjanez/ckanext-scheming_dcat/pull/28
* Update develop by @mjanez in https://github.com/mjanez/ckanext-scheming_dcat/pull/31
* Fix ckanext-fluent with custom extensions by @mjanez in https://github.com/mjanez/ckanext-scheming_dcat/pull/32
* Update README blockquotes by @mjanez in https://github.com/mjanez/ckanext-scheming_dcat/pull/33
* Add scheming_dcat harvester plugins by @mjanez in https://github.com/mjanez/ckanext-scheming_dcat/pull/36
* Fix codelists folder by @mjanez in https://github.com/mjanez/ckanext-scheming_dcat/pull/38
* Fix groups and add default values to CKAN harvester by @mjanez in https://github.com/mjanez/ckanext-scheming_dcat/pull/39
* Fix scheming_dcat name to schemingdcat (PEP 503 y PEP 508) by @mjanez in https://github.com/mjanez/ckanext-schemingdcat/pull/42
* Update develop by @mjanez in https://github.com/mjanez/ckanext-schemingdcat/pull/43
* Fix map attribution acording to ckanext-spatial  by @mjanez in https://github.com/mjanez/ckanext-schemingdcat/pull/44
* Bug - Fix extras instance in SchemingDCATHarvester by @mjanez in https://github.com/mjanez/ckanext-schemingdcat/pull/45
* Fix bugs ckan harvester by @mjanez in https://github.com/mjanez/ckanext-schemingdcat/pull/46
* Fix resource updating for XLS harvester and old scheming_dcat prefixes by @mjanez in https://github.com/mjanez/ckanext-schemingdcat/pull/48
* Fix source_date_format issue in SchemingDCATHarvester by @mjanez in https://github.com/mjanez/ckanext-schemingdcat/pull/49
* Fix accented character handling in SchemingDCATHarvester by @mjanez in https://github.com/mjanez/ckanext-schemingdcat/pull/51
* Fix bugs with XLS, CKAN and facet searchs by @mjanez in https://github.com/mjanez/ckanext-schemingdcat/pull/52
