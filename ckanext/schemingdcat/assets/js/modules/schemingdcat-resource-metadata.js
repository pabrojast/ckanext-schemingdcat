ckan.module('resource-metadata', function ($) {
  return {
    initialize: function () {
      var self = this;
      
      // Solo trabajar en formularios de recursos
      if (!this._isResourceForm()) {
        return;
      }
      
      // Crear botón para metadatos automáticos
      var $automaticBtn = $('<button>', {
        class: 'btn btn-info',
        style: 'margin-bottom: 20px; margin-left: 10px;',
        html: '<i class="fa fa-magic"></i> Show Automatic Metadata'
      });
      
      // Crear mensaje explicativo para metadatos automáticos
      var $automaticMessage = $('<div>', {
        class: 'alert alert-info',
        style: 'margin-bottom: 15px; display: none;',
        html: '<strong><i class="fa fa-info-circle"></i> Automatic Metadata:</strong><br>' +
              'These fields are automatically extracted when uploading files. ' +
              'If you manually edit any field, your value will be saved and that specific field will not be automatically processed.'
      });
      
      // Insertar botón y mensaje en el formulario
      $(this.el).prepend($automaticMessage);
      $(this.el).prepend($automaticBtn);
      
      // Grupo de metadatos automáticos
      var $automaticMetadataElements = $('.automatic_metadata-group.card2.mb-3');
      
      // Siempre ocultar metadatos automáticos por defecto
      $automaticMetadataElements.hide();
      
      // Manejar el click del botón de metadatos automáticos
      $automaticBtn.on('click', function(e) {
        e.preventDefault();
        $(this).toggleClass('active');
        
        if ($(this).hasClass('active')) {
          $automaticMetadataElements.show();
          $automaticMessage.show();
          $(this).html('<i class="fa fa-magic"></i> Hide Automatic Metadata');
        } else {
          $automaticMetadataElements.hide();
          $automaticMessage.hide();
          $(this).html('<i class="fa fa-magic"></i> Show Automatic Metadata');
        }
      });
    },
    
    _isResourceForm: function() {
      // Verificar si estamos en un formulario de recursos
      return window.location.pathname.includes('/resource/') || 
             window.location.pathname.includes('/new_resource') ||
             $('.resource-form').length > 0 ||
             $('[name*="resources"]').length > 0;
    }
  };
}); 