from ckan.plugins.interfaces import Interface


class ISchemingDCATHarvester(Interface):
    '''
    This is a common harvesting interface for SchemingDCATHarvester that provides a set of methods to be implemented by a harvester. 
    The methods are designed to be called at different stages of the harvesting process, allowing for 
    customization and extension of the default behavior. 

    The methods include hooks before and after the download of the remote sheet file, before and after the 
    cleaning process, after the parsing of the sheet file, and before and after the creation and update of 
    the dataset. 

    Additionally, there are methods to modify the dataset dict that will be created or updated, and to 
    update the package schema for the creation and update actions.

    Each method is documented with its purpose, parameters, and return values.
    '''

    def before_download(self, url, harvest_job):
        '''
        Called just before the remote RDF file is downloaded

        It returns a tuple with the url (which can be modified) and an
        optional list of error messages.

        If the url value evaluates to False the gather stage will be stop.

        This extension point can be useful to validate the URL using an
        external service.

        :param url: The harvest source URL, ie the remote RDF file location
        :type url: string
        :param harvest_job: A ``HarvestJob`` domain object which contains a
                            reference to the harvest source
                            (``harvest_job.source``).
        :type harvest_job: object


        :returns: A tuple with two items:
                    * The url. If this is False the gather stage will stop.
                    * A list of error messages. These will get stored as gather
                      errors by the harvester
        :rtype: tuple
        '''
        return url, []

    def update_session(self, session):
        '''
        Called before making the HTTP request to the remote site to download
        the RDF file.

        It returns a valid `requests` session object.

        This extension point can be useful to add special parameters to the 
        request (e.g. add client certificates).

        :param session: The requests session object
        :type session: object

        :returns: The updated requests session object
        :rtype: object
        '''
        return session

    def after_download(self, content, harvest_job):
        '''
        Called just after the remote RDF file has been downloaded

        It returns a tuple with the content (which can be modified) and an
        optional list of error messages.

        If the content value evaluates to False the gather stage will stop.

        This extension point can be useful to validate the file contents using
        an external service.

        :param content: The remote RDF file contents
        :type content: string
        :param harvest_job: A ``HarvestJob`` domain object which contains a
                            reference to the harvest source
                            (``harvest_job.source``).
        :type harvest_job: object


        :returns: A tuple with two items:
                    * The file content. If this is False the gather stage will
                      stop.
                    * A list of error messages. These will get stored as gather
                      errors by the harvester
        :rtype: tuple
        '''
        return content, []

    def before_cleaning(self, content_dict):
        '''
        This method is called before the cleaning process starts. It takes a dictionary of content as input.

        :param content_dict: The content to be cleaned.
        :type content_dict: dict

        :returns: A tuple with two items:
                    * The remote sheet content with all datasets, distributions and datadictionaries dicts.
                    * A list of error messages. These will get stored as gather errors by the harvester.
        :rtype: tuple
        '''
        return content_dict, []

    def after_cleaning(self, clean_datasets):
        '''
        This method is called after the cleaning process ends. It takes a list of cleaned datasets as input.

        :param clean_datasets: The cleaned datasets.
        :type clean_datasets: list

        :returns: A tuple with two items:
                    * The cleaned datasets list of dictionaries.
                    * A list of error messages. These will get stored as gather errors by the harvester.
        :rtype: tuple
        '''
        return clean_datasets, []

    def after_parsing(self, rdf_parser, harvest_job):
        '''
        Called just after the content from the remote RDF file has been parsed

        It returns a tuple with the parser (which can be modified) and an
        optional list of error messages.

        This extension point can be useful to work with the graph and put it to
        other stores, e.g. a triple store.

        :param rdf_parser: The RDF parser with the remote content as a graph object
        :type rdf_parser: ckanext.dcat.processors.RDFParser
        :param harvest_job: A ``HarvestJob`` domain object which contains a
                            reference to the harvest source
                            (``harvest_job.source``).
        :type harvest_job: object


        :returns: A tuple with two items:
                    * The RDF parser. If this is False the gather stage will
                      stop.
                    * A list of error messages. These will get stored as gather
                      errors by the harvester
        :rtype: tuple
        '''
        return rdf_parser, []

    def get_package_dict(self, context, data_dict):
        '''
        Allows to modify the dataset dict that will be created or updated

        This is the dict that the harvesters will pass to the `package_create`
        or `package_update` actions. Extensions can modify it to suit their
        needs, adding or removing filds, modifying the default ones, etc.

        This method should always return a package_dict. Note that, although
        unlikely in a particular instance, this method could be implemented by
        more than one plugin.

        If a dict is not returned by this function, the import stage will be
        cancelled.


        :param context: Contains a reference to the model, eg to
                        perform DB queries, and the user name used for
                        authorization.
        :type context: dict
        :param data_dict: Available data. Contains four keys:

            * `package_dict`
               The default package_dict generated by the harvester. Modify this
               or create a brand new one.
            * `xls_values`
               The parsed XLS dataset values. These contain more fields
               that are not added by default to the ``package_dict``.
            * `harvest_object`
               A ``HarvestObject`` domain object which contains a reference
               to the original metadata document (``harvest_object.content``)
               and the harvest source (``harvest_object.source``).

        :type data_dict: dict

        :returns: A dataset dict ready to be used by ``package_create`` or
                  ``package_update``
        :rtype: dict
        '''
        return data_dict['package_dict']

    def before_update(self, harvest_object, dataset_dict, temp_dict):
        '''
        Called just before the ``package_update`` action.
        It may be used to preprocess the dataset dict.

        If the content of the dataset dict is emptied (i.e. set to ``None``), 
        the dataset will not be updated in CKAN, but simply ignored.

        Implementations may store some temp values in temp_dict, that will be
        then passed back in the ``after_update`` call.

        :param harvest_object: A ``HarvestObject`` domain object.
        :type harvest_job: object
        :param dataset_dict: The dataset dict already parsed by the RDF parser
                             (and related plugins).
        :type dataset_dict: dict
        :param temp_dict: A dictionary, shared among all plugins, for storing
                          temp data. Such dict will be passed back in the
                          ``after_update`` call.
        :type temp_dict: dict
        '''
        pass

    def after_update(self, harvest_object, dataset_dict, temp_dict):
        '''
        Called just after a successful ``package_update`` action has been
        performed.

        :param harvest_object: A ``HarvestObject`` domain object.
        :type harvest_job: object
        :param dataset_dict: The dataset dict that has just been stored into
                             the DB.
        :type dataset_dict: dict
        :param temp_dict: A dictionary, shared among all plugins, for storing
                          temp data. 
        :type temp_dict: dict

        :returns: A string containing an error message, or None. If the error
                  string is not None, it will be saved as an import error,
                  and dataset importing will be rolled back,
        :rtype: string
        '''

        return None

    def before_create(self, harvest_object, dataset_dict, temp_dict):
        '''
        Called just before the ``package_create`` action.
        It may be used to preprocess the dataset dict.

        If the content of the dataset dict is emptied (i.e. set to ``None``), 
        the dataset will not be created in CKAN, but simply ignored.

        Implementations may store some temp values in temp_dict, that will be
        then passed back in the ``after_create`` call.

        :param harvest_object: A ``HarvestObject`` domain object.
        :type harvest_job: object
        :param dataset_dict: The dataset dict already parsed by the RDF parser
                             (and related plugins).
        :type dataset_dict: dict
        :param temp_dict: A dictionary, shared among all plugins, for storing
                          temp data. Such dict will be passed back in the
                          ``after_create`` call.
        :type temp_dict: dict
        '''
        pass

    def after_create(self, harvest_object, dataset_dict, temp_dict):
        '''
        Called just after a successful ``package_create`` action has been
        performed.

        :param harvest_object: A ``HarvestObject`` domain object.
        :type harvest_job: object
        :param dataset_dict: The dataset dict that has just been stored into
                             the DB.
        :type dataset_dict: dict
        :param temp_dict: A dictionary, shared among all plugins, for storing
                          temp data.
        :type temp_dict: dict

        :returns: A string containing an error message, or None. If the error
                  string is not None, it will be saved as an import error,
                  and dataset importing will be rolled back,
        :rtype: string
        '''
        return None

    def update_package_schema_for_create(self, package_schema):
        '''
        Called just before the ``package_create`` action.

        :param package_schema: The default create package schema dict.
        :type package_schema_dict: dict

        :returns: The updated package_schema object
        :rtype: object
        '''
        return package_schema

    def update_package_schema_for_update(self, package_schema):
        '''
        Called just before the ``package_update`` action.

        :param package_schema: The default update package schema dict.
        :type package_schema_dict: dict

        :returns: The updated package_schema object
        :rtype: object
        '''
        return package_schema
