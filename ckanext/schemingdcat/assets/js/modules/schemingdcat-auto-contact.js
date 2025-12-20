"use strict";

ckan.module('auto-contact', function ($) {
  return {
    initialize: function () {
      try {
        // Determinar si estamos en modo edición
        var isEditMode = window.location.href.indexOf('/edit/') !== -1;
        
        // En modo edición, no autorellenamos nada
        if (!isEditMode) {
          // Obtener los datos del usuario del campo oculto
          var $userDataField = $('#current-user-data');
          var userDataValue = $userDataField.length ? $userDataField.val() : null;
          
          // Solo intentar parsear si hay un valor válido
          if (userDataValue && userDataValue !== 'undefined' && userDataValue.trim() !== '') {
            var userData = JSON.parse(userDataValue);
            if (userData) {
              this._fillContactFields(userData);
            }
          }
        }
      } catch (e) {
        // Solo mostrar warning si hay un error real de parseo, no si simplemente no hay datos
        if (e instanceof SyntaxError) {
          console.debug('Auto-contact: No user data available for auto-fill');
        } else {
          console.warn('Auto-contact error:', e);
        }
      }
    },

    _fillContactFields: function (userData) {
      // Rellenar el campo de email
      if (userData.email) {
        this._fillField('input[name="contact_email"]', userData.email);
        this._fillField('input[name="publisher_email"]', userData.email);
        this._fillField('input[name="maintainer_email"]', userData.email);
        this._fillField('input[name="author_email"]', userData.email);
      }
      
      // Rellenar el campo de nombre
      if (userData.name) {
        this._fillField('input[name="contact_name"]', userData.name);
        this._fillField('input[name="maintainer"]', userData.name);
        this._fillField('input[name="author"]', userData.name);
      }
      
      // Rellenar el campo de url
      if (userData.url) {
        this._fillField('input[name="contact_url"]', userData.url);
      }
    },
    
    _fillField: function(selector, value) {
      const field = $(selector);
      if (field.length && !field.val()) {
        field.val(value);
      }
    }
  };
});