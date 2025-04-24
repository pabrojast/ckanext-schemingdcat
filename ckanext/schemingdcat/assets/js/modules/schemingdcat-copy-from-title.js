ckan.module('copy-from-title', function ($) {
    return {
      initialize: function () {
        var titleInput = $('input[name="title_translated-en"]');
        var identifierInput = this.el;
        var slugInput = $('input[name="name"]');
        
        // Determinar si estamos en modo edición
        var isEditMode = window.location.href.indexOf('/edit/') !== -1;
        
        // Guardar valores iniciales en modo edición
        var initialValues = {};
        if (isEditMode) {
          initialValues.identifier = identifierInput.val();
          initialValues.slug = slugInput.val();
        }
        
        function updateIdentifier() {
          var titleValue = titleInput.val();
          
          // En modo edición, solo actualizar si el campo estaba inicialmente vacío
          // En modo creación, actualizar siempre
          if (!isEditMode || !initialValues.identifier) {
            identifierInput.val(titleValue);
          }
          
          // En modo edición, solo actualizar el slug si estaba inicialmente vacío
          // En modo creación, actualizar siempre
          if (!isEditMode || !initialValues.slug) {
            slugInput.val(titleValue).trigger('change');
          }
        }

        // Usar 'input' para actualizar en tiempo real
        titleInput.on('input', updateIdentifier);
      }
    };
  });
