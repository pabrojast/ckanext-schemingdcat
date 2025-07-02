ckan.module('schemingdcat-simple-navigation', function ($) {
  return {
    initialize: function () {
      var self = this;
      console.log('Simple navigation module initialized');
      
      // Ejecutar inmediatamente
      self._checkForExistingDraft();
      
      // Verificar periódicamente
      setInterval(function() {
        self._ensureButtonEnabled();
      }, 1000);
      
      // Detectar navegación hacia atrás
      $(window).on('pageshow', function(event) {
        if (event.originalEvent && event.originalEvent.persisted) {
          setTimeout(function() {
            self._checkForExistingDraft();
          }, 500);
        }
      });
      
      // Guardar información del draft cuando se envía formulario
      $('form').on('submit', function() {
        self._saveDraftInfo();
      });
    },
    
    _checkForExistingDraft: function() {
      console.log('Checking for existing draft...');
      
      // Solo en página inicial de dataset/new
      if (window.location.pathname !== '/dataset/new') {
        return;
      }
      
      var self = this;
      setTimeout(function() {
        var $titleField = $('input[name="title_translated-en"], input[name="title"]');
        
        if ($titleField.length && $titleField.val()) {
          var title = $titleField.val();
          var slug = self._generateSlug(title);
          
          console.log('Title found:', title, 'Generated slug:', slug);
          
          // Verificar si existe draft con este slug
          self._checkLocalStorageForDraft(slug, function(foundDraft) {
            if (foundDraft) {
              console.log('Found existing draft:', foundDraft);
              self._redirectToDraft(foundDraft);
            }
          });
        }
      }, 1000);
    },
    
    _generateSlug: function(title) {
      return title.toLowerCase()
        .replace(/[^a-z0-9\s-]/g, '')
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-')
        .replace(/^-|-$/g, '');
    },
    
    _checkLocalStorageForDraft: function(slug, callback) {
      try {
        var drafts = JSON.parse(localStorage.getItem('schemingdcat_drafts') || '{}');
        var now = new Date().getTime();
        
        // Buscar draft por slug
        for (var draftSlug in drafts) {
          if (draftSlug === slug || draftSlug.startsWith(slug + '-')) {
            var draft = drafts[draftSlug];
            // Solo considerar drafts de las últimas 24 horas
            if (now - draft.created < 24 * 60 * 60 * 1000) {
              callback(draft);
              return;
            }
          }
        }
        
        callback(null);
      } catch (e) {
        console.log('Error checking localStorage:', e);
        callback(null);
      }
    },
    
    _redirectToDraft: function(draft) {
      var message = 'Se encontró un borrador existente: "' + draft.title + '"<br>' +
                   'Redirigiendo en 3 segundos...<br>' +
                   '<small>Si no deseas continuar con este borrador, recarga la página.</small>';
      
      this._showMessage(message, 'warning');
      
      setTimeout(function() {
        window.location.href = '/dataset/new/' + draft.slug + '/1';
      }, 3000);
    },
    
    _saveDraftInfo: function() {
      var $titleField = $('input[name="title_translated-en"], input[name="title"]');
      var $nameField = $('input[name="name"]');
      
      if ($titleField.length && $titleField.val() && $nameField.length && $nameField.val()) {
        try {
          var drafts = JSON.parse(localStorage.getItem('schemingdcat_drafts') || '{}');
          var slug = $nameField.val();
          
          drafts[slug] = {
            slug: slug,
            title: $titleField.val(),
            created: new Date().getTime(),
            url: window.location.pathname
          };
          
          localStorage.setItem('schemingdcat_drafts', JSON.stringify(drafts));
          console.log('Draft saved:', drafts[slug]);
        } catch (e) {
          console.log('Error saving draft:', e);
        }
      }
    },
    
    _ensureButtonEnabled: function() {
      var $submitButton = $('button[type="submit"], input[type="submit"]').filter(function() {
        var text = $(this).text() || $(this).val() || '';
        return text.toLowerCase().includes('next') || text.toLowerCase().includes('siguiente');
      });
      
      if ($submitButton.length && $submitButton.is(':disabled')) {
        // Verificar si realmente debería estar deshabilitado
        var $form = $submitButton.closest('form');
        var hasErrors = $form.find('.error:visible').length > 0;
        
        if (!hasErrors) {
          $submitButton.prop('disabled', false);
          $submitButton.removeClass('disabled');
          $submitButton.removeAttr('disabled');
        }
      }
    },
    
    _showMessage: function(message, type) {
      type = type || 'info';
      var alertClass = 'alert-' + type;
      
      var $message = $('<div class="alert ' + alertClass + '" style="margin: 20px 0; padding: 15px; border-radius: 4px;">' +
        '<i class="fa fa-info-circle"></i> ' + message +
        '</div>');
      
      // Remover mensajes anteriores
      $('.alert').remove();
      
      // Agregar al inicio del formulario o body
      var $target = $('form').first();
      if (!$target.length) {
        $target = $('body');
      }
      
      $target.prepend($message);
    }
  };
}); 