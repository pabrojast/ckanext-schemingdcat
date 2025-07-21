this.ckan.module('schemingdcat-resource-auto-fields', function ($) {
  'use strict';

  return {
    options: {
      autoFields: [
        // Spatial info fields
        'spatial_crs', 'spatial_resolution', 'feature_count', 'geometry_type',
        // Data info fields  
        'data_fields', 'data_statistics', 'data_domains',
        // Geographic info fields
        'geographic_coverage', 'administrative_boundaries',
        // Temporal info fields
        'file_created_date', 'file_modified_date', 'data_temporal_coverage',
        // Technical info fields
        'file_size_bytes', 'compression_info', 'format_version', 'file_integrity',
        // Content info fields (non-spatial files)
        'content_type_detected', 'document_pages', 'spreadsheet_sheets', 'text_content_info'
      ],
      autoFieldGroups: [
        'spatial_info', 'data_info', 'geographic_info', 
        'temporal_info', 'technical_info', 'content_info'
      ],
      collapsedByDefault: true,
      showIndicator: true,
      masterSectionTitle: 'Automatically Generated Metadata',
      masterSectionDescription: 'This section contains metadata automatically extracted from your uploaded resource. Click to expand and review or modify the generated information.',
      masterSectionIcon: 'fa-magic'
    },

    initialize: function () {
      var self = this;
      console.log('[schemingdcat-resource-auto-fields] Initializing module...');
      
      // Use a small delay to ensure DOM is ready
      setTimeout(function() {
        // Find the resource form
        self.form = $('form[action*="/resource/"], form#resource-edit, form#resource-new');
        if (!self.form.length) {
          self.form = self.el.closest('form');
        }
        
        // Only run on resource forms
        if (!self.isResourceForm()) {
          console.log('[schemingdcat-resource-auto-fields] Not a resource form, skipping');
          return;
        }
        
        // Add debug logging
        console.log('[schemingdcat-resource-auto-fields] Form found:', self.form);
        console.log('[schemingdcat-resource-auto-fields] Auto fields configured:', self.options.autoFields);
        console.log('[schemingdcat-resource-auto-fields] Auto field groups configured:', self.options.autoFieldGroups);

        self.setupAutoFieldCollapsing();
        self.monitorAutoFilledFields();
      }, 100);
    },

    isResourceForm: function() {
      // Check if this is a resource form (not dataset form)
      var isResourceCreate = this.form.attr('action') && this.form.attr('action').includes('/resource/new');
      var isResourceEdit = this.form.attr('action') && this.form.attr('action').includes('/resource/edit');
      var hasResourceFields = this.form.find('input[name="url"], input[name="upload"]').length > 0;
      
      return isResourceCreate || isResourceEdit || hasResourceFields;
    },

    setupAutoFieldCollapsing: function() {
      var self = this;
      
      // Find all form groups (card2 elements)
      var formGroups = this.form.find('.card2');
      var autoFieldGroups = [];
      
      console.log('[schemingdcat-resource-auto-fields] Found form groups:', formGroups.length);
      
      // First pass: identify all groups with auto-filled fields
      formGroups.each(function() {
        var $group = $(this);
        var hasAutoFields = self.groupHasAutoFields($group);
        
        if (hasAutoFields) {
          autoFieldGroups.push($group);
        }
      });
      
      // If we have auto-field groups, create a master section
      if (autoFieldGroups.length > 0) {
        // Create master section wrapper
        var $masterSection = self.createMasterSection();
        
        // Find the insertion point - specifically look for the resource_url-group
        var $insertionPoint = self.form.find('.resource_url-group');
        
        if (!$insertionPoint.length) {
          // Look for upload wrapper as alternative
          $insertionPoint = self.form.find('.schemingdcat-upload-wrapper').closest('.card2');
        }
        
        if (!$insertionPoint.length) {
          // Look for any upload field
          $insertionPoint = self.form.find('input[name="upload"], input[name="url"]').closest('.card2');
        }
        
        if ($insertionPoint.length) {
          console.log('[schemingdcat-resource-auto-fields] Inserting master section after:', $insertionPoint.attr('class'));
          // Insert after the upload field group
          $insertionPoint.after($masterSection);
        } else {
          console.log('[schemingdcat-resource-auto-fields] No suitable insertion point found, inserting before first non-auto group');
          // If no suitable insertion point, insert before the first non-auto field group
          var inserted = false;
          formGroups.each(function() {
            var $group = $(this);
            if (!self.groupHasAutoFields($group) && !inserted) {
              $group.before($masterSection);
              inserted = true;
            }
          });
          
          if (!inserted) {
            // As last resort, prepend to form
            var firstGroup = formGroups.first();
            if (firstGroup.length) {
              firstGroup.before($masterSection);
            }
          }
        }
        
        // Move all auto-field groups into the master section
        var $masterContent = $masterSection.find('.schemingdcat-master-content');
        autoFieldGroups.forEach(function($group) {
          $group.appendTo($masterContent);
          
          // Process each group
          var $header = $group.find('.card2-header').first();
          var $body = $group.find('.card2-body').first();
          
          // Remove individual indicators from each group
          $header.find('.schemingdcat-auto-field-indicator').remove();
          
          // Make group collapsible
          self.makeGroupCollapsible($group, $header, $body);
          
          // Collapse individual groups by default
          if (self.options.collapsedByDefault) {
            self.collapseGroup($group, $header, $body);
          }
        });
        
        // Set up master section behavior
        self.setupMasterSectionBehavior($masterSection);
        
        // Collapse master section by default
        if (self.options.collapsedByDefault) {
          self.collapseMasterSection($masterSection);
        }
      }
      
      // Handle individual fields that might not be in groups
      this.handleIndividualAutoFields();
    },

    groupHasAutoFields: function($group) {
      var self = this;
      var hasAuto = false;
      
      // Get group class
      var groupClass = $group.attr('class') || '';
      console.log('[schemingdcat-resource-auto-fields] Checking group class:', groupClass);
      
      // Check if group class contains any of the auto field group IDs
      self.options.autoFieldGroups.forEach(function(groupId) {
        if (groupClass.indexOf(groupId + '-group') !== -1) {
          hasAuto = true;
          console.log('[schemingdcat-resource-auto-fields] Found auto field group:', groupId);
        }
      });
      
      // Also check if group contains any auto-filled fields
      if (!hasAuto) {
        self.options.autoFields.forEach(function(fieldName) {
          if ($group.find('[name="' + fieldName + '"], [name*="__' + fieldName + '"]').length > 0) {
            hasAuto = true;
            console.log('[schemingdcat-resource-auto-fields] Found auto field:', fieldName);
          }
        });
      }
      
      return hasAuto;
    },

    createMasterSection: function() {
      var self = this;
      
      var $masterSection = $('<div>', {
        class: 'schemingdcat-master-section card2 mb-3',
        html: '<div class="card2-header schemingdcat-master-header">' +
              '<button type="button" class="btn btn-xs schemingdcat-master-toggle" title="Toggle all auto-generated fields">' +
              '<i class="fa fa-chevron-down"></i></button>' +
              '<h3 class="mb-0"><i class="fa ' + self.options.masterSectionIcon + '" style="padding-right:5px;"></i>' +
              self.options.masterSectionTitle + '</h3>' +
              '<p class="schemingdcat-master-description">' + self.options.masterSectionDescription + '</p>' +
              '</div>' +
              '<div class="schemingdcat-master-content"></div>'
      });
      
      return $masterSection;
    },
    
    setupMasterSectionBehavior: function($masterSection) {
      var self = this;
      var $header = $masterSection.find('.schemingdcat-master-header');
      var $content = $masterSection.find('.schemingdcat-master-content');
      var $toggleBtn = $masterSection.find('.schemingdcat-master-toggle');
      
      // Make header clickable
      $header.css('cursor', 'pointer');
      
      // Handle clicks on the master section header
      $header.on('click.master', function(e) {
        // Don't toggle if clicking on form elements
        if ($(e.target).is('input, select, textarea, label, a')) {
          return;
        }
        e.preventDefault();
        self.toggleMasterSection($masterSection);
      });
    },
    
    toggleMasterSection: function($masterSection) {
      if ($masterSection.hasClass('collapsed')) {
        this.expandMasterSection($masterSection);
      } else {
        this.collapseMasterSection($masterSection);
      }
    },
    
    collapseMasterSection: function($masterSection) {
      var $content = $masterSection.find('.schemingdcat-master-content');
      var $toggleIcon = $masterSection.find('.schemingdcat-master-toggle i');
      
      $masterSection.addClass('collapsed');
      $content.slideUp(200);
      $toggleIcon.removeClass('fa-chevron-down').addClass('fa-chevron-right');
    },
    
    expandMasterSection: function($masterSection) {
      var $content = $masterSection.find('.schemingdcat-master-content');
      var $toggleIcon = $masterSection.find('.schemingdcat-master-toggle i');
      
      $masterSection.removeClass('collapsed');
      $content.slideDown(200);
      $toggleIcon.removeClass('fa-chevron-right').addClass('fa-chevron-down');
    },

    makeGroupCollapsible: function($group, $header, $body) {
      var self = this;
      
      // Check if already processed to avoid duplicates
      if ($group.hasClass('schemingdcat-collapsible')) {
        return;
      }
      
      // Add collapsible class
      $group.addClass('schemingdcat-collapsible');
      
      // Create toggle button
      var $toggleBtn = $('<button>', {
        type: 'button',
        class: 'btn btn-xs schemingdcat-collapse-toggle',
        title: 'Toggle fields',
        html: '<i class="fa fa-chevron-down"></i>'
      });
      
      // Add toggle button to header only if not already present
      if ($header.find('.schemingdcat-collapse-toggle').length === 0) {
        $header.css('cursor', 'pointer').prepend($toggleBtn);
      }
      
      // Handle click events
      $header.off('click.autofields').on('click.autofields', function(e) {
        // Don't toggle if clicking on form elements
        if ($(e.target).is('input, select, textarea, label, a')) {
          return;
        }
        e.preventDefault();
        self.toggleGroup($group, $header, $body);
      });
    },

    handleIndividualAutoFields: function() {
      var self = this;
      
      // Find auto fields that are not in card2 groups
      self.options.autoFields.forEach(function(fieldName) {
        var $fields = self.form.find('[name="' + fieldName + '"], [name*="__' + fieldName + '"]');
        
        $fields.each(function() {
          var $field = $(this);
          var $container = $field.closest('.control-group, .form-group');
          
          // Skip if already in a collapsible group
          if ($container.closest('.schemingdcat-collapsible').length > 0) {
            return;
          }
          
          // Create a wrapper for the field
          var $wrapper = $('<div>', {
            class: 'schemingdcat-auto-field-wrapper'
          });
          
          $container.wrap($wrapper);
          $wrapper = $container.parent();
          
          // Add indicator
          var $indicator = $('<div>', {
            class: 'schemingdcat-auto-field-single-indicator',
            html: '<i class="fa fa-magic"></i> Auto-filled field'
          });
          
          $wrapper.prepend($indicator);
          
          // Make it collapsible
          if (self.options.collapsedByDefault) {
            $container.hide();
            $wrapper.addClass('collapsed');
          }
          
          $indicator.on('click', function() {
            $container.toggle();
            $wrapper.toggleClass('collapsed');
          });
        });
      });
    },

    toggleGroup: function($group, $header, $body) {
      if ($group.hasClass('collapsed')) {
        this.expandGroup($group, $header, $body);
      } else {
        this.collapseGroup($group, $header, $body);
      }
    },

    collapseGroup: function($group, $header, $body) {
      console.log('[schemingdcat-resource-auto-fields] Collapsing group');
      $group.addClass('collapsed');
      $body.slideUp(200, function() {
        // Ensure it's hidden after animation
        $body.css('display', 'none');
      });
      $header.find('.schemingdcat-collapse-toggle i')
        .removeClass('fa-chevron-down')
        .addClass('fa-chevron-right');
    },

    expandGroup: function($group, $header, $body) {
      console.log('[schemingdcat-resource-auto-fields] Expanding group');
      $group.removeClass('collapsed');
      $body.css('display', 'block').hide().slideDown(200);
      $header.find('.schemingdcat-collapse-toggle i')
        .removeClass('fa-chevron-right')
        .addClass('fa-chevron-down');
    },

    monitorAutoFilledFields: function() {
      var self = this;
      
      // Monitor for changes to auto-filled fields
      self.options.autoFields.forEach(function(fieldName) {
        var $fields = self.form.find('[name="' + fieldName + '"], [name*="__' + fieldName + '"]');
        
        $fields.each(function() {
          var $field = $(this);
          
          // Add visual indicator when field is auto-filled
          $field.on('change', function() {
            if ($field.attr('data-auto-filled') === 'true') {
              $field.addClass('schemingdcat-auto-filled');
              
              // Expand the group if it's collapsed and a field was auto-filled
              var $group = $field.closest('.schemingdcat-collapsible');
              if ($group.length > 0 && $group.hasClass('collapsed')) {
                var $header = $group.find('.card2-header').first();
                var $body = $group.find('.card2-body').first();
                self.expandGroup($group, $header, $body);
                
                // Add a temporary highlight
                $group.addClass('schemingdcat-auto-filled-highlight');
                setTimeout(function() {
                  $group.removeClass('schemingdcat-auto-filled-highlight');
                }, 3000);
              }
            }
          });
        });
      });
    }
  };
});