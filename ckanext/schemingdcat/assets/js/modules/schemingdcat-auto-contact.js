"use strict";

ckan.module('auto-contact', function ($) {
  return {
    initialize: function () {
      try {
        // Solo realizamos acciones en modo de creación, no en edición
        if (window.location.href.indexOf('/edit/') === -1) {
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
      // Rellenar campos solo si están vacíos y si tenemos datos del usuario
      this._fillFieldIfEmpty('input[name="contact_email"]', userData.email);
      this._fillFieldIfEmpty('input[name="publisher_email"]', userData.email);
      this._fillFieldIfEmpty('input[name="maintainer_email"]', userData.email);
      this._fillFieldIfEmpty('input[name="author_email"]', userData.email);
      
      this._fillFieldIfEmpty('input[name="contact_name"]', userData.name);
      this._fillFieldIfEmpty('input[name="maintainer"]', userData.name);
      this._fillFieldIfEmpty('input[name="author"]', userData.name);
      
      this._fillFieldIfEmpty('input[name="contact_url"]', userData.url);
    },
    
    _fillFieldIfEmpty: function(selector, value) {
      if (!value) return; // No hacemos nada si no hay valor para rellenar
      
      const field = $(selector);
      // Solo rellenamos si el campo existe, está vacío y tenemos un valor para rellenar
      if (field.length && !field.val().trim()) {
        // Establecemos el valor directamente sin disparar eventos
        field[0].value = value;
      }
    }
  };
});