ckan.module('schemingdcat-form-navigation', function ($) {
  return {
    initialize: function () {
      var self = this;
      
      // Ejecutar inmediatamente al cargar
      self._fixNavigationState();
      
      // Limpiar drafts antiguos
      self._cleanOldDrafts();
      
      // Debug: mostrar drafts actuales
      self._debugDrafts();
      
      // Rastrear si venimos de navegación hacia atrás
      self._trackNavigationState();
      
      // Detectar navegación del navegador (botón atrás/adelante)
      $(window).on('pageshow', function(event) {
        // Si la página viene de la caché del navegador
        if (event.originalEvent && event.originalEvent.persisted) {
          self._fixNavigationState();
          self._handleDuplicateNameIssue();
        }
      });
      
      // Para navegación con history API
      $(window).on('popstate', function(event) {
        setTimeout(function() {
          self._fixNavigationState();
          self._handleDuplicateNameIssue();
        }, 50);
      });
      
      // Detectar cuando se navega a una nueva página (para rastrear drafts)
      $(window).on('beforeunload', function() {
        self._saveDraftInfo();
      });
      
      // Guardar información del draft cuando se envía el formulario
      $('form').on('submit', function() {
        self._saveDraftInfo();
      });
      
      // Verificar inmediatamente si hay drafts existentes cuando carga la página
      setTimeout(function() {
        self._handleDuplicateNameIssue();
      }, 1000);
     
      // Comentar temporalmente la intercepción del formulario para evitar errores 400
      // TODO: Mejorar la lógica de detección de conflictos
      // $('form').on('submit', function(e) {
      //   if (self._isCreatingNewDataset()) {
      //     var potentialConflict = self._checkForNameConflict();
      //     if (potentialConflict) {
      //       e.preventDefault();
      //       self._generateUniqueNameOnSubmit();
      //       return false;
      //     }
      //   }
      // });
      
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
    },
    
    _isCreatingNewDataset: function() {
      // Detectar si estamos creando un nuevo dataset (no editando uno existente)
      return window.location.href.includes('/dataset/new') && 
             !window.location.href.includes('/edit/');
    },
    
    _checkForNameConflict: function() {
      // Verificar si puede haber un conflicto de nombres
      var $nameField = $('input[name="name"]');
      var $titleField = $('input[name="title_translated-en"], input[name="title"]');
      
      if ($nameField.length && $titleField.length) {
        var currentName = $nameField.val();
        var currentTitle = $titleField.val();
        
        // Si tenemos un título pero no un name, o si el name se deriva del título
        // existe potencial para conflicto si ya navegamos hacia atrás
        return !currentName || this._seemsAutoGenerated(currentName, currentTitle);
      }
      return false;
    },
    
    _seemsAutoGenerated: function(name, title) {
      if (!name || !title) return false;
      
      // Convertir título a slug simple para comparar
      var slugifiedTitle = title.toLowerCase()
        .replace(/[^a-z0-9\s-]/g, '')
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-')
        .replace(/^-|-$/g, '');
      
      return name === slugifiedTitle || name.startsWith(slugifiedTitle + '-');
    },
    
    _generateUniqueNameOnSubmit: function() {
      var $nameField = $('input[name="name"]');
      var $titleField = $('input[name="title_translated-en"], input[name="title"]');
      
      if ($nameField.length && $titleField.length) {
        var originalName = $nameField.val();
        var title = $titleField.val();
        
        // Generar un nuevo nombre único agregando timestamp
        var timestamp = new Date().getTime();
        var newName = originalName ? originalName + '-' + timestamp : 
                     this._generateSlugFromTitle(title) + '-' + timestamp;
        
        // Actualizar el campo de nombre
        $nameField.val(newName);
        
        // Mostrar mensaje informativo al usuario
        this._showDuplicateNameMessage(newName);
        
        // Reenviar el formulario sin la prevención
        setTimeout(function() {
          $nameField.closest('form')[0].submit();
        }, 500);
      }
    },
    
    _generateSlugFromTitle: function(title) {
      if (!title) return 'dataset';
      
      return title.toLowerCase()
        .replace(/[^a-z0-9\s-]/g, '')
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-')
        .replace(/^-|-$/g, '');
    },
    
    _showDuplicateNameMessage: function(newName) {
      this._showSimpleMessage('Se detectó un posible conflicto de nombre. Se ha generado un nombre único: ' + newName);
    },
    
    _showSimpleMessage: function(messageText) {
      console.log('Showing message:', messageText);
      
      // Crear y mostrar mensaje informativo
      var message = $('<div class="alert alert-info" style="margin-top: 10px; z-index: 9999; position: relative;">' +
        '<i class="fa fa-info-circle"></i> ' + messageText +
        '</div>');
      
      // Intentar agregarlo a varios lugares posibles
      var $targetContainer = $('.form-group').first();
      if (!$targetContainer.length) {
        $targetContainer = $('.form-actions');
      }
      if (!$targetContainer.length) {
        $targetContainer = $('form');
      }
      if (!$targetContainer.length) {
        $targetContainer = $('body');
      }
      
      if ($targetContainer.length) {
        // Remover mensajes anteriores
        $('.alert-info').remove();
        // Agregar nuevo mensaje
        $targetContainer.prepend(message);
        
        // Auto-remover el mensaje después de 8 segundos
        setTimeout(function() {
          message.fadeOut();
        }, 8000);
      }
    },
    
    _cleanOldDrafts: function() {
      try {
        var recentDrafts = JSON.parse(localStorage.getItem('recentDrafts') || '{}');
        var now = new Date().getTime();
        var cleaned = {};
        
        for (var draftName in recentDrafts) {
          var draftInfo = recentDrafts[draftName];
          // Mantener drafts de las últimas 48 horas
          if (now - draftInfo.created < 48 * 60 * 60 * 1000) {
            cleaned[draftName] = draftInfo;
          }
        }
        
        localStorage.setItem('recentDrafts', JSON.stringify(cleaned));
      } catch (e) {
        console.log('Error cleaning old drafts:', e);
      }
    },
    
    _debugDrafts: function() {
      try {
        var recentDrafts = JSON.parse(localStorage.getItem('recentDrafts') || '{}');
        console.log('Current drafts in localStorage:', recentDrafts);
        return recentDrafts;
      } catch (e) {
        console.log('Error reading drafts:', e);
        return {};
      }
    },
    
    _handleDuplicateNameIssue: function() {
      console.log('Checking for duplicate name issue. Current URL:', window.location.pathname);
      
      // Verificar si estamos en la página inicial de creación de dataset
      if (this._isCreatingNewDataset() && window.location.pathname === '/dataset/new') {
        var self = this;
        
        // Verificar después de un pequeño delay para permitir que el DOM se cargue
        setTimeout(function() {
          var $nameField = $('input[name="name"]');
          var $titleField = $('input[name="title_translated-en"], input[name="title"]');
          
          console.log('Fields found - name:', $nameField.length, 'title:', $titleField.length);
          
          if ($nameField.length && $titleField.length) {
            var currentName = $nameField.val();
            var currentTitle = $titleField.val();
            
            console.log('Current values - name:', currentName, 'title:', currentTitle);
            
            // Si tenemos un título, verificar por draft existente
            if (currentTitle) {
              var baseName = self._getBaseName(currentName) || self._generateSlugFromTitle(currentTitle);
              console.log('Generated base name:', baseName);
              
              // Verificar en localStorage si existe un draft reciente con este nombre
              self._checkRecentDrafts(baseName, function(foundDraft) {
                if (foundDraft) {
                  console.log('Found existing draft:', foundDraft);
                  self._redirectToExistingDraft(foundDraft);
                } else {
                  console.log('No existing draft found for:', baseName);
                }
              });
            }
          }
        }, 500);
      }
    },
    
    _detectPotentialBackNavigation: function() {
      // Detectar navegación hacia atrás por otros medios
      var $nameField = $('input[name="name"]');
      if ($nameField.length) {
        var currentName = $nameField.val();
        // Si el nombre ya tiene timestamps, probablemente venimos de navegación hacia atrás
        return this._hasTimestamp(currentName);
      }
      return false;
    },
    
    _hasTimestamp: function(name) {
      if (!name) return false;
      // Verificar si el nombre contiene timestamps (números largos al final)
      return /-\d{13,}/.test(name);
    },
    
    _getBaseName: function(currentName) {
      if (!currentName) return null;
      
      // Remover timestamps del final (números largos al final precedidos por guión)
      var cleanName = currentName.replace(/-\d{13,}(-\d{13,})*$/, '');
      return cleanName === currentName ? currentName : cleanName;
    },
    
    _checkRecentDrafts: function(baseName, callback) {
      try {
        var recentDrafts = JSON.parse(localStorage.getItem('recentDrafts') || '{}');
        
        // Buscar draft por nombre exacto primero
        if (recentDrafts[baseName]) {
          var draftInfo = recentDrafts[baseName];
          var now = new Date().getTime();
          // Verificar si el draft es reciente (últimas 24 horas)
          if (now - draftInfo.created < 24 * 60 * 60 * 1000) {
            callback(draftInfo);
            return;
          }
        }
        
        // Buscar por nombre base (removiendo timestamps)
        for (var draftName in recentDrafts) {
          var draftBaseName = this._getBaseName(draftName);
          if (draftBaseName === baseName) {
            var draftInfo = recentDrafts[draftName];
            var now = new Date().getTime();
            if (now - draftInfo.created < 24 * 60 * 60 * 1000) {
              callback(draftInfo);
              return;
            }
          }
        }
      } catch (e) {
        console.log('Error checking recent drafts:', e);
      }
      
      // No se encontró ningún draft
      callback(null);
    },
    
    _redirectToExistingDraft: function(draftInfo) {
      var currentUrlPath = window.location.pathname;
      var draftName = draftInfo.name || draftInfo.baseName;
      
      // Si ya estamos en la URL correcta, no hacer nada
      if (currentUrlPath.includes('/dataset/new/' + draftName)) {
        this._showSimpleMessage('Continuando con el borrador existente: ' + draftName);
        return;
      }
      
      // Construir URL de edición para el draft existente (página 1)
      var editUrl = '/dataset/new/' + draftName + '/1';
      
      this._showSimpleMessage('Se encontró un borrador existente. Redirigiendo a: ' + draftName + '...');
      setTimeout(function() {
        window.location.href = editUrl;
      }, 2000);
    },
    
    _getCurrentPageNumber: function() {
      // Obtener número de página actual desde la URL o desde elementos del DOM
      var urlPath = window.location.pathname;
      var match = urlPath.match(/\/dataset\/new\/[^\/]+\/(\d+)/);
      
      if (match && match[1]) {
        return parseInt(match[1]);
      }
      
      // Si no hay número en la URL, intentar detectar desde los stages activos
      var $activeStage = $('.stages li.active');
      if ($activeStage.length) {
        var $allStages = $('.stages li');
        return $allStages.index($activeStage) + 1;
      }
      
      return 1; // Por defecto página 1
    },
    
    _trackNavigationState: function() {
      // Verificar si venimos de navegación hacia atrás
      var navigationEntries = performance.getEntriesByType('navigation');
      if (navigationEntries.length > 0) {
        var navEntry = navigationEntries[0];
        if (navEntry.type === 'back_forward') {
          // El usuario usó navegación hacia atrás/adelante
          sessionStorage.setItem('cameFromBackNav', 'true');
        }
      }
      
      // También verificar si hay parámetros que indican navegación hacia atrás
      var referrer = document.referrer;
      var currentUrl = window.location.href;
      if (referrer && referrer.includes('/dataset/new/') && currentUrl.includes('/dataset/new')) {
        sessionStorage.setItem('cameFromBackNav', 'true');
      }
    },
    
    _saveDraftInfo: function() {
      var $nameField = $('input[name="name"]');
      var $titleField = $('input[name="title_translated-en"], input[name="title"]');
      var $idField = $('input[name="id"]');
      
      if ($nameField.length && $nameField.val() && $titleField.length && $titleField.val()) {
        try {
          var recentDrafts = JSON.parse(localStorage.getItem('recentDrafts') || '{}');
          var draftName = $nameField.val();
          var baseName = this._getBaseName(draftName) || draftName;
          
          // Guardar tanto por nombre completo como por nombre base
          var draftData = {
            name: draftName,
            baseName: baseName,
            title: $titleField.val(),
            id: $idField.length ? $idField.val() : null,
            created: new Date().getTime(),
            url: window.location.pathname,
            lastPage: this._getCurrentPageNumber()
          };
          
          recentDrafts[draftName] = draftData;
          recentDrafts[baseName] = draftData;
          
          localStorage.setItem('recentDrafts', JSON.stringify(recentDrafts));
          console.log('Draft info saved:', draftData);
        } catch (e) {
          console.log('Error saving draft info:', e);
        }
      }
    },
    
    _cameFromBackNavigation: function() {
      var cameFromBack = sessionStorage.getItem('cameFromBackNav');
      sessionStorage.removeItem('cameFromBackNav'); // Limpiar después de verificar
      return cameFromBack === 'true';
    }
  };
}); 