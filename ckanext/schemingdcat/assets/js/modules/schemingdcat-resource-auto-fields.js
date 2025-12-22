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
      masterSectionDescription: 'This section will be populated with metadata automatically extracted after you upload your file. Once generated, you can expand this section to review and modify the information as needed.',
      masterSectionIcon: 'fa-magic'
    },

    initialize: function () {
      var self = this;
      console.log('[schemingdcat-resource-auto-fields] Initializing module...');
      
      // Check if already initialized to prevent duplicates
      if (this.el.data('auto-fields-initialized')) {
        console.log('[schemingdcat-resource-auto-fields] Already initialized, skipping');
        return;
      }
      this.el.data('auto-fields-initialized', true);
      
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
        
        // Check for DOI resource files from previous step
        self.checkDoiResourceFiles();
        
        // Check if master section already exists
        if (self.form.find('.schemingdcat-master-section').length > 0) {
          console.log('[schemingdcat-resource-auto-fields] Master section already exists, skipping');
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

    /**
     * Check for DOI resource files stored in sessionStorage
     * and pre-fill the URL field if available
     */
    checkDoiResourceFiles: function() {
      try {
        // Prevent duplicate notifications
        if ($('.doi-files-notification').length > 0) {
          console.log('[schemingdcat-resource-auto-fields] DOI notification already exists, skipping');
          return;
        }
        
        var storedData = sessionStorage.getItem('doi_resource_files');
        if (!storedData) {
          return;
        }
        
        var doiData = JSON.parse(storedData);
        console.log('[schemingdcat-resource-auto-fields] Found DOI resource files:', doiData);
        
        // Check if data is recent (within last 30 minutes)
        var timestamp = new Date(doiData.timestamp);
        var now = new Date();
        var ageMinutes = (now - timestamp) / (1000 * 60);
        
        if (ageMinutes > 30) {
          console.log('[schemingdcat-resource-auto-fields] DOI data is too old, clearing');
          sessionStorage.removeItem('doi_resource_files');
          return;
        }
        
        // Show notification about available DOI files
        if (doiData.files && doiData.files.length > 0) {
          this.showDoiFilesNotification(doiData);
        }
        
      } catch (e) {
        console.warn('[schemingdcat-resource-auto-fields] Error checking DOI files:', e);
      }
    },

    /**
     * Show notification about available DOI files with improved UI
     * @param {Object} doiData - DOI resource data
     */
    showDoiFilesNotification: function(doiData) {
      var self = this;
      // Normalize files (infer names / formats from URL when missing)
      var files = (doiData.files || []).map(function(file) {
        var normalized = $.extend({}, file);
        if (!normalized.format && normalized.url) {
          normalized.format = self.getFormatFromUrl(normalized.url);
        }
        if (!normalized.filename && normalized.url) {
          normalized.filename = self.getFilenameFromUrl(normalized.url);
        }
        return normalized;
      });
      var packageId = this.getPackageId();
      var uniqueId = 'doi-' + Date.now();
      var enableMultiMode = files.length > 1;
      
      // Add styles first
      this.addDoiNotificationStyles();
      
      // Build the complete HTML structure
      var html = '<div class="doi-files-notification" id="' + uniqueId + '">' +
        '<div class="doi-notification-header">' +
          '<div class="doi-notification-title">' +
            '<i class="fa fa-link"></i> Links found from DOI (' + files.length + ' available)' +
          '</div>' +
          '<button type="button" class="btn btn-sm btn-link doi-files-dismiss">' +
            '<i class="fa fa-times"></i>' +
          '</button>' +
        '</div>' +
        '<div class="doi-notification-body">' +
          '<div class="doi-mode-selector">' +
            '<button type="button" class="btn btn-default doi-mode-btn active" data-mode="single">' +
              '<i class="fa fa-file-o"></i> Add single resource' +
            '</button>' +
            (enableMultiMode ? (
              '<button type="button" class="btn btn-default doi-mode-btn" data-mode="multiple">' +
                '<i class="fa fa-files-o"></i> Add multiple resources' +
              '</button>'
            ) : '') +
          '</div>' +
          '<div class="doi-mode-content">' +
            '<div class="doi-mode-panel doi-single-panel active">' +
              '<p class="doi-help-text">' +
                '<i class="fa fa-info-circle"></i> Click on a link to fill the form below with that resource. You can still upload a local file using the standard upload field below.' +
              '</p>' +
              '<div class="doi-files-list" id="' + uniqueId + '-single-list"></div>' +
            '</div>' +
            (enableMultiMode ? (
              '<div class="doi-mode-panel doi-multi-panel">' +
                '<p class="doi-help-text">' +
                  '<i class="fa fa-info-circle"></i> Select links to create multiple resources at once (remote links from the DOI).' +
                '</p>' +
                '<div class="doi-select-all-wrapper">' +
                  '<label><input type="checkbox" class="doi-select-all"> Select all</label>' +
                '</div>' +
                '<div class="doi-files-list" id="' + uniqueId + '-multi-list"></div>' +
                '<div class="doi-multi-actions">' +
                  '<button type="button" class="btn btn-primary doi-add-selected" disabled>' +
                    '<i class="fa fa-plus-circle"></i> Add selected (<span class="selected-count">0</span>)' +
                  '</button>' +
                '</div>' +
                '<div class="doi-multi-progress" style="display: none;">' +
                  '<div class="progress">' +
                    '<div class="progress-bar progress-bar-striped active" style="width: 0%"></div>' +
                  '</div>' +
                  '<p class="doi-progress-status"></p>' +
                '</div>' +
              '</div>'
            ) : '') +
          '</div>' +
        '</div>' +
      '</div>';
      
      var $notification = $(html);
      
      // Populate single file list
      var $singleList = $notification.find('#' + uniqueId + '-single-list');
      files.forEach(function(file, index) {
        if (!file.url) return;
        
        var displayName = self.getDisplayName(file, index);
        var formatBadge = file.format ? '<span class="badge">' + self.escapeHtml(file.format) + '</span>' : '';
        
        var $item = $('<div class="doi-file-item">' +
          '<button type="button" class="btn btn-sm btn-success doi-file-use">' +
            '<i class="fa fa-plus"></i> Use' +
          '</button>' +
          '<div class="doi-file-info">' +
            '<div class="doi-file-name">' + self.escapeHtml(displayName) + ' ' + formatBadge + '</div>' +
            '<div class="doi-file-url">' + self.escapeHtml(file.url) + '</div>' +
          '</div>' +
        '</div>');
        
        $item.data('file', file);
        $singleList.append($item);
      });
      
      // Populate multiple file list
      if (enableMultiMode) {
        var $multiList = $notification.find('#' + uniqueId + '-multi-list');
        files.forEach(function(file, index) {
          if (!file.url) return;
          
          var displayName = self.getDisplayName(file, index);
          var formatBadge = file.format ? '<span class="badge">' + self.escapeHtml(file.format) + '</span>' : '';
          var checkId = uniqueId + '-check-' + index;
          
          var $item = $('<div class="doi-file-item doi-file-checkbox">' +
            '<input type="checkbox" class="doi-file-check" id="' + checkId + '">' +
            '<label for="' + checkId + '" class="doi-file-info">' +
              '<div class="doi-file-name">' + self.escapeHtml(displayName) + ' ' + formatBadge + '</div>' +
              '<div class="doi-file-url">' + self.escapeHtml(file.url) + '</div>' +
            '</label>' +
          '</div>');
          
          $item.data('file', file);
          $multiList.append($item);
        });
      }
      
      // Find insertion point - look for Resource locator section or form start
      var $insertPoint = this.form.find('.card2').first();
      if ($insertPoint.length) {
        $insertPoint.before($notification);
      } else {
        this.form.prepend($notification);
      }
      
      // Bind mode switching
      $notification.on('click', '.doi-mode-btn', function(e) {
        e.preventDefault();
        var mode = $(this).data('mode');
        $notification.find('.doi-mode-btn').removeClass('active');
        $(this).addClass('active');
        $notification.find('.doi-mode-panel').removeClass('active');
        $notification.find('.doi-' + mode + '-panel').addClass('active');
      });
      
      // Handle single file use
      $notification.on('click', '.doi-file-use', function(e) {
        e.preventDefault();
        var $item = $(this).closest('.doi-file-item');
        var file = $item.data('file');
        
        if (file) {
          self.applyDoiFileToForm(file.url, file.filename || '', file.format || '');
          $item.addClass('used');
          $(this).prop('disabled', true).html('<i class="fa fa-check"></i> Applied');
        }
      });
      
      // Handle checkbox changes
      $notification.on('change', '.doi-file-check', function() {
        self.updateMultiSelectCount($notification);
      });
      
      // Handle select all
      $notification.on('change', '.doi-select-all', function() {
        var isChecked = $(this).is(':checked');
        $notification.find('.doi-file-check').prop('checked', isChecked);
        self.updateMultiSelectCount($notification);
      });
      
      // Handle add selected
      $notification.on('click', '.doi-add-selected', function(e) {
        e.preventDefault();
        self.addSelectedDoiResources($notification, packageId, doiData);
      });
      
      // Handle dismiss
      $notification.on('click', '.doi-files-dismiss', function(e) {
        e.preventDefault();
        $notification.slideUp(200, function() {
          $(this).remove();
        });
        sessionStorage.removeItem('doi_resource_files');
      });
      
      console.log('[schemingdcat-resource-auto-fields] DOI notification created with', files.length, 'files');
    },
    
    /**
     * Get display name for a DOI file
     */
    getDisplayName: function(file, index) {
      if (file.filename) {
        return file.filename.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');
      }
      if (file.description && file.description !== 'Publisher page' && file.description !== 'Document landing page') {
        return file.description;
      }
      if (file.url) {
        return this.getFilenameFromUrl(file.url).replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');
      }
      return 'Resource ' + (index + 1);
    },
    
    /**
     * Infer filename from URL (without querystring)
     */
    getFilenameFromUrl: function(url) {
      if (!url) return '';
      try {
        var cleanUrl = url.split('?')[0].split('#')[0];
        var parts = cleanUrl.split('/');
        return parts[parts.length - 1] || 'resource';
      } catch (e) {
        return 'resource';
      }
    },
    
    /**
     * Infer format/extension from URL
     */
    getFormatFromUrl: function(url) {
      if (!url) return '';
      try {
        var filename = this.getFilenameFromUrl(url);
        if (filename.indexOf('.') === -1) return '';
        return filename.split('.').pop().toUpperCase();
      } catch (e) {
        return '';
      }
    },
    
    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml: function(text) {
      if (!text) return '';
      var div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    },
    
    /**
     * Get package ID from URL or form
     */
    getPackageId: function() {
      // Try from URL
      var path = window.location.pathname;
      var match = path.match(/\/dataset\/([^\/]+)/);
      if (match) return match[1];
      
      // Try from form action
      if (this.form.length) {
        var action = this.form.attr('action') || '';
        match = action.match(/\/dataset\/([^\/]+)/);
        if (match) return match[1];
      }
      
      return null;
    },
    
    /**
     * Update count of selected files for multi-select
     */
    updateMultiSelectCount: function($notification) {
      var count = $notification.find('.doi-file-check:checked').length;
      $notification.find('.selected-count').text(count);
      $notification.find('.doi-add-selected').prop('disabled', count === 0);
    },
    
    /**
     * Add selected DOI files as separate resources
     */
    addSelectedDoiResources: function($notification, packageId, doiData) {
      var self = this;
      var $selectedItems = $notification.find('.doi-file-check:checked').closest('.doi-file-item');
      
      if ($selectedItems.length === 0) {
        console.log('[schemingdcat-resource-auto-fields] No files selected');
        return;
      }
      
      if (!packageId) {
        console.error('[schemingdcat-resource-auto-fields] No package ID found');
        alert('Error: Could not determine the dataset. Please try again.');
        return;
      }
      
      // Collect selected files data from jQuery data
      var selectedFiles = [];
      $selectedItems.each(function() {
        var file = $(this).data('file');
        if (file && file.url) {
          selectedFiles.push(file);
        }
      });
      
      console.log('[schemingdcat-resource-auto-fields] Adding', selectedFiles.length, 'resources');
      
      // Show progress
      var $progress = $notification.find('.doi-multi-progress');
      var $progressBar = $progress.find('.progress-bar');
      var $progressStatus = $progress.find('.doi-progress-status');
      var $addBtn = $notification.find('.doi-add-selected');
      
      $addBtn.prop('disabled', true).html('<i class="fa fa-spinner fa-spin"></i> Creating resources...');
      $progress.show();
      
      // Create resources sequentially
      var completed = 0;
      var errors = [];
      
      function createNextResource(index) {
        if (index >= selectedFiles.length) {
          // All done
          self.onMultiResourcesComplete($notification, completed, errors, packageId);
          return;
        }
        
        var file = selectedFiles[index];
        var displayName = self.getDisplayName(file, index);
        var percent = Math.round((index / selectedFiles.length) * 100);
        $progressBar.css('width', percent + '%');
        $progressStatus.text('Creating resource ' + (index + 1) + ' of ' + selectedFiles.length + ': ' + displayName);
        
        self.createResourceFromDoiFile(packageId, file, doiData, function(success, result) {
          if (success) {
            completed++;
            // Mark as created
            $selectedItems.eq(index).addClass('used created')
              .find('.doi-file-check').prop('disabled', true);
          } else {
            errors.push({ file: file, error: result });
          }
          
          // Continue with next
          setTimeout(function() {
            createNextResource(index + 1);
          }, 300);
        });
      }
      
      createNextResource(0);
    },
    
    /**
     * Create a single resource from DOI file data
     */
    createResourceFromDoiFile: function(packageId, file, doiData, callback) {
      var self = this;
      
      // Generate resource name from filename or description
      var resourceName = this.getDisplayName(file, 0);
      var inferredFormat = file.format || this.getFormatFromUrl(file.url);
      
      // Ensure name is not empty
      if (!resourceName || resourceName.trim() === '') {
        resourceName = this.getFilenameFromUrl(file.url).replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');
      }
      if (!resourceName || resourceName.trim() === '') {
        resourceName = 'DOI Resource ' + new Date().toISOString().slice(0, 10);
      }
      
      var resourceData = {
        package_id: packageId,
        url: file.url,
        name: resourceName,
        format: inferredFormat ? inferredFormat.toUpperCase() : '',
        description: 'Added from DOI: ' + (doiData.doi || '')
      };
      
      console.log('[schemingdcat-resource-auto-fields] Creating resource:', resourceData);
      
      $.ajax({
        url: '/api/3/action/resource_create',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(resourceData),
        success: function(response) {
          if (response.success) {
            console.log('[schemingdcat-resource-auto-fields] Resource created:', response.result.id);
            callback(true, response.result);
          } else {
            console.error('[schemingdcat-resource-auto-fields] Resource creation failed:', response.error);
            callback(false, response.error);
          }
        },
        error: function(xhr, status, error) {
          console.error('[schemingdcat-resource-auto-fields] Resource creation error:', error);
          var errorMsg = error;
          try {
            var response = JSON.parse(xhr.responseText);
            errorMsg = response.error && response.error.message ? response.error.message : error;
          } catch(e) {}
          callback(false, errorMsg);
        }
      });
    },
    
    /**
     * Handle completion of multi-resource creation
     */
    onMultiResourcesComplete: function($notification, completed, errors, packageId) {
      var $progress = $notification.find('.doi-multi-progress');
      var $progressBar = $progress.find('.progress-bar');
      var $progressStatus = $progress.find('.doi-progress-status');
      var $addBtn = $notification.find('.doi-add-selected');
      
      $progressBar.css('width', '100%').removeClass('active');
      
      if (errors.length === 0) {
        $progressBar.addClass('progress-bar-success');
        $progressStatus.html('<i class="fa fa-check-circle text-success"></i> ' + 
          completed + ' resource(s) created successfully!');
        $addBtn.html('<i class="fa fa-check"></i> Completed');
        
        // Clear stored DOI data
        sessionStorage.removeItem('doi_resource_files');
        
        // Redirect to dataset page after delay
        setTimeout(function() {
          window.location.href = '/dataset/' + packageId;
        }, 2000);
      } else {
        $progressBar.addClass('progress-bar-warning');
        $progressStatus.html('<i class="fa fa-exclamation-triangle text-warning"></i> ' + 
          completed + ' created, ' + errors.length + ' failed');
        $addBtn.prop('disabled', false).html('<i class="fa fa-refresh"></i> Retry failed');
      }
    },
    
    /**
     * Add CSS styles for DOI notification
     */
    addDoiNotificationStyles: function() {
      if ($('#doi-notification-styles').length > 0) return;
      
      var styles = 
        '<style id="doi-notification-styles">' +
        '.doi-files-notification {' +
          'margin: 15px 0;' +
          'border: 2px solid #5bc0de;' +
          'border-radius: 8px;' +
          'background: #fff;' +
          'box-shadow: 0 2px 8px rgba(0,0,0,0.1);' +
        '}' +
        '.doi-notification-header {' +
          'display: flex;' +
          'justify-content: space-between;' +
          'align-items: center;' +
          'padding: 12px 15px;' +
          'background: linear-gradient(135deg, #5bc0de 0%, #46b8da 100%);' +
          'border-radius: 6px 6px 0 0;' +
          'color: #fff;' +
        '}' +
        '.doi-notification-title {' +
          'font-weight: 600;' +
          'font-size: 14px;' +
        '}' +
        '.doi-notification-title i {' +
          'margin-right: 8px;' +
        '}' +
        '.doi-notification-header .btn-link {' +
          'color: #fff;' +
          'opacity: 0.8;' +
          'padding: 0;' +
          'font-size: 18px;' +
        '}' +
        '.doi-notification-header .btn-link:hover {' +
          'opacity: 1;' +
        '}' +
        '.doi-notification-body {' +
          'padding: 15px;' +
        '}' +
        '.doi-mode-selector {' +
          'display: flex;' +
          'gap: 10px;' +
          'margin-bottom: 15px;' +
        '}' +
        '.doi-mode-btn {' +
          'flex: 1;' +
          'padding: 10px;' +
          'border-radius: 6px;' +
        '}' +
        '.doi-mode-btn.active {' +
          'background: #337ab7;' +
          'color: #fff;' +
          'border-color: #2e6da4;' +
        '}' +
        '.doi-mode-btn i {' +
          'margin-right: 5px;' +
        '}' +
        '.doi-mode-panel {' +
          'display: none;' +
        '}' +
        '.doi-mode-panel.active {' +
          'display: block;' +
        '}' +
        '.doi-help-text {' +
          'color: #666;' +
          'font-size: 13px;' +
          'margin-bottom: 12px;' +
          'padding: 8px 12px;' +
          'background: #f8f9fa;' +
          'border-radius: 4px;' +
        '}' +
        '.doi-help-text i {' +
          'color: #5bc0de;' +
          'margin-right: 5px;' +
        '}' +
        '.doi-select-all-wrapper {' +
          'margin-bottom: 10px;' +
        '}' +
        '.doi-select-all-wrapper label {' +
          'font-weight: normal;' +
          'cursor: pointer;' +
        '}' +
        '.doi-files-list {' +
          'max-height: 200px;' +
          'overflow-y: auto;' +
          'border: 1px solid #e0e0e0;' +
          'border-radius: 6px;' +
          'background: #fafafa;' +
        '}' +
        '.doi-file-item {' +
          'display: flex;' +
          'align-items: flex-start;' +
          'padding: 12px;' +
          'border-bottom: 1px solid #eee;' +
          'background: #fff;' +
          'transition: background 0.2s;' +
        '}' +
        '.doi-file-item:last-child {' +
          'border-bottom: none;' +
        '}' +
        '.doi-file-item:hover {' +
          'background: #f5f9fc;' +
        '}' +
        '.doi-file-item.used {' +
          'background: #d4edda;' +
        '}' +
        '.doi-file-item.created {' +
          'background: #cce5ff;' +
        '}' +
        '.doi-file-item .btn {' +
          'margin-right: 12px;' +
          'flex-shrink: 0;' +
        '}' +
        '.doi-file-item.doi-file-checkbox {' +
          'gap: 10px;' +
        '}' +
        '.doi-file-item.doi-file-checkbox input[type="checkbox"] {' +
          'margin-top: 4px;' +
          'flex-shrink: 0;' +
        '}' +
        '.doi-file-info {' +
          'flex: 1;' +
          'min-width: 0;' +
        '}' +
        '.doi-file-info label {' +
          'display: block;' +
          'cursor: pointer;' +
          'margin: 0;' +
          'font-weight: normal;' +
        '}' +
        '.doi-file-name {' +
          'font-weight: 600;' +
          'color: #333;' +
          'margin-bottom: 4px;' +
        '}' +
        '.doi-file-name .badge {' +
          'margin-left: 8px;' +
          'font-weight: normal;' +
          'background: #337ab7;' +
        '}' +
        '.doi-file-url {' +
          'font-size: 12px;' +
          'color: #888;' +
          'word-break: break-all;' +
        '}' +
        '.doi-multi-actions {' +
          'margin-top: 15px;' +
          'padding-top: 15px;' +
          'border-top: 1px solid #eee;' +
        '}' +
        '.doi-multi-progress {' +
          'margin-top: 15px;' +
        '}' +
        '.doi-multi-progress .progress {' +
          'margin-bottom: 10px;' +
          'height: 20px;' +
          'border-radius: 10px;' +
        '}' +
        '.doi-progress-status {' +
          'font-size: 13px;' +
          'color: #666;' +
        '}' +
        '</style>';
      
      $('head').append(styles);
    },

    /**
     * Apply DOI file URL to the resource form
     * @param {string} url - File URL
     * @param {string} filename - Original filename
     * @param {string} format - File format
     */
    applyDoiFileToForm: function(url, filename, format) {
      // Infer missing bits from URL to avoid "undefined" resources
      if (!filename) {
        filename = this.getFilenameFromUrl(url);
      }
      if (!format) {
        format = this.getFormatFromUrl(url);
      }
      // Find and fill URL field
      var $urlField = this.form.find('input[name="url"]');
      if ($urlField.length && (!$urlField.val() || $urlField.val().trim() === '')) {
        $urlField.val(url).trigger('change');
        console.log('[schemingdcat-resource-auto-fields] Set URL field:', url);
      }
      
      // Try to set name/title field
      if (filename) {
        var $nameField = this.form.find('input[name="name"]');
        if ($nameField.length && (!$nameField.val() || $nameField.val().trim() === '')) {
          // Clean filename for display
          var displayName = filename.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');
          $nameField.val(displayName).trigger('change');
        }
      }
      
      // Try to set format field
      if (format) {
        var $formatField = this.form.find('select[name="format"], input[name="format"]');
        if ($formatField.length) {
          if ($formatField.is('select')) {
            // Try to find matching option
            var $option = $formatField.find('option[value="' + format + '"], option[value="' + format.toUpperCase() + '"], option[value="' + format.toLowerCase() + '"]');
            if ($option.length) {
              $formatField.val($option.val()).trigger('change');
            }
          } else {
            $formatField.val(format.toUpperCase()).trigger('change');
          }
        }
      }
      
      // Show success message
      this.showDoiAppliedMessage();
    },

    /**
     * Show success message when DOI file is applied
     */
    showDoiAppliedMessage: function() {
      var $msg = $('<div>', {
        class: 'alert alert-success doi-applied-message',
        html: '<i class="fa fa-check-circle"></i> Link from DOI applied to resource'
      });
      
      this.form.find('.doi-files-notification').after($msg);
      
      setTimeout(function() {
        $msg.fadeOut(300, function() { $(this).remove(); });
      }, 3000);
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
        
        // Find the insertion point - look for form actions (submit buttons)
        var $formActions = self.form.find('.form-actions');
        
        if ($formActions.length) {
          console.log('[schemingdcat-resource-auto-fields] Inserting master section before form actions');
          // Insert before the form action buttons
          $formActions.before($masterSection);
        } else {
          console.log('[schemingdcat-resource-auto-fields] No form actions found, looking for last card2 group');
          // If no form actions, insert after the last non-auto field group
          var $lastNonAutoGroup = null;
          formGroups.each(function() {
            var $group = $(this);
            if (!self.groupHasAutoFields($group)) {
              $lastNonAutoGroup = $group;
            }
          });
          
          if ($lastNonAutoGroup) {
            console.log('[schemingdcat-resource-auto-fields] Inserting after last non-auto group');
            $lastNonAutoGroup.after($masterSection);
          } else {
            // As last resort, append to form
            console.log('[schemingdcat-resource-auto-fields] Appending to form');
            self.form.append($masterSection);
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
              '<p class="schemingdcat-master-description">' +
              '<i class="fa fa-info-circle" style="margin-right:5px;"></i>' +
              self.options.masterSectionDescription + '</p>' +
              '<div class="schemingdcat-master-note">' +
              '<i class="fa fa-clock-o"></i> Metadata extraction occurs automatically after file upload' +
              '</div>' +
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
