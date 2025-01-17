ckan.module('publisher-uri-field', function ($) {
  return {
    initialize: function () {
      var self = this;
      var orgSelect = $('select[name="owner_org"]');
      var domainBase = $('#publisher-uri-domain').val();
      
      // Actualizar el URI cuando cambia la organización
      orgSelect.on('change', function() {
        var orgId = $(this).val();
        if (orgId) {
          self.el.val(domainBase + orgId);
        } else {
          self.el.val('');
        }
      });
      
      // Establecer el valor inicial si hay una organización seleccionada
      var initialOrgId = orgSelect.val();
      if (initialOrgId) {
        self.el.val(domainBase + initialOrgId);
      }
    }
  };
}); 