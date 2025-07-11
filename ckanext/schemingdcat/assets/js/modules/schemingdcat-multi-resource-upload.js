ckan.module('schemingdcat-multi-resource-upload', function ($) {
  return {
    initialize: function () {
      var self = this;
      
      console.log('[schemingdcat-multi-upload] Inicializando módulo de subida múltiple');

      // Permitir selección múltiple en todos los file inputs de resources
      self._enableMultipleSelection();
      
      // Añadir soporte para drag & drop múltiple
      self._enableMultipleDragDrop();

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
      
      // Mejorar el botón existente si ya está presente
      self._enhanceAddButton();
    },

    /* Añade atributo multiple a los inputs existentes (y futuros mediante delegación) */
    _enableMultipleSelection: function () {
      $('input[type="file"][id^="field-resource-upload"]').attr('multiple', 'multiple');
      console.log('[schemingdcat-multi-upload] Habilitada selección múltiple en inputs de archivo');
    },
    
    /* Habilita drag & drop múltiple en las zonas de subida */
    _enableMultipleDragDrop: function () {
      var self = this;
      
      // Buscar todas las zonas de upload existentes
      $('.upload-dropzone, .schemingdcat-upload-wrapper').each(function() {
        var $dropzone = $(this);
        
        $dropzone.on('drop', function(e) {
          var dt = e.originalEvent.dataTransfer;
          if (dt && dt.files && dt.files.length > 1) {
            e.preventDefault();
            e.stopPropagation();
            
            // Encontrar el input file asociado
            var $fileInput = $dropzone.find('input[type="file"]').first();
            if (!$fileInput.length) {
              $fileInput = $dropzone.closest('.form-group').find('input[type="file"]').first();
            }
            
            if ($fileInput.length) {
              console.log('[schemingdcat-multi-upload] Detectados ' + dt.files.length + ' archivos en drag & drop');
              self._handleMultipleFiles($fileInput, dt.files);
            }
          }
        });
      });
    },
    
    /* Mejora el botón de añadir recurso existente */
    _enhanceAddButton: function () {
      var $addBtn = this._findAddButton();
      if ($addBtn.length) {
        console.log('[schemingdcat-multi-upload] Botón "Añadir recurso" encontrado y mejorado');
        
        // Añadir icono si no lo tiene
        if (!$addBtn.find('i').length) {
          $addBtn.prepend('<i class="fa fa-plus"></i> ');
        }
        
        // Añadir tooltip
        $addBtn.attr('title', 'Haz clic para añadir otro recurso, o selecciona múltiples archivos arriba para crearlos automáticamente');
      }
    },
    
    /* Encuentra el botón de añadir recurso con mejor lógica */
    _findAddButton: function () {
      var selectors = [
        '#add-resource',
        '.add-resource',
        'button[data-module="add-resource"]',
        'button[data-action="add-resource"]',
        'button.resource-add',
        '.multi-resource-controls button'
      ];
      
      for (var i = 0; i < selectors.length; i++) {
        var $btn = $(selectors[i]);
        if ($btn.length) {
          console.log('[schemingdcat-multi-upload] Botón encontrado con selector: ' + selectors[i]);
          return $btn;
        }
      }
      
      console.warn('[schemingdcat-multi-upload] No se encontró ningún botón "Añadir recurso"');
      return $();
    },

    /* Gestiona la selección múltiple dividiendo los ficheros en varios bloques resource */
    _handleMultipleFiles: function ($originInput, files) {
      var filesArr = Array.prototype.slice.call(files);
      if (!filesArr.length) return;
      
      console.log('[schemingdcat-multi-upload] Procesando ' + filesArr.length + ' archivos');
      
      // Mostrar feedback visual
      this._showProcessingFeedback(filesArr.length);

      // Dejamos el primer fichero en el bloque actual
      var firstFile = filesArr.shift();
      this._setInputFile($originInput, firstFile);
      this._autoFillFields($originInput.closest('.resource-upload-field, .form-group'), firstFile);

      var self = this;
      var processed = 1;
      
      // Procesar archivos restantes con delay
      filesArr.forEach(function (file, index) {
        setTimeout(function() {
          self._addResourceWithFile(file, function() {
            processed++;
            self._updateProcessingFeedback(processed, filesArr.length + 1);
            
            if (processed === filesArr.length + 1) {
              self._hideProcessingFeedback();
              self._showSuccessFeedback(processed);
            }
          });
        }, (index + 1) * 300); // Delay escalonado para mejor UX
      });
    },

    /* Crea un nuevo bloque resource pulsando el botón estándar y rellena los datos */
    _addResourceWithFile: function (file, callback) {
      var self = this;
      var $addBtn = this._findAddButton();
      
      if (!$addBtn.length) {
        console.error('[schemingdcat-multi-upload] No se encontró el botón "Añadir recurso"');
        if (callback) callback(false);
        return;
      }

      $addBtn.trigger('click');

      // Esperamos a que el DOM se actualice con timeout más largo si es necesario
      var attempts = 0;
      var maxAttempts = 10;
      
      function tryFindNewResource() {
        attempts++;
        var $wrapper = $('.resource-upload-field').last();
        
        if ($wrapper.length) {
          var $fileInput = $wrapper.find('input[type="file"][id^="field-resource-upload"]');
          if ($fileInput.length) {
            // forzar multiple por si la plantilla no lo trae
            $fileInput.attr('multiple', 'multiple');
            self._setInputFile($fileInput, file);
            self._autoFillFields($wrapper, file);
            console.log('[schemingdcat-multi-upload] Recurso añadido exitosamente: ' + file.name);
            if (callback) callback(true);
            return;
          }
        }
        
        if (attempts < maxAttempts) {
          setTimeout(tryFindNewResource, 250);
        } else {
          console.error('[schemingdcat-multi-upload] No se pudo crear el nuevo recurso después de ' + maxAttempts + ' intentos');
          if (callback) callback(false);
        }
      }
      
      setTimeout(tryFindNewResource, 250);
    },

    /* Asigna un objeto File a un input mediante DataTransfer */
    _setInputFile: function ($input, file) {
      if (typeof DataTransfer !== 'undefined') {
        try {
          var dt = new DataTransfer();
          dt.items.add(file);
          $input[0].files = dt.files;
          
          // Trigger change event para que otros módulos respondan
          $input.trigger('change');
        } catch (err) {
          console.warn('[schemingdcat-multi-upload] DataTransfer no soportado en este navegador: ' + err.message);
        }
      }
    },

    /* Rellena automáticamente campos básicos (name, format, created) con mejor lógica */
    _autoFillFields: function ($wrapper, file) {
      // Nombre (sin extensión)
      var baseName = file.name.replace(/\.[^.]+$/, '');
      var $nameField = $wrapper.find('input[name$="name"], input[name*="name"]').first();
      if ($nameField.length && !$nameField.val()) {
        $nameField.val(baseName);
      }

      // Formato (extensión) con mapeo mejorado
      var ext = file.name.split('.').pop().toUpperCase();
      var formatMap = {
        'XLSX': 'XLS',
        'GEOJSON': 'GeoJSON',
        'JPEG': 'JPEG',
        'JPG': 'JPEG',
        'HTM': 'HTML',
        'TXT': 'TXT',
        'DOC': 'DOC',
        'DOCX': 'DOC',
        'PPT': 'PPT',
        'PPTX': 'PPT'
      };
      var format = formatMap[ext] || ext;
      
      var $formatField = $wrapper.find('input[name$="format"], input[name*="format"]').first();
      if ($formatField.length && !$formatField.val()) {
        $formatField.val(format);
      }

      // Fecha (created) si existe y está vacía
      var $created = $wrapper.find('input[name$="created"], input[name*="created"]').first();
      if ($created.length && !$created.val()) {
        var today = new Date().toISOString().slice(0, 10);
        $created.val(today);
      }
      
      // Descripción automática
      var $description = $wrapper.find('textarea[name$="description"], textarea[name*="description"]').first();
      if ($description.length && !$description.val()) {
        $description.val('Archivo subido: ' + file.name + ' (' + this._formatFileSize(file.size) + ')');
      }
    },
    
    /* Formatea el tamaño del archivo */
    _formatFileSize: function (bytes) {
      if (bytes === 0) return '0 Bytes';
      var k = 1024;
      var sizes = ['Bytes', 'KB', 'MB', 'GB'];
      var i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    /* Muestra feedback visual durante el procesamiento */
    _showProcessingFeedback: function (totalFiles) {
      var $feedback = $('<div class="multi-upload-feedback alert alert-info">' +
        '<i class="fa fa-spinner fa-spin"></i> ' +
        'Procesando ' + totalFiles + ' archivos...' +
        '<div class="progress" style="margin-top: 10px;">' +
        '<div class="progress-bar" style="width: 0%"></div>' +
        '</div>' +
        '</div>');
      
      $('.multi-resource-controls').after($feedback);
    },
    
    /* Actualiza el feedback del progreso */
    _updateProcessingFeedback: function (processed, total) {
      var percentage = (processed / total) * 100;
      $('.multi-upload-feedback .progress-bar').css('width', percentage + '%');
      $('.multi-upload-feedback').html(
        '<i class="fa fa-spinner fa-spin"></i> ' +
        'Procesando archivos: ' + processed + '/' + total +
        '<div class="progress" style="margin-top: 10px;">' +
        '<div class="progress-bar" style="width: ' + percentage + '%"></div>' +
        '</div>'
      );
    },
    
    /* Oculta el feedback de procesamiento */
    _hideProcessingFeedback: function () {
      setTimeout(function() {
        $('.multi-upload-feedback').fadeOut(500, function() {
          $(this).remove();
        });
      }, 1000);
    },
    
    /* Muestra feedback de éxito */
    _showSuccessFeedback: function (totalProcessed) {
      var $success = $('<div class="multi-upload-success alert alert-success">' +
        '<i class="fa fa-check"></i> ' +
        '¡Éxito! Se han creado ' + totalProcessed + ' recursos.' +
        '</div>');
      
      $('.multi-resource-controls').after($success);
      
      setTimeout(function() {
        $success.fadeOut(500, function() {
          $(this).remove();
        });
      }, 3000);
    }
  };
}); 