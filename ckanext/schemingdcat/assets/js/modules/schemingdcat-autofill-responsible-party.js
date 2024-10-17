ckan.module('autofill-responsible-party', function ($) {
    return {
      initialize: function () {
        var formData = JSON.parse($('#form_data').val());
        
        // Publisher
        this.autofillField('publisher_name', formData.contact_name);
        this.autofillField('publisher_email', formData.contact_email);
        this.autofillField('publisher_url', formData.contact_url);
        
        // Maintainer
        this.autofillField('maintainer', formData.contact_name);
        this.autofillField('maintainer_email', formData.contact_email);
        this.autofillField('maintainer_url', formData.contact_url);
        
        // Author
        this.autofillField('author', formData.contact_name);
        this.autofillField('author_email', formData.contact_email);
        this.autofillField('author_url', formData.contact_url);
      },
      
      autofillField: function (fieldName, value) {
        var field = $('input[name="' + fieldName + '"]');
        if (field.length && !field.val()) {
          field.val(value);
          field.trigger('change');
        }
      }
    };
  });