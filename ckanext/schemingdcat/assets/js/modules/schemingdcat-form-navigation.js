ckan.module('schemingdcat-form-navigation', function ($) {
  return {
    initialize: function () {
      var self = this;
      
      // Ejecutar inmediatamente al cargar
      self._fixNavigationState();
      
      // Detectar navegación del navegador (botón atrás/adelante)
      $(window).on('pageshow', function(event) {
        // Si la página viene de la caché del navegador
        if (event.originalEvent && event.originalEvent.persisted) {
          self._fixNavigationState();
        }
      });
      
      // Para navegación con history API
      $(window).on('popstate', function(event) {
        setTimeout(function() {
          self._fixNavigationState();
        }, 50);
      });
      
      // Verificar estado periódicamente para casos edge
      setInterval(function() {
        self._checkButtonState();
      }, 1000);
    },
    
    _fixNavigationState: function() {
      var self = this;
      
      // Encontrar todos los botones de envío del formulario
      var $buttons = $('button[type="submit"], input[type="submit"]').filter(function() {
        var text = $(this).text() || $(this).val() || '';
        return text.toLowerCase().includes('next') || 
               text.toLowerCase().includes('siguiente') ||
               text.toLowerCase().includes('update') ||
               text.toLowerCase().includes('actualizar');
      });
      
      if ($buttons.length === 0) {
        // Buscar botones por clase o contexto
        $buttons = $('.btn-primary[type="submit"], .form-actions button[type="submit"]');
      }
      
      $buttons.each(function() {
        var $button = $(this);
        var $form = $button.closest('form');
        
        // Asegurar que el botón esté habilitado
        $button.prop('disabled', false);
        $button.removeClass('disabled');
        $button.attr('disabled', false);
        $button.removeAttr('disabled');
        
        // Asegurar visibilidad
        $button.show();
        $button.css({
          'visibility': 'visible',
          'display': '',
          'opacity': '1'
        });
        
        // Verificar si estamos en un formulario multi-página
        self._updatePageNavigationState($button);
      });
    },
    
    _updatePageNavigationState: function($button) {
      // Verificar si estamos en una página intermedia del formulario
      var $stages = $('.stages.stage-1');
      if ($stages.length > 0) {
        var $activeStage = $stages.find('li.active');
        var $allStages = $stages.find('li');
        var activeIndex = $allStages.index($activeStage);
        var totalStages = $allStages.length;
        
        // Si no estamos en la última etapa, el botón debe estar disponible
        if (activeIndex >= 0 && activeIndex < totalStages - 1) {
          $button.prop('disabled', false);
          $button.removeClass('disabled btn-disabled');
          $button.removeAttr('disabled');
          
          // Específicamente para el botón "Next"
          var buttonText = $button.text() || $button.val() || '';
          if (buttonText.toLowerCase().includes('next') || 
              buttonText.toLowerCase().includes('siguiente')) {
            $button.show();
            $button.css('visibility', 'visible');
          }
        }
      }
    },
    
    _checkButtonState: function() {
      // Verificación periódica para asegurar que el botón no se bloquee
      var $form = $('form[data-module], form.dataset-form');
      if ($form.length) {
        var $submitButton = $form.find('button[type="submit"], input[type="submit"]').first();
        
        if ($submitButton.length && $submitButton.is(':disabled')) {
          // Si el botón está deshabilitado, verificar si debería estarlo
          var hasVisibleErrors = $form.find('.error:visible, .alert-error:visible').length > 0;
          
          if (!hasVisibleErrors) {
            // No hay errores visibles, habilitar el botón
            $submitButton.prop('disabled', false);
            $submitButton.removeClass('disabled');
            $submitButton.removeAttr('disabled');
          }
        }
      }
    }
  };
}); 