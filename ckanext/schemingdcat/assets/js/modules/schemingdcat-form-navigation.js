ckan.module('schemingdcat-form-navigation', function ($) {
  return {
    initialize: function () {
      var self = this;
      
             // Ejecutar inmediatamente al cargar
       self._fixNavigationState();
       
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
       // Crear y mostrar mensaje informativo
       var message = $('<div class="alert alert-info" style="margin-top: 10px;">' +
         '<i class="fa fa-info-circle"></i> ' + messageText +
         '</div>');
       
       var $nameField = $('input[name="name"]');
       if ($nameField.length) {
         // Remover mensajes anteriores
         $nameField.closest('.form-group').find('.alert-info').remove();
         // Agregar nuevo mensaje
         $nameField.closest('.form-group').append(message);
         
         // Auto-remover el mensaje después de 5 segundos
         setTimeout(function() {
           message.fadeOut();
         }, 5000);
       }
     },
     
          _handleDuplicateNameIssue: function() {
       // Solo procesar si realmente venimos de navegación hacia atrás
       if (!this._cameFromBackNavigation() && !this._detectPotentialBackNavigation()) {
         return;
       }
       
       // Verificar si estamos en una situación potencial de conflicto
       if (this._isCreatingNewDataset()) {
         var self = this;
         var $nameField = $('input[name="name"]');
         var $titleField = $('input[name="title_translated-en"], input[name="title"]');
         
         if ($nameField.length && $titleField.length) {
           var currentName = $nameField.val();
           var currentTitle = $titleField.val();
           
           // Si tenemos datos que sugieren que ya estuvimos aquí antes
           if (currentTitle && (!currentName || this._seemsAutoGenerated(currentName, currentTitle))) {
             var baseName = this._getBaseName(currentName) || this._generateSlugFromTitle(currentTitle);
             
             // Intentar encontrar si ya existe un draft con este nombre base
             this._findExistingDraft(baseName, function(foundDraft) {
               if (foundDraft) {
                 // Redirigir a la página de edición del draft existente
                 self._redirectToExistingDraft(foundDraft);
               } else {
                 // Solo generar nombre único si no encontramos draft existente
                 // Y solo si el nombre actual ya tiene timestamps (evitar agregar múltiples)
                 if (self._hasTimestamp(currentName)) {
                   self._showSimpleMessage('Detectado nombre con timestamp múltiple, manteniendo: ' + currentName);
                 } else {
                   var timestamp = new Date().getTime();
                   var uniqueName = baseName + '-' + timestamp;
                   $nameField.val(uniqueName);
                   self._showSimpleMessage('Se ha generado un nombre único: ' + uniqueName);
                 }
               }
             });
           }
         }
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
     
     _findExistingDraft: function(baseName, callback) {
       var self = this;
       
       // Verificar si estamos en el contexto de un draft existente
       var urlPath = window.location.pathname;
       var match = urlPath.match(/\/dataset\/new\/([^\/]+)/);
       
       if (match && match[1]) {
         var urlDatasetName = match[1];
         var urlBaseName = this._getBaseName(urlDatasetName);
         
         // Si el nombre base de la URL coincide con el que estamos buscando
         if (urlBaseName === baseName) {
           callback({
             name: urlBaseName,
             isExisting: true
           });
           return;
         }
       }
       
       // Usar una técnica más segura: verificar si hay un input hidden con el dataset ID
       var $datasetIdField = $('input[name="id"]');
       if ($datasetIdField.length && $datasetIdField.val()) {
         // Si hay un ID, significa que estamos editando un draft existente
         var datasetId = $datasetIdField.val();
         callback({
           name: baseName,
           id: datasetId,
           isExisting: true
         });
         return;
       }
       
       // Verificar en localStorage si tenemos información sobre drafts recientes
       try {
         var recentDrafts = JSON.parse(localStorage.getItem('recentDrafts') || '{}');
         if (recentDrafts[baseName]) {
           var draftInfo = recentDrafts[baseName];
           // Verificar si el draft es reciente (últimas 24 horas)
           var now = new Date().getTime();
           if (now - draftInfo.created < 24 * 60 * 60 * 1000) {
             callback({
               name: baseName,
               isExisting: true,
               fromStorage: true
             });
             return;
           }
         }
       } catch (e) {
         // Ignorar errores de localStorage
       }
       
       // Si no encontramos evidencia clara de un draft existente
       callback(null);
     },
     
     _redirectToExistingDraft: function(draftInfo) {
       var currentUrl = window.location.href;
       var currentPage = this._getCurrentPageNumber();
       
       // Si ya estamos en la URL correcta, no hacer nada
       var currentUrlPath = window.location.pathname;
       if (currentUrlPath.includes('/dataset/new/' + draftInfo.name)) {
         // Ya estamos en el draft correcto, solo mostrar mensaje
         this._showSimpleMessage('Continuando con el borrador existente: ' + draftInfo.name);
         return;
       }
       
       // Construir URL de edición para el draft existente
       var editUrl = '/dataset/new/' + draftInfo.name;
       if (currentPage > 1) {
         editUrl += '/' + currentPage;
       }
       
       this._showSimpleMessage('Redirigiendo al borrador existente: ' + draftInfo.name + '...');
       setTimeout(function() {
         window.location.href = editUrl;
       }, 1500);
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
       if (this._isCreatingNewDataset()) {
         var $nameField = $('input[name="name"]');
         var $titleField = $('input[name="title_translated-en"], input[name="title"]');
         var $idField = $('input[name="id"]');
         
         if ($nameField.length && $nameField.val() && $titleField.length && $titleField.val()) {
           try {
             var recentDrafts = JSON.parse(localStorage.getItem('recentDrafts') || '{}');
             var baseName = this._getBaseName($nameField.val()) || $nameField.val();
             
             recentDrafts[baseName] = {
               name: $nameField.val(),
               title: $titleField.val(),
               id: $idField.length ? $idField.val() : null,
               created: new Date().getTime(),
               url: window.location.pathname
             };
             
             localStorage.setItem('recentDrafts', JSON.stringify(recentDrafts));
           } catch (e) {
             // Ignorar errores de localStorage
           }
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