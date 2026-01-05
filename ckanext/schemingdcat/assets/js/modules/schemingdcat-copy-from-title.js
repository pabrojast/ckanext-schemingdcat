ckan.module('copy-from-title', function ($) {
  return {
    initialize: function () {
      var titleInput = $('input[name="title_translated-en"]');
      var identifierInput = this.el;
      var slugInput = $('input[name="name"]');

      if (!identifierInput.length || !slugInput.length) {
        return;
      }

      // Determinar si estamos en modo edición
      var isEditMode = window.location.href.indexOf('/edit/') !== -1;

      // Guardar valores iniciales en modo edición
      var initialValues = {};
      if (isEditMode) {
        initialValues.identifier = identifierInput.val();
        initialValues.slug = slugInput.val();
      }

      var syncing = false;

      function syncFromTitle() {
        var titleValue = titleInput.val();

        // En modo edición, solo actualizar si el campo estaba inicialmente vacío
        // En modo creación, actualizar siempre
        if (!isEditMode || !initialValues.identifier) {
          identifierInput.val(titleValue);
        }

        // En modo edición, solo actualizar el slug si estaba inicialmente vacío
        // En modo creación, actualizar siempre
        if (!isEditMode || !initialValues.slug) {
          syncing = true;
          slugInput.val(titleValue).trigger('change');
          syncing = false;
        }
      }

      function syncSlugFromIdentifier() {
        if (syncing) return;
        syncing = true;
        slugInput.val(identifierInput.val()).trigger('change');
        syncing = false;
      }

      function syncIdentifierFromSlug(value) {
        if (syncing) return;
        syncing = true;
        identifierInput.val(value);
        syncing = false;
      }

      // Usar 'input' para actualizar en tiempo real desde el titulo
      if (titleInput.length) {
        titleInput.on('input', syncFromTitle);
      }

      // Mantener identifier y slug acoplados en edicion manual
      identifierInput.on('input', syncSlugFromIdentifier);
      slugInput.on('slugify', function (event, currentValue) {
        syncIdentifierFromSlug(currentValue);
      });
      slugInput.on('change', function () {
        syncIdentifierFromSlug(slugInput.val());
      });
    }
  };
});
