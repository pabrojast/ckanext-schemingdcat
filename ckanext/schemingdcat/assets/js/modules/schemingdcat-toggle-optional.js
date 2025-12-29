ckan.module('toggle-optional', function ($) {
  return {
    initialize: function () {
      var self = this;
      
      // Ocultar loader y mostrar contenido cuando el JS está listo
      $('#form-loading').hide();
      $('#form-fields-container').css('visibility', 'visible');
      
      // Crear el campo oculto para el modo
      var $hiddenInput = $('<input>', {
        type: 'hidden',
        name: 'form_mode',
        id: 'form_mode',
        value: 'basic' // valor por defecto
      }).appendTo(this.el);
      
      // Crear el botón toggle con ícono
      var $toggleBtn = $('<button>', {
        class: 'btn btn-default',
        style: 'margin-bottom: 20px;',
        html: '<i class="fa fa-cog"></i> Show Advanced & Metadata fields'
      });
      
      // Insertar el botón en el contenedor
      $(this.el).append($toggleBtn);
      
      // Lista de campos que siempre deben mostrarse (obligatorios)
      var requiredFields = [
        '[name="title_translated-en"]',
        '[name="notes_translated-en"]'
      ];
      
      // Lista de campos opcionales a ocultar
      var optionalFields = [
        '[name="title_translated-es"]',
        '[name="title_translated-fr"]',
        '[name="notes_translated-es"]',
        '[name="notes_translated-fr"]',
        '[name="graphic_overview"]',
        '[name="tag_uri"]',
        '[name="contact_uri"]',
        '[name="contact_url"]',
        '[name="language"]',
        '[name="dcat_type"]',
        '[name="theme_eu"]',
        '[name="hvd_category"]',
        '[name="topic"]',
        '[name="publisher_name"]',
        '[name="publisher_identifier"]',
        '[name="publisher_uri"]',
        '[name="publisher_email"]',
        '[name="publisher_url"]',
        '[name="publisher_type"]',
        '[name="maintainer"]',
        '[name="maintainer_uri"]',
        '[name="maintainer_email"]',
        '[name="maintainer_url"]',
        '[name="author"]',
        '[name="author_uri"]',
        '[name="author_email"]',
        '[name="author_url"]',
        '[name="alternate_identifier"]',
        '[name="provenance-es"]',
        '[name="provenance-fr"]',
        '[name="provenance-en"]',
        '[name="conforms_to"]',
        '[name="metadata_profile"]',
        '[name="temporal_start"]',
        '[name="temporal_end"]',
        '[name="frequency"]',
        '[name="lineage_source"]',
        '[name="source"]',
        '[name="lineage_process_steps-es"]',
        '[name="lineage_process_steps-fr"]',
        '[name="lineage_process_steps-en"]',
        '[name="lineage_process_steps"]',
        '[name="reference"]',
        '[name="purpose-es"]',
        '[name="purpose-en"]',
        '[name="purpose-fr"]',
        '[name="unesdocurl"]',
        '[name="unesdocimage"]',
        '[name="encoding"]',
        '[name="license_id"]',
        '[name="access_rights"]',
        '[name="version"]',
        '[name="version_notes-es"]',
        '[name="version_notes-fr"]',
        '[name="version_notes-en"]',
        '[name="valid"]',
        '[name="theme"]',
        '[name="inspire_id"]',
        '[name="representation_type"]',
        '[name="spatial"]',
        // Nuevos campos de metadatos comprensivos (se ocultan por defecto)
        '[name="spatial_crs"]',
        '[name="spatial_resolution"]',
        '[name="feature_count"]',
        '[name="geometry_type"]',
        '[name="data_fields"]',
        '[name="data_statistics"]',
        '[name="data_domains"]',
        '[name="geographic_coverage"]',
        '[name="administrative_boundaries"]',
        '[name="file_created_date"]',
        '[name="file_modified_date"]',
        '[name="data_temporal_coverage"]',
        '[name="file_size_bytes"]',
        '[name="compression_info"]',
        '[name="format_version"]',
        '[name="file_integrity"]',
        '[name="content_type_detected"]',
        '[name="document_pages"]',
        '[name="spreadsheet_sheets"]',
        '[name="text_content_info"]',
        '[name="spatial_extent"]'
      ];
      
      // Añadir los grupos completos a ocultar
      var optionalGroups = [
        '.publisher-group.card2.mb-3',
        '.maintainer-group.card2.mb-3', 
        '.author-group.card2.mb-3',
        '.standards-group.card2.mb-3',
        '.lineage-group.card2.mb-3',
        '.temporal_info-group.card2.mb-3',
        '.purpose-group.card2.mb-3',
        '.unesdoc-group.card2.mb-3',
        '.license_info-group.card2.mb-3',
        '.version_notes-group.card2.mb-3',
        // Nuevos grupos de metadatos comprensivos (se ocultan por defecto)
        '.spatial_info-group.card2.mb-3',
        '.data_info-group.card2.mb-3',
        '.geographic_info-group.card2.mb-3',
        '.technical_info-group.card2.mb-3',
        '.content_info-group.card2.mb-3'
      ];
      
      // Identificar campos opcionales específicos y sus contenedores
      var $optionalFields = $('.form-group').filter(function() {
        var $field = $(this).find(optionalFields.join(','));
        var $required = $(this).find(requiredFields.join(','));
        return $field.length > 0 && $required.length === 0;
      });
      
      // Añadir los grupos opcionales al conjunto de elementos a ocultar
      var $optionalGroupElements = $(optionalGroups.join(','));
      var $allOptionalElements = $optionalFields.add($optionalGroupElements);
      
      // Ocultar campos opcionales por defecto
      $allOptionalElements.hide();
      
      // Manejar el click del botón
      $toggleBtn.on('click', function(e) {
        e.preventDefault();
        $(this).toggleClass('active');
        
        // Obtener todos los elementos de la lista de navegación
        var $navItems = $('.stages li');
        
        if ($(this).hasClass('active')) {
          $allOptionalElements.hide();
          $(this).html('<i class="fa fa-cog"></i> Show Advanced & Metadata fields');
          $hiddenInput.val('basic');
          
          // Ocultar los elementos de navegación correspondientes
          $navItems.each(function(index) {
            var text = $(this).text().trim().toLowerCase();
            if (text.includes('responsible party') || 
                text.includes('quality') || 
                text.includes('license info')) {
              $(this).hide();
            }
          });
          
        } else {
          $allOptionalElements.show();
          $(this).html('<i class="fa fa-cog"></i> Hide Advanced & Metadata fields');
          $hiddenInput.val('advanced');
          
          // Mostrar todos los elementos de navegación
          $navItems.show();
        }
      });
      
      // Modificar el trigger inicial para establecer el estado por defecto según la página actual
      var currentPage = $('.stages li.active').index();
      if (currentPage >= 10 && currentPage <= 20) {
        // Para páginas 2-4, iniciar en modo avanzado
        $toggleBtn.removeClass('active');
        $allOptionalElements.show();
        $toggleBtn.html('<i class="fa fa-cog"></i> Hide Advanced & Metadata fields');
        $hiddenInput.val('basic');
        $('.stages li').show();
      } else {
        // Para otras páginas, iniciar en modo básico
        $toggleBtn.addClass('active');
        $allOptionalElements.hide();
        $toggleBtn.html('<i class="fa fa-cog"></i> Show Advanced & Metadata fields');
        $hiddenInput.val('basic');
        
        // Ocultar los elementos de navegación correspondientes
        $('.stages li').each(function(index) {
          var text = $(this).text().trim().toLowerCase();
          if (text.includes('responsible party') || 
              text.includes('quality') || 
              text.includes('license info')) {
            $(this).hide();
          }
        });
      }
    }
  };
});