ckan.module('schemingdcat-autofill-today', function ($) {
    return {
      initialize: function () {
        var el = this.el;
        
        // Función para obtener la fecha de hoy en formato YYYY-MM-DD
        function getTodayDate() {
          var today = new Date();
          var dd = today.getDate();
          var mm = today.getMonth() + 1; // Enero es 0!
          var yyyy = today.getFullYear();
          
          // Asegurar dos dígitos
          if (dd < 10) dd = '0' + dd;
          if (mm < 10) mm = '0' + mm;
          
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
      }
    };
  });
