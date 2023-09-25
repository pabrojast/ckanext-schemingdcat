<h1 align="center">ckanext-scheming_dcat. LOD/INSPIRE metadata enhancement for ckanext-scheming</h1>
<p align="center">

<p align="center">
    <a href="#overview">Overview</a> •
    <a href="#installation">Installation</a> •
    <a href="#configuration">Configuration</a> •
    <a href="#schemas">Schemas</a> •
    <a href="#running-the-tests">Running the Tests</a>
</p>

## Overview
This CKAN extension provides functions and templates specifically designed to extend `ckanext-scheming` and includes DCAT enhancements to adapt CKAN Schema to [GeoDCAT-AP](./ckanext/scheming_dcat/schemas/geodcatap/geodcatap_dataset.yaml).

>**Warning**:<br>
> Requires [mjanez/ckanext-dcat](https://github.com/mjanez/ckanext-dcat), [ckan/ckanext-scheming](https://github.com/ckan/ckanext-scheming) and [ckan/ckanext-spatial](https://github.com/ckan/ckanext-spatial) to work properly.
>
> It is **recommended to use with:** [`ckan-docker`](https://github.com/mjanez/ckan-docker) deployment or only use [`ckan-pycsw`](https://github.com/mjanez/ckan-pycsw) to deploy a CSW Catalog.


Enhancements:
- Could use schemas for `ckanext-scheming` in the plugin like [CKAN GeoDCAT-AP schema](ckanext/scheming_dcat/schemas/geodcatap/geodcatap_datasets.yaml)
- Improve the search functionality in CKAN for custom schemas. It uses the fields defined in a scheming file to provide a set of tools to use these fields for scheming, and a way to include icons in their labels when displaying them. More info: [`ckanext-scheming_dcat`](https://github.com/mjanez/ckanext-scheming_dcat)
- Add Metadata downloads for Linked Open Data formats ([`mjanez/ckanext-dcat`](https://github.com/mjanez/ckanext-dcat)) and Geospatial Metadata (ISO 19139, Dublin Core, etc. with [`mjanez/ckan-pycsw`](https://github.com/mjanez/ckanext-pycsw))
- Add i18n translations.
- Add a set of useful helpers and templates to be used with Metadata Schemas.
- Update the base theme of CKAN to use with the enhancements of this extension.


## Requirements
This plugin is compatible with CKAN 2.9 or later.


## Installation
```sh
cd $CKAN_VENV/src/

# Install latest stable release of:
## ckanext-scheming: https://github.com/ckan/ckanext-scheming/tags (e.g. release-3.0.0)
pip install -e git+https://github.com/ckan/ckanext-scheming.git@release-3.0.0#egg=ckanext-scheming

## mjanez/ckanext-dcat: https://github.com/mjanez/ckanext-dcat/tags (e.g. 1.2.0-geodcatap)
pip install -e git+https://github.com/mjanez/ckanext-dcat.git@1.2.0-geodcatap#egg=ckanext-dcat
pip install -r https://raw.githubusercontent.com/mjanez/ckanext-dcat/master/requirements.txt

## ckanext-spatial: https://github.com/ckan/ckanext-spatial/tags (e.g. v.2.0.0)
pip install -e git++https://github.com/ckan/ckanext-spatial.git@v2.0.0#egg=ckanext-spatial
pip install -r https://raw.githubusercontent.com/ckan/ckanext-spatial/master/requirements.txt

# Install the scheming_dataset plugin
pip install -e "git+https://github.com/ckan/ckanext-scheming_dcat.git#egg=ckanext-scheming_dcat"
```

## Configuration
Set the plugin:

  ```ini
  # Add the plugin to the list of plugins
  ckan.plugins = ... spatial_metadata ... dcat ... scheming_dcat
  ```
>**Warning**<br>
> When using `scheming_dcat` extension,**`scheming` should not appear in the list of plugins loaded in CKAN.** But `dcat` and `spatial` should.

### Scheming DCAT
Set the schemas you want to use with configuration options:

  ```ini
  # Each of the plugins is optional depending on your use
  ckan.plugins = scheming_dcat_datasets scheming_dcat_groups scheming_dcat_organizations
  ```

To use custom schemas in `ckanext-scheming`:

  ```ini
  # module-path:file to schemas being used
  scheming.dataset_schemas = ckanext.scheming_dcat:schemas/geodcatap/geodcatap_dataset.yaml
  scheming.group_schemas = ckanext.scheming_dcat:schemas/geodcatap/geodcatap_group.json
  scheming.organization_schemas = ckanext.scheming_dcat:schemas/geodcatap/geodcatap_org.json

  #   URLs may also be used, e.g:
  #
  # scheming.dataset_schemas = http://example.com/spatialx_schema.yaml

  #   Preset files may be included as well. The default preset setting is:
  scheming.presets = ckanext.scheming_dcat:schemas/geodcatap/geodcatap_presets.json

  #   The is_fallback setting may be changed as well. Defaults to false:
  scheming.dataset_fallback = false
  ```

### Endpoints
You can update the [`endpoints.yaml`](./ckanext/scheming_dcat/config/endpoints.yaml) file to add your custom OGC/LOD endpoints, only has 2 types of endpoints: `lod` and `ogc`, and the `profile` avalaible in [`ckanext-dcat`](https://github.com/mjanez/ckanext-dcat) Preferably between 4 and 8.

Examples:

* LOD endpoint: A Linked Open Data endpoint is a DCAT endpoint that provides access to RDF data. More information about the catalogue endpoint, how to use the endpoint, (e.g. `https://{ckan-instance-host}/catalog.{format}?[page={page}]&[modified_since={date}]&[profiles={profile1},{profile2}]&[q={query}]&[fq={filter query}]`, and more at [`ckanext-dcat`](https://github.com/mjanez/ckanext-dcat?tab=readme-ov-file#catalog-endpoint)
    ```yaml
      - name: euro_dcat_ap_2_rdf
        display_name: RDF DCAT-AP
        type: lod
        format: rdf
        image_display_url: /images/icons/endpoints/euro_dcat_ap_2.svg
        description: RDF DCAT-AP Endpoint for european data portals.
        profile: euro_dcat_ap_2
        profile_label: DCAT-AP
        version: null
    ```

* OGC Endpoint: An OGC CSW endpoint provides a standards-based interface to discover, browse, and query metadata about spatial datasets and data services. More info about the endpoint at [OGC: Catalogue Service](https://www.ogc.org/)standard/cat/
    ```yaml
      - name: csw_inspire
        display_name: CSW INSPIRE 2.0.2
        type: ogc
        format: xml
        image_display_url: /images/icons/endpoints/csw_inspire.svg
        description: OGC-INSPIRE Endpoint for spatial metadata.
        profile: spain_dcat
        profile_label: INSPIRE
        version: 2.0.2
    ```

### Facet Scheming
To configure facets, there are no mandatory sets in the config file for this extension. The following sets can be used:

  ```ini
  scheming_dcat.facet_list: [list of fields]      # List of fields in scheming file to use to faceting. Use ckan defaults if not provided.
  scheming_dcat.default_facet_operator: [AND|OR]  # OR if not defined

   scheming_dcat.icons_dir: (dir)                  # images/icons if not defined
  ```

As an example for facet list, we could suggest:

  ```ini
  scheming_dcat.facet_list = "theme groups theme_es dcat_type owner_org res_format publisher_name publisher_type frequency tags tag_uri conforms_to spatial_uri"
  ```

The same custom fields for faceting can be used when browsing organizations and groups data:

  ```ini
  scheming_dcat.organization_custom_facets = true
  scheming_dcat.group_custom_facets = true
  ```

This two last settings are not mandatory. You can omit one or both (or set them to `false`), and the default fields for faceting will be used instead.

#### Facet Scheming integration with Solr
1. Clear the index in solr:

	`ckan -c [route to your .ini ckan config file] search-index clear`
   
2. Modify the schema file on Solr (schema or managed schema) to add the multivalued fields added in the scheming extension used for faceting. You can add any field defined in the schema file used in the ckanext-scheming extension that you want to use for faceting.
   You must define each field with these parameters:
   - `type: string` - to avoid split the text in tokens, each individually "faceted".
   - `uninvertible: false` - as recomended by solr´s documentation 
   - `docValues: true` - to ease recovering faceted resources
   - `indexed: true` - to let ckan recover resources under this facet 
   - `stored: true` - to let the value to be recovered by queries
   - `multiValued`: well... it depends on if it is a multivalued field (several values for one resource) or a regular field (just one value). Use "true" or "false" respectively. 
   
   E.g. [`ckanext-iepnb`](https://github.com/OpenDataGIS/ckanext-iepnb) extension are ready to use these multivalued fields. You have to add this configuration fragment to solr schema in order to use them:
	
    ```xml
    <!-- Extra fields -->
      <field name="tag_uri" type="string" uninvertible="false" docValues="true" indexed="true" stored="true" multiValued="true"/>
      <field name="conforms_to" type="string" uninvertible="false" docValues="true" indexed="true" stored="true" multiValued="true"/>
      <field name="lineage_source" type="string" uninvertible="false" docValues="true" indexed="true" stored="true" multiValued="true"/>
      <field name="lineage_process_steps" type="string" uninvertible="false" docValues="true" indexed="true" stored="true" multiValued="true"/>
      <field name="reference" type="string" uninvertible="false" docValues="true" indexed="true" stored="true" multiValued="true"/>
      <field name="theme" type="string" uninvertible="false" docValues="true" indexed="true" stored="true" multiValued="true"/>
      <field name="theme_es" type="string" uninvertible="false" docValues="true" multiValued="true" indexed="true" stored="true"/>
      <field name="metadata_profile" type="string" uninvertible="false" docValues="true" multiValued="true" indexed="true" stored="true"/>
      <field name="resource_relation" type="string" uninvertible="false" docValues="true" indexed="true" stored="true" multiValued="true"/>
    ```

    >**Note**<br>
    >You can ommit any field you're not going to use for faceting, but the best policy could be to add all values at the beginning. 
    >
    >The extra fields depend on your [schema](/ckanext/scheming_dcat/schemas/)
   	
	**Be sure to restart Solr after modify the schema.**
	
3. Restart CKAN. 
     
4. Reindex solr index:

	`ckan -c [route to your .ini ckan config file] search-index rebuild`

	Sometimes solr can issue an error while reindexing. In that case I'd try to restart solr, delete index ("search-index clear"), restart solr, rebuild index, and restart solr again.
	
	Ckan needs to "fix" multivalued fields to be able to recover values correctly for faceting, so this step must be done in order to use faceting with multivalued fields. 

### Icons
Icons for each field option in the [`scheming file`](ckanext/scheming_dcat/schemas/geodcatap/geodcatap_datasets.yaml) can be set in multiple ways:

- Set a root directory path for icons for each field using the `icons_dir` key in the scheming file.
- If `icons_dir` is not defined, the directory path is guessed starting from the value provided for the `scheming_dcat.icons_dir` parameter in the CKAN config file, adding the name of the field as an additional step to the path (`public/images/icons/{field_name`).
- For each option, use the `icon` setting to provide the last steps of the icon path from the field's root path defined before. This value may be just a file name or include a path to add to the icon's root directory.
- If `icon` is not used, a directory and file name are guessed from the option's value.
- Icons files are tested for existence when using `schemingdct_schema_icon` function to get them. If the file doesn't exist, the function returns `None`. Icons can be provided by any CKAN extension in its `public` directory.
- Set a `default icon` for a field using the default_icon setting in the scheming file. You can get it using `schemingdct_schema_get_default_icon` function, and it is your duty to decide when and where to get and use it in a template.

## New theme
Update the base theme of CKAN to use with the enhancements of this extension.

![image](https://github.com/mjanez/ckanext-scheming_dcat/assets/96422458/97b91bdc-b1ec-402a-9750-cfe30ca3201b)
![image](https://github.com/mjanez/ckanext-scheming_dcat/assets/96422458/48b63c9e-1ab2-4504-b991-2ac63a8875c8)
![image](https://github.com/mjanez/ckanext-scheming_dcat/assets/96422458/213def6f-5d4c-4786-9d5b-24fed010d307)

![screenshot 1695622478](https://github.com/mjanez/ckanext-scheming_dcat/assets/96422458/bb522849-1319-49cd-ab93-5c3fa5784587)
![screenshot 1695622650](https://github.com/mjanez/ckanext-scheming_dcat/assets/96422458/7244f9c2-416d-4489-aee8-41cf91ae25a5)
![image](https://github.com/mjanez/ckanext-scheming_dcat/assets/96422458/5325df04-0ee7-48c3-a924-c8875fc8e2ad)
![screenshot 1695622687](https://github.com/mjanez/ckanext-scheming_dcat/assets/96422458/054ff4e5-56a3-4683-9492-1aa0659ee536)
![screenshot 1695622719](https://github.com/mjanez/ckanext-scheming_dcat/assets/96422458/1ecb14c9-9946-4802-8e02-7a51e2911226)

## Schemas
With this plugin, you can customize the group, organization, and dataset entities in CKAN. Adding and enabling a schema will modify the forms used to update and create each entity, indicated by the respective `type` property at the root level. Such as `group_type`, `organization_type`, and `dataset_type`. Non-default types are supported properly as is indicated throughout the examples.

Are available to use with this extension a number of custom schema, more info: [`schemas/README.md`](./ckanext/scheming_dcat/schemas/README.md)

### GeoDCAT-AP (ES)
[`schemas/geodcatp_es`](/ckanext/scheming_dcat/schemas/geodcatap_es/geodcatap_es_dataset.yaml) with specific extensions for spatial data and [GeoDCAT-AP](https://github.com/SEMICeu/GeoDCAT-AP)/[INSPIRE](https://github.com/INSPIRE-MIF/technical-guidelines) metadata [profiles](https://en.wikipedia.org/wiki/Geospatial_metadata). 

>**Note**<br>
> RDF to CKAN dataset mapping: [GeoDCAT-AP (ES) to CKAN](ckanext/scheming_dcat/schemas/README.md#geodcat-ap-es)


### DCAT 
[`schemas/dcat`](/ckanext/scheming_dcat/schemas/dcat/dcat_dataset.yaml) based
on: [DCAT](https://www.w3.org/TR/vocab-dcat-3/).

>**Note**<br>
> RDF to CKAN dataset mapping: [DCAT to CKAN](ckanext/scheming_dcat/schemas/README.md#dcat)

### DCAT-AP (EU)
[`schemas/dcatap`](/ckanext/scheming_dcat/schemas/dcatap/dcatap_dataset.yaml) based on: [DCAT-AP](https://op.europa.eu/en/web/eu-vocabularies/dcat-ap) for the european context.

>**Note**<br>
> RDF to CKAN dataset mapping: [DCAT-AP (EU) to CKAN](ckanext/scheming_dcat/schemas/README.md#dcat-ap-eu)

### GeoDCAT-AP (EU)
[`schemas/geodcatap`](/ckanext/scheming_dcat/schemas/geodcatap/geodcatap_dataset.yaml) based on: [GeoDCAT-AP](https://github.com/SEMICeu/GeoDCAT-AP) for the european context.

>**Note**<br>
> RDF to CKAN dataset mapping: [GeoDCAT-AP (EU) to CKAN](ckanext/scheming_dcat/schemas/README.md#geodcat-ap-eu)


## Running the Tests
To run the tests:

    pytest --ckan-ini=test.ini ckanext/scheming_dcat/tests
