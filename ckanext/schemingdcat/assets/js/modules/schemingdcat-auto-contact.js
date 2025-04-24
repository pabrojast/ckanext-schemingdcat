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
          const userData = JSON.parse($('#current-user-data').val());
          if (userData) {
            this._fillContactFields(userData);
          }
        }
      } catch (e) {
        console.warn('No se pudo obtener información del usuario actual:', e);
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