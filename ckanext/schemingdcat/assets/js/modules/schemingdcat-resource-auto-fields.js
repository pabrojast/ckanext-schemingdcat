this.ckan.module('schemingdcat-resource-auto-fields', function ($) {
  'use strict';

  return {
    options: {
      autoFields: ['name', 'format', 'mimetype', 'encoding', 'created'],
      autoFieldGroups: ['resource_title', 'resource_type', 'resource_identification'],
      collapsedByDefault: true,
      showIndicator: true,
      indicatorText: 'Auto-filled fields'
    },

    initialize: function () {
      console.log('[schemingdcat-resource-auto-fields] Initializing module...');
      this.form = this.el.closest('form');
      
      // Only run on resource forms
      if (!this.isResourceForm()) {
        console.log('[schemingdcat-resource-auto-fields] Not a resource form, skipping');
        return;
      }

      this.setupAutoFieldCollapsing();
      this.monitorAutoFilledFields();
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
      
      formGroups.each(function() {
        var $group = $(this);
        var $header = $group.find('.card2-header').first();
        var $body = $group.find('.card2-body').first();
        
        // Check if this group contains auto-filled fields
        var hasAutoFields = self.groupHasAutoFields($group);
        
        if (hasAutoFields) {
          // Add collapsible functionality
          self.makeGroupCollapsible($group, $header, $body);
          
          // Collapse by default if option is set
          if (self.options.collapsedByDefault) {
            self.collapseGroup($group, $header, $body);
          }
        }
      });
      
      // Also handle individual fields that might not be in groups
      this.handleIndividualAutoFields();
    },

    groupHasAutoFields: function($group) {
      var self = this;
      var hasAuto = false;
      
      // Check if group contains any auto-filled fields
      self.options.autoFields.forEach(function(fieldName) {
        if ($group.find('[name="' + fieldName + '"], [name*="__' + fieldName + '"]').length > 0) {
          hasAuto = true;
        }
      });
      
      // Check if group ID matches auto field groups
      // Extract group ID from class name (e.g., "resource_type-group card2 mb-3")
      var groupClass = $group.attr('class') || '';
      var groupMatch = groupClass.match(/(\w+)-group/);
      var groupId = groupMatch ? groupMatch[1] : '';
      
      if (groupId && self.options.autoFieldGroups.includes(groupId)) {
        hasAuto = true;
      }
      
      return hasAuto;
    },

    makeGroupCollapsible: function($group, $header, $body) {
      var self = this;
      
      // Add collapsible class
      $group.addClass('schemingdcat-collapsible');
      
      // Create toggle button
      var $toggleBtn = $('<button>', {
        type: 'button',
        class: 'btn btn-xs schemingdcat-collapse-toggle',
        title: 'Toggle auto-filled fields',
        html: '<i class="fa fa-chevron-down"></i>'
      });
      
      // Add auto-field indicator
      if (self.options.showIndicator) {
        var $indicator = $('<span>', {
          class: 'schemingdcat-auto-field-indicator',
          html: '<i class="fa fa-magic"></i> ' + self.options.indicatorText
        });
        $header.append($indicator);
      }
      
      // Add toggle button to header
      $header.css('cursor', 'pointer').prepend($toggleBtn);
      
      // Handle click events
      $header.on('click', function(e) {
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
      $group.addClass('collapsed');
      $body.slideUp(200);
      $header.find('.schemingdcat-collapse-toggle i')
        .removeClass('fa-chevron-down')
        .addClass('fa-chevron-right');
    },

    expandGroup: function($group, $header, $body) {
      $group.removeClass('collapsed');
      $body.slideDown(200);
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