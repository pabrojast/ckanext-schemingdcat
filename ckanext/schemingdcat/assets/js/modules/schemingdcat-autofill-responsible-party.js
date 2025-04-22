ckan.module('autofill-responsible-party', function ($) {
    return {
      initialize: function () {
        // Solo autorrellena en modo de creación, no en edición
        if (window.location.href.indexOf('/edit/') === -1) {
          try {
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
          } catch (e) {
            console.warn('Error al procesar datos del formulario:', e);
          }
        }
      },
      
      autofillField: function (fieldName, value) {
        if (!value) return; // No hacemos nada si no hay valor
        
        var field = $('input[name="' + fieldName + '"]');
        // Solo rellenamos si el campo existe, está vacío y tenemos un valor para rellenar
        if (field.length && !field.val().trim()) {
          // Establecemos el valor directamente sin disparar eventos
          field[0].value = value;
        }
      }
    };
  });