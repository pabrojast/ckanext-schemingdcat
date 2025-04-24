ckan.module('schemingdcat-autofill-today', function ($) {
    return {
      initialize: function () {
        var el = this.el;
        
        // Determinar si estamos en modo edición
        var isEditMode = window.location.href.indexOf('/edit/') !== -1;
        
        // En modo creación, rellenar con la fecha de hoy si está vacío
        if (!isEditMode) {
          // Función para obtener la fecha de hoy en formato YYYY-MM-DD
          function getTodayDate() {
            var today = new Date();
            var dd = String(today.getDate()).padStart(2, '0');
            var mm = String(today.getMonth() + 1).padStart(2, '0'); // Enero es 0!
            var yyyy = today.getFullYear();
            return yyyy + '-' + mm + '-' + dd;
          }
          
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
