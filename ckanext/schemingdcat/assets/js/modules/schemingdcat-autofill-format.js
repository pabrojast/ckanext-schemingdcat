ckan.module('schemingdcat-autofill-format', function ($) {
  return {
    initialize: function () {
      var self = this;
      var formatField = this.el;
      
      // Encontrar el campo de upload/URL en el mismo formulario
      var form = formatField.closest('form');
      var urlField = form.find('input[name$="__url"], input[name="url"]').first();
      var uploadField = form.find('input[type="file"][name$="__upload"], input[type="file"][name="upload"]').first();
      
      // Función para obtener la extensión de un archivo o URL
      function getFileExtension(filename) {
        if (!filename) return '';
        
        // Eliminar parámetros de consulta si es una URL
        filename = filename.split('?')[0];
        
        // Obtener la extensión
        var parts = filename.split('.');
        if (parts.length > 1) {
          return parts[parts.length - 1].toUpperCase();
        }
        return '';
      }
      
      // Función para actualizar el formato basado en la extensión
      function updateFormat(filename) {
        if (!filename || formatField.val()) return; // No sobrescribir si ya hay un valor
        
        var extension = getFileExtension(filename);
        if (extension) {
          // Mapeo de extensiones comunes a formatos
          var formatMap = {
            'CSV': 'CSV',
            'XLS': 'XLS',
            'XLSX': 'XLS',
            'JSON': 'JSON',
            'GEOJSON': 'GeoJSON',
            'XML': 'XML',
            'RDF': 'RDF',
            'TTL': 'Turtle',
            'N3': 'N3',
            'PDF': 'PDF',
            'DOC': 'DOC',
            'DOCX': 'DOC',
            'TXT': 'TXT',
            'SHP': 'SHP',
            'KML': 'KML',
            'KMZ': 'KMZ',
            'GPX': 'GPX',
            'ZIP': 'ZIP',
            'PNG': 'PNG',
            'JPG': 'JPEG',
            'JPEG': 'JPEG',
            'GIF': 'GIF',
            'TIF': 'TIFF',
            'TIFF': 'TIFF'
          };
          
          var format = formatMap[extension] || extension;
          formatField.val(format).trigger('change');
        }
      }
      
      // Escuchar cambios en el campo URL
      urlField.on('change blur', function() {
        updateFormat($(this).val());
      });
      
      // Escuchar cambios en el campo de upload
      uploadField.on('change', function() {
        var files = this.files;
        if (files && files.length > 0) {
          updateFormat(files[0].name);
        }
      });
      
      // También verificar si ya hay un valor en URL al cargar
      if (urlField.val() && !formatField.val()) {
        updateFormat(urlField.val());
      }
    }
  };
});