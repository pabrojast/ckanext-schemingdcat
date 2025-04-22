ckan.module('copy-from-title', function ($) {
    return {
      initialize: function () {
        // Solo configuramos el comportamiento en modo de creación, no en edición
        if (window.location.href.indexOf('/edit/') === -1) {
          var titleInput = $('input[name="title_translated-en"]');
          var identifierInput = this.el;
          var slugInput = $('input[name="name"]');
          
          function updateIdentifier() {
            var titleValue = titleInput.val();
            
            // Actualizar el identificador solo si está vacío
            if (identifierInput.length && !identifierInput.val().trim() && titleValue) {
              identifierInput[0].value = titleValue;
            }
            
            // Actualizar el slug solo si está vacío
            if (slugInput.length && !slugInput.val().trim() && titleValue) {
              // Para el slug necesitamos disparar el evento change para que se genere correctamente
              slugInput.val(titleValue).trigger('change');
            }
          }

          // Usar 'input' para actualizar en tiempo real, pero solo en modo creación
          titleInput.on('input', updateIdentifier);
        }
      }
    };
  });
