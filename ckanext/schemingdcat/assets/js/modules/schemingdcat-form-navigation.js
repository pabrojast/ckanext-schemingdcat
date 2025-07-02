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
      
      // Manejar el envío del formulario para detectar conflictos de nombres
      $('form').on('submit', function(e) {
        if (self._isCreatingNewDataset()) {
          var potentialConflict = self._checkForNameConflict();
          if (potentialConflict) {
            e.preventDefault();
            self._resolveDuplicateName();
            return false;
          }
        }
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
     
     _resolveDuplicateName: function() {
       var self = this;
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
         
         // Enviar el formulario después de un breve delay
         setTimeout(function() {
           $nameField.closest('form').off('submit').submit();
         }, 1000);
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
       // Crear y mostrar mensaje informativo
       var message = $('<div class="alert alert-info" style="margin-top: 10px;">' +
         '<i class="fa fa-info-circle"></i> ' +
         'Se detectó un posible conflicto de nombre. Se ha generado un nombre único: <strong>' + newName + '</strong>' +
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
       // Esta función se ejecuta cuando detectamos navegación hacia atrás
       // Verificar si estamos en una situación potencial de conflicto
       if (this._isCreatingNewDataset()) {
         var self = this;
         var $nameField = $('input[name="name"]');
         var $titleField = $('input[name="title_translated-en"], input[name="title"]');
         
         if ($nameField.length && $titleField.length) {
           var currentName = $nameField.val();
           var currentTitle = $titleField.val();
           
           // Si tenemos datos que sugieren que ya estuvimos aquí antes,
           // verificar si existe un draft
           if (currentTitle && (!currentName || this._seemsAutoGenerated(currentName, currentTitle))) {
             var potentialName = currentName || this._generateSlugFromTitle(currentTitle);
             
             // Verificar si existe un draft con este nombre
             this._checkForExistingDraft(potentialName, function(exists, packageData) {
               if (exists && packageData) {
                 // Si existe un draft, preguntar al usuario si quiere continuar editándolo
                 self._handleExistingDraft(packageData);
               } else {
                 // Si no existe, generar un nombre único preventivamente
                 var timestamp = new Date().getTime();
                 var uniqueName = potentialName + '-' + timestamp;
                 $nameField.val(uniqueName);
               }
             });
           }
         }
       }
     },
     
     _checkForExistingDraft: function(packageName, callback) {
       // Verificar via API si existe un package con este nombre
       $.ajax({
         url: '/api/3/action/package_show',
         type: 'POST',
         data: JSON.stringify({id: packageName}),
         contentType: 'application/json',
         success: function(response) {
           if (response.success && response.result) {
             var pkg = response.result;
             // Verificar si es un draft
             if (pkg.state === 'draft') {
               callback(true, pkg);
             } else {
               callback(false, null);
             }
           } else {
             callback(false, null);
           }
         },
         error: function() {
           // Si hay error (ej. package no existe), callback false
           callback(false, null);
         }
       });
     },
     
     _handleExistingDraft: function(packageData) {
       var self = this;
       
       // Crear modal o mensaje para preguntar al usuario
       var modalHtml = 
         '<div class="modal fade" id="draft-exists-modal" tabindex="-1" role="dialog">' +
           '<div class="modal-dialog" role="document">' +
             '<div class="modal-content">' +
               '<div class="modal-header">' +
                 '<h4 class="modal-title">Borrador existente encontrado</h4>' +
               '</div>' +
               '<div class="modal-body">' +
                 '<p>Ya existe un borrador del dataset "<strong>' + packageData.title + '</strong>" con este nombre.</p>' +
                 '<p>¿Qué te gustaría hacer?</p>' +
               '</div>' +
               '<div class="modal-footer">' +
                 '<button type="button" class="btn btn-primary" id="continue-editing">Continuar editando el borrador</button>' +
                 '<button type="button" class="btn btn-default" id="create-new">Crear uno nuevo con nombre único</button>' +
               '</div>' +
             '</div>' +
           '</div>' +
         '</div>';
       
       // Remover modal anterior si existe
       $('#draft-exists-modal').remove();
       
       // Agregar modal al DOM
       $('body').append(modalHtml);
       
       // Mostrar modal
       $('#draft-exists-modal').modal('show');
       
       // Manejar clicks
       $('#continue-editing').on('click', function() {
         // Redirigir a la página de edición del draft existente
         var editUrl = '/dataset/edit/' + packageData.name;
         window.location.href = editUrl;
       });
       
       $('#create-new').on('click', function() {
         $('#draft-exists-modal').modal('hide');
         // Generar nombre único y continuar
         var timestamp = new Date().getTime();
         var newName = packageData.name + '-' + timestamp;
         $('input[name="name"]').val(newName);
         self._showDuplicateNameMessage(newName);
       });
     }
   };
}); 