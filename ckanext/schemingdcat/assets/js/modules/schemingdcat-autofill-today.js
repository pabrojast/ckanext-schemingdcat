ckan.module('schemingdcat-autofill-today', function ($) {
    return {
      initialize: function () {
        var el = this.el;
        
        // Función para obtener la fecha de hoy en formato YYYY-MM-DD
        function getTodayDate() {
          var today = new Date();
          var dd = String(today.getDate()).padStart(2, '0');
          var mm = String(today.getMonth() + 1).padStart(2, '0'); // Enero es 0!
          var yyyy = today.getFullYear();
          return yyyy + '-' + mm + '-' + dd;
        }
        
        // Determinar si estamos en un formulario de recurso
        var isResourceForm = el.closest('.resource-form').length > 0 || 
                            el.closest('#resource-edit').length > 0 ||
                            el.attr('name') && el.attr('name').indexOf('resources__') !== -1;
        
        // Determinar si estamos en modo edición del dataset (no del recurso)
        var isDatasetEditMode = window.location.href.indexOf('/edit/') !== -1 && !isResourceForm;
        
        // En modo creación de dataset o cuando es un nuevo recurso, rellenar con la fecha de hoy si está vacío
        if (!isDatasetEditMode || isResourceForm) {
          // Si el campo está vacío, llenarlo con la fecha de hoy
          if (!el.val()) {
            el.val(getTodayDate());
          }
        }
        
        // Convertir la fecha al formato dd-mm-YYYY cuando se envíe el formulario
        el.closest('form').on('submit', function() {
          var dateValue = el.val();
          if (dateValue) {
            var parts = dateValue.split('-');
            if (parts.length === 3) {
              el.val(parts[2] + '-' + parts[1] + '-' + parts[0]);
            }
          }
        });
      }
    };
  });
