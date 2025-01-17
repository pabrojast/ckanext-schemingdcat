"use strict";

ckan.module('auto-contact', function ($) {
  return {
    initialize: function () {
      try {
        // Obtener los datos del usuario del campo oculto
        const userData = JSON.parse($('#current-user-data').val());
        if (userData) {
          this._fillContactFields(userData);
        }
      } catch (e) {
        console.warn('No se pudo obtener información del usuario actual:', e);
      }
    },

    _fillContactFields: function (userData) {
      // Rellenar el campo de email
      const emailField = $('input[name="contact_email"]');
      if (emailField.length && !emailField.val() && userData.email) {
        emailField.val(userData.email);
      }
      const emailField2 = $('input[name="publisher_email"]');
      if (emailField2.length && !emailField2.val() && userData.email) {
        emailField2.val(userData.email);
      }
      const emailField3 = $('input[name="maintainer_email"]');
      if (emailField3.length && !emailField3.val() && userData.email) {
        emailField3.val(userData.email);
      }
      const emailField4 = $('input[name="author_email"]');
      if (emailField4.length && !emailField4.val() && userData.email) {
        emailField4.val(userData.email);
      }

      // Rellenar el campo de nombre
      const nameField = $('input[name="contact_name"]');
      if (nameField.length && !nameField.val() && userData.name) {
        nameField.val(userData.name);
      }
      const nameField3 = $('input[name="maintainer"]');
      if (nameField3.length && !nameField3.val() && userData.name) {
        nameField3.val(userData.name);
      }
      const nameField4 = $('input[name="author"]');
      if (nameField4.length && !nameField4.val() && userData.name) {
        nameField4.val(userData.name);
      }

      // Rellenar el campo de url
      const urlField = $('input[name="contact_url"]');
      if (urlField.length && !urlField.val() && userData.url) {
        urlField.val(userData.url);
      }
    }
  };
});