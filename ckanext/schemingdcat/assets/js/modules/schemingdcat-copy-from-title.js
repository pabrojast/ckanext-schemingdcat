ckan.module('copy-from-title', function ($) {
    return {
      initialize: function () {
        var titleInput = $('input[name="title_translated-en"]');
        var identifierInput = this.el;
        var slugInput = $('input[name="name"]');
        
        var identifierInitialValue = identifierInput.val();
        var slugInitialValue = slugInput.val();
        
        function updateIdentifier() {
          var titleValue = titleInput.val();
          
          // Actualizar el identificador si estaba inicialmente vacío
          if (!identifierInitialValue) {
            identifierInput.val(titleValue);
            identifierInput.trigger('change');
          }
          
          // Actualizar el slug si estaba inicialmente vacío
          if (!slugInitialValue) {
            slugInput.val(titleValue).trigger('change');
          }
        }

        // Usar 'input' para actualizar en tiempo real
        titleInput.on('input', updateIdentifier);
        
        // No actualizamos al cargar la página
      }
    };
  });
