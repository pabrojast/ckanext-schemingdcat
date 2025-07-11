ckan.module('schemingdcat-multi-resource-upload', function ($) {
  return {
    initialize: function () {
      var self = this;

      // Permitir selección múltiple en todos los file inputs de resources
      self._enableMultipleSelection();

      // Delegamos el evento change para capturar selecciones múltiples
      $(document).on('change', 'input[type="file"][id^="field-resource-upload"]', function (e) {
        var $input = $(this);
        var files = e.target.files;
        if (!files || files.length <= 1) {
          // Caso normal (un solo fichero): dejamos que CKAN actúe con su flow habitual
          return;
        }
        self._handleMultipleFiles($input, files);
      });
    },

    /* Añade atributo multiple a los inputs existentes (y futuros mediante delegación) */
    _enableMultipleSelection: function () {
      $('input[type="file"][id^="field-resource-upload"]').attr('multiple', 'multiple');
    },

    /* Gestiona la selección múltiple dividiendo los ficheros en varios bloques resource */
    _handleMultipleFiles: function ($originInput, files) {
      var filesArr = Array.prototype.slice.call(files);
      if (!filesArr.length) return;

      // Dejamos el primer fichero en el bloque actual
      var firstFile = filesArr.shift();
      this._setInputFile($originInput, firstFile);
      this._autoFillFields($originInput.closest('.resource-upload-field'), firstFile);

      var self = this;
      filesArr.forEach(function (file) {
        self._addResourceWithFile(file);
      });
    },

    /* Crea un nuevo bloque resource pulsando el botón estándar y rellena los datos */
    _addResourceWithFile: function (file) {
      var self = this;
      var $addBtn = $('.add-resource, #add-resource, button[data-module="add-resource"], button[data-action="add-resource"], button.resource-add').first();
      if (!$addBtn.length) {
        console.warn('schemingdcat: No se encontró el botón "Añadir recurso".');
        return;
      }

      $addBtn.trigger('click');

      // Esperamos a que el DOM se actualice (CKAN clona la plantilla vía JS)
      setTimeout(function () {
        var $wrapper = $('.resource-upload-field').last();
        if (!$wrapper.length) {
          console.warn('schemingdcat: No se encontró el contenedor del nuevo recurso.');
          return;
        }
        var $fileInput = $wrapper.find('input[type="file"][id^="field-resource-upload"]');
        if (!$fileInput.length) {
          console.warn('schemingdcat: El nuevo recurso no contiene input file.');
          return;
        }
        // forzar multiple por si la plantilla no lo trae
        $fileInput.attr('multiple', 'multiple');
        self._setInputFile($fileInput, file);
        self._autoFillFields($wrapper, file);
      }, 250); // 250 ms suele bastar
    },

    /* Asigna un objeto File a un input mediante DataTransfer */
    _setInputFile: function ($input, file) {
      if (typeof DataTransfer !== 'undefined') {
        try {
          var dt = new DataTransfer();
          dt.items.add(file);
          $input[0].files = dt.files;
        } catch (err) {
          console.warn('schemingdcat: DataTransfer no soportado en este navegador.');
        }
      }
    },

    /* Rellena automáticamente campos básicos (name, format, created) */
    _autoFillFields: function ($wrapper, file) {
      // Nombre (sin extensión)
      var baseName = file.name.replace(/\.[^.]+$/, '');
      $wrapper.find('input[name$="name"], input[name$="name__"]').first().val(baseName);

      // Formato (extensión)
      var ext = file.name.split('.').pop().toUpperCase();
      var map = { 'XLSX': 'XLS', 'GEOJSON': 'GeoJSON' };
      var format = map[ext] || ext;
      $wrapper.find('input[name$="format"], input[name$="format__"]').first().val(format);

      // Fecha (created) si existe y está vacía
      var $created = $wrapper.find('input[name$="created"], input[name$="created__"]').first();
      if ($created.length && !$created.val()) {
        var today = new Date().toISOString().slice(0, 10);
        $created.val(today);
      }
    }
  };
}); 