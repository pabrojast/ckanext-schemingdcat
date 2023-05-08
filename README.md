# ckanext-facet-scheming

`ckanext-facet_scheming` provides functions and templates that have been specially developed to extend the search functionality in CKAN for custom schemas.  It uses the fields defined in a scheming file to provide a set of tools to use these fields for scheming, and a way to include icons in their labels when displaying them.

![image](https://user-images.githubusercontent.com/96422458/235639244-4c2fc026-efec-460c-9800-62d2b5668b4a.png)



## Requirements

>**Warning**<br>
> This extension needs [custom GeoDCAT-AP ckanext-scheming](https://github.com/mjanez/ckanext-scheming) extension to work.

Facet-scheming is designed to provide templates and functions to be used by other extensions over it. It uses the fields defined in a scheming file to provide
 a set of tools to use those fields for scheming, and a way to include icons in its labels when displaying them.

Compatibility with core CKAN versions:

| CKAN version    | Compatible?   |
| --------------- | ------------- |
| 2.8 and earlier | not tested    |
| 2.9             | yes           |
| 2.10            | not yet       |

Suggested values:

* "yes"
* "not tested" - I can't think of a reason why it wouldn't work
* "not yet" - there is an intention to get it working
* "no"


## Installation

To install ckanext-facet-scheming:

1. Activate your CKAN virtual environment, for example:

     . /usr/lib/ckan/default/bin/activate

2. Clone the source and install it on the virtualenv

    git clone https://github.com/dsanjurj/ckanext-facet-scheming.git
    cd ckanext-facet-scheming
    pip install -e .
	pip install -r requirements.txt
	sudo rm -fR /*

3. Add `facet-scheming` to the `ckan.plugins` setting in your CKAN
   config file (by default the config file is located at
   `/etc/ckan/default/ckan.ini`).

4. Clear the index in solr:

	`ckan -c [route to your .ini ckan config file] search-index clear`
   
5. Modify the schema file on Solr (schema or managed schema) to add the multivalued fields added in the scheming extension used for faceting. You can add any field defined in the schema file used in the ckanext-scheming extension that you want to use for faceting.
   You must define each field with these parameters:
   - type: string - to avoid split the text in tokens, each individually "faceted".
   - uninvertible: false - as recomended by solr´s documentation 
   - docValues: true - to ease recovering faceted resources
   - indexed: true - to let ckan recover resources under this facet 
   - stored: true - to let the value to be recovered by queries
   - multiValued: well... it depends on if it is a multivalued field (several values for one resource) or a regular field (just one value). Use "true" or "false" respectively. 
   
   By now iepnb extension are ready to use these multivalued fields. You have to add this configuration fragment to solr schema in order to use them:

	
```xml
	<! IEPNB extra fields - >
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
   	
	Be sure to restart Solr after modify the schema.
	
6. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu:

     sudo service apache2 reload
     
7. Reindex solr index:

	`ckan -c [route to your .ini ckan config file] search-index rebuild`

	Sometimes solr can issue an error while reindexing. In that case I'd try to restart solr, delete index ("search-index clear"), restart solr, rebuild index, and restart solr again.
	
	Ckan needs to "fix" multivalued fields to be able to recover values correctly for faceting, so this step must be done in order to use faceting with multivalued fields. 
     
## Helpers

Facet-scheming provides a set of useful helpers to be used in templates

- **fscheming\_default\_facet\_search\_operator**(): Returns the default 
facet search operator: AND/OR (string)
- **fscheming\_decode\_json**( json\_text ): Converts a JSON formatted text
 in a python object using ckan.common.json
- **fscheming\_organization\_name**( id ): Returns the name of the organization
 given its id. Returns None if not found
- **fscheming\_get_facet\_label**( facet ): Returns the label of a facet as
 defined in the scheming file
- **fscheming\_get\_facet\_items\_dict**( facet, search\_facets=None, limit=None,
 exclude\_active=False, scheming\_choices=None): Returns the list of unselected 
 facet items (objects) for the given facet, sorted by the field indicated in the request.
        Arguments:
  - facet -- the name of the facet to filter.
  - search\_facets -- dict with search facets. Taken from c.search_facets if not
   defined
  - limit -- the max. number of facet items to return. Taken from 
  c.search\_facets_limits if not defined
  - exclude\_active -- only return unselected facets.
  - scheming\_choices -- scheming choices to use to get labels from values.
   If not provided takes `display\_name` field provided by Solr
- **fscheming\_new\_order\_url**(name, concept): Returns a url with the order
 parameter for the given facet and concept to use.  
    Based in the actual order it rotates ciclically from
     \[no order\]->[direct order]->[inverse order] for the given concept \(name or count\)
- **fscheming\_schema\_get\_icons\_dir**(field): Gets the icons' directory
 for the given field. It can be obtained (in order of preference) from the 
 _icons\_dir_ property for the given field in the scheming file, from the 
 _facet\_scheming.icons\_dir_ value  given in CKAN configuration file, plus
  the name of the field, or from the directory named after the field name 
  in `images/icons` dir.
- **fscheming\_schema\_get\_default\_icon**(field): Gets the default 
 icon for the given field, defined in the schemig file, o `None` if not defined.
- **fscheming\_schema\_icon**(choice, dir=None): Search for the icon path for 
 the especified choice beside the given dir (if any). If the scheming file include a _icon_ 
 setting for the choice, this is returned (beside the given _dir_).
  If not, it takes the last fragment of the value url for the icon name, and 
  the next two fragments of the url as two steps from _dir_ to the icon file.  
  It locates the file searching for svg, png, jpeg or gif extensions in all 
  the _public_ dirs of the ckan configured extensions. If the file could be 
  located, it returns the relative url. If not, it returns `None`.
- **fscheming\_get\_choice\_dic**(field, value): Gets the choice item for the 
  given value in field of the scheming file. 

## Templates

Also a set of useful templates and snippets are provided

- **fscheming\_facet\_list.html** Extending ckan original facet list 
snippet, provides a way to show facet labels instead of values (which is what 
Solr provides), prepending an icon if provided. To call you must extend the template 
`package/search.html`.

- **fscheming\_facet_search\_operator** Gives the control to select the operator used to
combine facets. 

- **multiple\_choice\_icon** Display snippet to use instead the original _multiple\_choice_ snippet
provided by the scheming extension. It adds an icon before the label of the value.

- **select\_icon** Display snippet to use instead the original _select_ snippet
provided by the scheming extension. It adds an icon before the label of the value.

- **multiple\_select-icon** Form snipet to use instead the original multiple_select to show icons 
in multiple options fileds when adding or editing a resource

## Config settings

### Config (.ini) file

There are not mandatory sets in the config file for this extension. You can use the following sets:

```
facet_scheming.facet_list: [list of fields]      # List of fields in scheming file to use to faceting. Use ckan defaults if not provided.
facet_scheming.default_facet_operator: [AND|OR]  # OR if not defined
facet_scheming.icons_dir: (dir)                  # images/icons if not defined
```

As an example for facet list, we could suggest:

```
facet_scheming.facet_list = theme theme_es dcat_type owner_org res_format publisher_name publisher_type frequency tags tag_uri conforms_to
```

### Icons

You can set where the icons for each filed option in a scheming file must be by multiple ways:

- You can set a root directory path for icons for each field using the "icons\_dir" key in the scheming file.

- If you don´t define this key, the directory path are guessed starting from the value provided for the 
"facet\_scheming.icons\_dir" parameter ("images/icons" by default if not provided) in CKAN config file, adding the 
name of the field (field\_name) as a additional step to the path.

Having the root path for the icons used by the values for the options of a field, you must define where the 
icons for each option must be, or know where the extension will search for them by default

- For each option you can use a "icon" setting to provide the last steps of the icon path (from the field icons´ 
root path defined before). This value may be just a file name, or include a path to add to the icon´s root 
directory (_some\_name.jpg_ or _some\_dir\_name/some\_name.jpg_).

- If you dont use this setting, a directory and file name are guessed from the option´s value:

  - If the value is a url, the last two steps of the url are used to guess were the icon is. The first is added 
  to the icons´ dir path guessed or defined in the previous step as a subdirectory. The second are used to 
  guess the icon's name, adding and testing "svg","png","jpg" or "gif" as possible extensions.
  - If the value is not a url, it is taken as the name of the icon (testing the extensions named before) in the 
  icons root directory for this field.
  
Icons files are tested for existence when using fscheming\_schema\_icon function to get them. If the file doesn't exist, the 
function returns `None`. Icons can be provided by any ckan extension, in its `public` directory.

You can set a default icon for a field using the _default\_icon_ setting in the scheming file. You can get it using 
fscheming\_schema\_get\_default\_icon function, and is your duty do decide when and where get and use it in 
a template.

Examples:

We have set `facet\_scheming.icons\_dir: images/icons` in .ini CKAN config file (or not set this parameter at all,
because this is the default value)

Defining icons in a schema file:

```
- field_name: strange_field
...
  icons_dir: icons/for/strange/field
...
  choices:
  - value: http://some_domain.fake/level1/level2/strange_value
    label:
      en: Strange Value
      es: Valor Extraño
    description:
      en: ''
      es: 'Valor extraño para un campo extraño'
    icon: strange_value_icon.gif
    ...
```
    
Icons file for "strange_field" field will be searched in public/icons/for/strange/field directory in all CKAN extensions. Url will be
icons/for/strange/field/strange\_value\_icon.gif if file was found in any extension.

The value provided in facet\_scheming.icons\_dir (images/icons) will NOT be used to compose the url, because you have provided icons\_dir in the scheming file for this field.

Using icons not defined in the schema file:

```
- field_name: strange_field
...
  choices:
  - value: http://some_domain.fake/level1/level2/strange_value
    label:
      en: Strange Value
      es: Valor Extraño
    description:
      en: ''
      es: 'Valor extraño para un campo extraño'
    ...
```

Directory for icons will be taken from facet\_scheming.icons\_dir, bacause you not provide a 

Url for this option will be _images/icons/strange\_field/level2/strange\_value.[ext]_,
 beeing [ext] any extension in svg, png, jpg or gif (searched in this order). 

## Developer installation

To install ckanext-facet-scheming for development, activate your CKAN virtualenv and
do:

    git clone https://github.com/dsanjurj/ckanext-facet-scheming.git
    cd ckanext-facet-scheming
    python setup.py develop
    pip install -r dev-requirements.txt


## Tests

To run the tests, do:

    pytest --ckan-ini=test.ini


## Releasing a new version of ckanext-facet-scheming

If ckanext-facet-scheming should be available on PyPI you can follow these steps to publish a new version:

1. Update the version number in the `setup.py` file. See [PEP 440](http://legacy.python.org/dev/peps/pep-0440/#public-version-identifiers) for how to choose version numbers.

2. Make sure you have the latest version of necessary packages:

    pip install --upgrade setuptools wheel twine

3. Create a source and binary distributions of the new version:

       python setup.py sdist bdist_wheel && twine check dist/*

   Fix any errors you get.

4. Upload the source distribution to PyPI:

       twine upload dist/*

5. Commit any outstanding changes:

       git commit -a
       git push

6. Tag the new release of the project on GitHub with the version number from
   the `setup.py` file. For example if the version number in `setup.py` is
   0.0.1 then do:

       git tag 0.0.1
       git push --tags

## License

[AGPL](https://www.gnu.org/licenses/agpl-3.0.en.html)
