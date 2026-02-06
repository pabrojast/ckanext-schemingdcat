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
      masterSectionIcon: 'fa-magic',
      packageId: null
    },

    initialize: function () {
      var self = this;
      console.log('[schemingdcat-resource-auto-fields] Initializing module...');
      this.cachedPackageId = this.options.packageId || null;
      
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
      if (!files.length) {
        console.log('[schemingdcat-resource-auto-fields] DOI data contained no usable files');
        sessionStorage.removeItem('doi_resource_files');
        return;
      }
      var packageId = this.getPackageId();
      var uniqueId = 'doi-' + Date.now();
      var hasMultiple = files.length > 1;
      var preselectLinks = files.length > 0;
      var initialCount = preselectLinks ? files.length : 0;
      var selectLabel = hasMultiple ? 'Select all links' : 'Add this link as a remote resource';
      
      // Add styles first
      this.addDoiNotificationStyles();
      
      var description = hasMultiple
        ? 'We found several links in the DOI. Choose which ones to add as remote resources. You can also use any link to fill the form and upload your own file below.'
        : 'We found a link in the DOI. You can add it as a remote resource or use it to fill the form while uploading your own file.';

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
          '<p class="doi-help-text">' +
            '<i class="fa fa-info-circle"></i> ' + description +
          '</p>' +
          '<div class="doi-actions-row">' +
            '<label class="doi-select-all-wrapper">' +
              '<input type="checkbox" class="doi-select-all"' + (preselectLinks ? ' checked' : '') + '> ' + selectLabel +
            '</label>' +
            '<button type="button" class="btn btn-primary doi-add-selected"' + (preselectLinks ? '' : ' disabled') + '>' +
              '<i class="fa fa-plus-circle"></i> Add selected (<span class="selected-count">' + initialCount + '</span>)' +
            '</button>' +
          '</div>' +
          '<div class="doi-files-list" id="' + uniqueId + '-list"></div>' +
          '<div class="doi-multi-progress" style="display: none;">' +
            '<div class="progress">' +
              '<div class="progress-bar progress-bar-striped active" style="width: 0%"></div>' +
            '</div>' +
            '<p class="doi-progress-status"></p>' +
          '</div>' +
          '<div class="doi-multi-errors alert alert-danger" style="display: none;"></div>' +
          '<div class="doi-multi-success alert alert-success" style="display: none;"></div>' +
        '</div>' +
      '</div>';
      
      var $notification = $(html);
      this.addUploadGuidance();
      
      // Populate file list
      var $list = $notification.find('#' + uniqueId + '-list');
      files.forEach(function(file, index) {
        if (!file.url) return;
        
        var displayName = self.getDisplayName(file, index);
        var formatBadge = file.format ? '<span class="badge">' + self.escapeHtml(file.format) + '</span>' : '';
        var checkId = uniqueId + '-check-' + index;
        var checkedAttr = preselectLinks ? ' checked' : '';
        
        var $item = $('<div class="doi-file-item">' +
          '<div class="doi-file-main">' +
            '<label for="' + checkId + '" class="doi-file-check-label">' +
              '<input type="checkbox" class="doi-file-check" id="' + checkId + '"' + checkedAttr + '>' +
              '<span class="doi-file-name">' + self.escapeHtml(displayName) + ' ' + formatBadge + '</span>' +
            '</label>' +
            '<div class="doi-file-url">' + self.escapeHtml(file.url) + '</div>' +
          '</div>' +
          '<div class="doi-inline-actions">' +
            '<button type="button" class="btn btn-link doi-file-use">' +
              '<i class="fa fa-magic"></i> Use in this form' +
            '</button>' +
            '<span class="doi-inline-hint">Fills URL, name and format; you can still upload a local file.</span>' +
          '</div>' +
        '</div>');
        
        $item.data('file', file);
        $list.append($item);
      });
      
      // Find insertion point - look for Resource locator section or form start
      var $insertPoint = this.form.find('.card2').first();
      if ($insertPoint.length) {
        $insertPoint.before($notification);
      } else {
        this.form.prepend($notification);
      }
      
      // Initial count
      this.updateMultiSelectCount($notification);

      // Handle single file use
      $notification.on('click', '.doi-file-use', function(e) {
        e.preventDefault();
        var $item = $(this).closest('.doi-file-item');
        var file = $item.data('file');
        
        if (file) {
          self.applyDoiFileToForm(file.url, file.filename || '', file.format || '');
          $item.addClass('used');
          $(this).html('<i class="fa fa-check"></i> Applied to form');
        }
      });
      
      // Handle checkbox changes
      $notification.on('change', '.doi-file-check', function() {
        self.updateMultiSelectCount($notification);
      });
      
      // Handle select all
      $notification.on('change', '.doi-select-all', function() {
        var isChecked = $(this).is(':checked');
        $notification.find('.doi-file-check:not(:disabled)').prop('checked', isChecked);
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
        self.clearRedirectTimer($notification);
        $notification.slideUp(200, function() {
          $(this).remove();
        });
        sessionStorage.removeItem('doi_resource_files');
      });

      // Allow canceling redirect after multi-add
      $notification.on('click', '.doi-stay-here', function(e) {
        e.preventDefault();
        self.clearRedirectTimer($notification);
        $(this).replaceWith('<span class="text-muted">Staying on this form as requested.</span>');
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
        // Remove trailing slashes
        cleanUrl = cleanUrl.replace(/\/+$/, '');
        var parts = cleanUrl.split('/');
        // Get the last non-empty segment
        var filename = '';
        for (var i = parts.length - 1; i >= 0; i--) {
          if (parts[i] && parts[i].trim() !== '') {
            filename = parts[i];
            break;
          }
        }
        return filename || 'resource';
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
        var ext = filename.split('.').pop().toUpperCase();
        if (ext === 'PDF') {
          return 'URL';
        }
        return ext;
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
      if (this.cachedPackageId) {
        return this.cachedPackageId;
      }

      var optionId = this.options.packageId || this.el.data('packageId');
      if (optionId) {
        this.cachedPackageId = optionId;
        return optionId;
      }
      
      // Try hidden fields commonly present in resource forms
      var $pkgField = this.form.find('input[name="package_id"], input[name="pkg_name"], input[name="dataset_id"]').first();
      if ($pkgField.length && $pkgField.val()) {
        this.cachedPackageId = $pkgField.val();
        return this.cachedPackageId;
      }

      // Try from URL
      var fromUrl = this.extractPackageIdFromPath(window.location.pathname);
      if (fromUrl) {
        this.cachedPackageId = fromUrl;
        return fromUrl;
      }
      
      // Try from form action
      if (this.form.length) {
        var action = this.form.attr('action') || '';
        var fromAction = this.extractPackageIdFromPath(action);
        if (fromAction) {
          this.cachedPackageId = fromAction;
          return fromAction;
        }
      }
      
      return null;
    },

    extractPackageIdFromPath: function(path) {
      if (!path) return null;
      try {
        var clean = path.split('?')[0];
        var parts = clean.split('/').filter(function(p) { return p; });
        var datasetIndex = parts.indexOf('dataset');
        if (datasetIndex === -1 || parts.length <= datasetIndex + 1) {
          return null;
        }
        var candidate = decodeURIComponent(parts[datasetIndex + 1]);
        if ((candidate === 'new_resource' || candidate === 'new_metadata') && parts.length > datasetIndex + 2) {
          return decodeURIComponent(parts[datasetIndex + 2]);
        }
        return candidate;
      } catch (e) {
        console.warn('[schemingdcat-resource-auto-fields] Could not parse package ID from path', e);
        return null;
      }
    },
    
    /**
     * Update count of selected files for multi-select
     */
    updateMultiSelectCount: function($notification) {
      var $enabledChecks = $notification.find('.doi-file-check:not(:disabled)');
      var count = $enabledChecks.filter(':checked').length;
      $notification.find('.selected-count').text(count);
      $notification.find('.doi-add-selected').prop('disabled', count === 0);
      if ($enabledChecks.length > 0) {
        var allChecked = count === $enabledChecks.length;
        $notification.find('.doi-select-all').prop('checked', allChecked);
      }
    },
    
    /**
     * Add selected DOI files as separate resources
     */
    addSelectedDoiResources: function($notification, packageId, doiData) {
      var self = this;
      var $selectedItems = $notification.find('.doi-file-check:checked:not(:disabled)').closest('.doi-file-item');
      this.clearMultiErrors($notification);
      this.clearRedirectTimer($notification);
      
      if ($selectedItems.length === 0) {
        console.log('[schemingdcat-resource-auto-fields] No files selected');
        return;
      }
      
      if (!packageId) {
        console.error('[schemingdcat-resource-auto-fields] No package ID found');
        this.showMultiErrorMessage($notification, 'No dataset was detected. Please finish creating the dataset first or reload this page.');
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
      var $selectAll = $notification.find('.doi-select-all');
      var $checks = $notification.find('.doi-file-check');
      
      $progressBar.removeClass('progress-bar-success progress-bar-warning').addClass('active').css('width', '0%');
      $progressStatus.text('');
      $addBtn.prop('disabled', true).html('<i class="fa fa-spinner fa-spin"></i> Creating resources...');
      $selectAll.prop('disabled', true);
      $checks.prop('disabled', true);
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
        
        self.createResourceFromDoiFile(packageId, file, doiData, index, function(success, result) {
        if (success) {
          completed++;
          // Mark as created
          $selectedItems.eq(index).addClass('used created')
            .find('.doi-file-check').prop('disabled', true).prop('checked', false);
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
     * @param {string} packageId - The dataset package ID
     * @param {Object} file - File data object with url, filename, format, etc.
     * @param {Object} doiData - Original DOI metadata
     * @param {number} index - Index of the file in the selection (for unique naming)
     * @param {Function} callback - Callback function(success, result)
     */
    createResourceFromDoiFile: function(packageId, file, doiData, index, callback) {
      var self = this;
      
      // Generate resource name from filename or description
      var resourceName = this.getDisplayName(file, index);
      var inferredFormat = file.format || this.getFormatFromUrl(file.url);
      
      // Ensure name is not empty
      if (!resourceName || resourceName.trim() === '') {
        resourceName = this.getFilenameFromUrl(file.url).replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');
      }
      // If still empty or generic, create a unique name with index and format
      if (!resourceName || resourceName.trim() === '' || resourceName === 'resource') {
        var formatLabel = inferredFormat ? ' (' + inferredFormat + ')' : '';
        resourceName = (doiData.title ? doiData.title.substring(0, 50) : 'DOI Resource') + formatLabel + ' - ' + (index + 1);
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
      var self = this;
      var $progress = $notification.find('.doi-multi-progress');
      var $progressBar = $progress.find('.progress-bar');
      var $progressStatus = $progress.find('.doi-progress-status');
      var $addBtn = $notification.find('.doi-add-selected');
      var $selectAll = $notification.find('.doi-select-all');
      
      $progressBar.css('width', '100%').removeClass('active');
      
      if (errors.length === 0) {
        $progressBar.addClass('progress-bar-success');
        $progressStatus.html('<i class="fa fa-check-circle text-success"></i> ' + 
          completed + ' resource(s) created successfully!');
        $addBtn.html('<i class="fa fa-plus-circle"></i> Add selected (<span class="selected-count">0</span>)');
        $selectAll.prop('disabled', false).prop('checked', false);
        $notification.find('.doi-file-item').not('.used').find('.doi-file-check').prop('disabled', false).prop('checked', false);
        self.updateMultiSelectCount($notification);
        var redirectSeconds = 3;
        $notification.find('.doi-multi-success').html(
          '<i class="fa fa-check-circle"></i> ' + completed + ' resource(s) were created. Redirecting to the dataset in ' + redirectSeconds + ' seconds. ' +
          '<button type="button" class="btn btn-link btn-sm doi-stay-here">Stay here to upload a local file</button>'
        ).show();
        
        // Clear stored DOI data so future forms do not repeat the prompt
        sessionStorage.removeItem('doi_resource_files');

        // Redirect unless user chooses to stay
        var timer = setTimeout(function() {
          window.location.href = '/dataset/' + packageId;
        }, redirectSeconds * 1000);
        $notification.data('doiRedirectTimer', timer);
      } else {
        $progressBar.addClass('progress-bar-warning');
        $progressStatus.html('<i class="fa fa-exclamation-triangle text-warning"></i> ' + 
          completed + ' created, ' + errors.length + ' failed');
        var remainingSelected = $notification.find('.doi-file-check:checked:not(:disabled)').length;
        $addBtn.html('<i class="fa fa-plus-circle"></i> Add selected (<span class="selected-count">' + remainingSelected + '</span>)');
        $addBtn.prop('disabled', remainingSelected === 0);
        $selectAll.prop('disabled', false);
        $notification.find('.doi-file-item').not('.used').find('.doi-file-check').prop('disabled', false);
        self.updateMultiSelectCount($notification);
        self.renderMultiErrors($notification, errors);
      }
    },

    clearMultiErrors: function($notification) {
      var $errors = $notification.find('.doi-multi-errors');
      if ($errors.length) {
        $errors.hide().empty();
      }
      var $success = $notification.find('.doi-multi-success');
      if ($success.length) {
        $success.hide().empty();
      }
    },

    /**
     * Clear a pending redirect timer (if any)
     */
    clearRedirectTimer: function($notification) {
      var timer = $notification && $notification.data('doiRedirectTimer');
      if (timer) {
        clearTimeout(timer);
        $notification.removeData('doiRedirectTimer');
      }
    },

    showMultiErrorMessage: function($notification, message) {
      var $errors = $notification.find('.doi-multi-errors');
      if ($errors.length) {
        $errors.html('<i class="fa fa-exclamation-triangle"></i> ' + this.escapeHtml(message)).show();
      } else {
        alert(message);
      }
    },

    renderMultiErrors: function($notification, errors) {
      var $errors = $notification.find('.doi-multi-errors');
      if (!$errors.length || !errors || errors.length === 0) {
        return;
      }
      var self = this;
      var items = errors.map(function(item) {
        var label = 'Resource';
        if (item.file) {
          label = self.getDisplayName(item.file, 0) || item.file.url || 'Resource';
        }
        var errorText = item.error;
        if (errorText === undefined || errorText === null) {
          errorText = 'Unknown error';
        } else if (typeof errorText !== 'string') {
          try {
            errorText = JSON.stringify(errorText);
          } catch (e) {
            errorText = String(errorText);
          }
        }
        return '<li><strong>' + self.escapeHtml(label) + ':</strong> ' + self.escapeHtml(errorText) + '</li>';
      }).join('');
      $errors.html('<strong>Some resources could not be created:</strong><ul class="list-unstyled">' + items + '</ul>').show();
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
        '.doi-upload-note {' +
          'margin-bottom: 10px;' +
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
          'margin: 0;' +
          'font-weight: 600;' +
          'color: #444;' +
          'display: flex;' +
          'align-items: center;' +
          'gap: 6px;' +
          'cursor: pointer;' +
        '}' +
        '.doi-actions-row {' +
          'display: flex;' +
          'align-items: center;' +
          'gap: 10px;' +
          'justify-content: space-between;' +
          'flex-wrap: wrap;' +
          'margin-bottom: 10px;' +
        '}' +
        '.doi-files-list {' +
          'max-height: 240px;' +
          'overflow-y: auto;' +
          'border: 1px solid #e0e0e0;' +
          'border-radius: 6px;' +
          'background: #fafafa;' +
        '}' +
        '.doi-file-item {' +
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
        '.doi-file-main {' +
          'display: flex;' +
          'flex-direction: column;' +
          'gap: 4px;' +
        '}' +
        '.doi-file-check-label {' +
          'display: flex;' +
          'align-items: center;' +
          'gap: 8px;' +
          'font-weight: 600;' +
          'color: #333;' +
          'margin: 0;' +
          'cursor: pointer;' +
        '}' +
        '.doi-file-check-label input {' +
          'margin: 0;' +
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
        '.doi-inline-actions {' +
          'display: flex;' +
          'align-items: center;' +
          'gap: 10px;' +
          'margin-top: 8px;' +
          'flex-wrap: wrap;' +
        '}' +
        '.doi-inline-actions .btn-link {' +
          'padding: 0;' +
        '}' +
        '.doi-inline-hint {' +
          'font-size: 12px;' +
          'color: #666;' +
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
        '.doi-multi-errors {' +
          'margin-top: 10px;' +
        '}' +
        '.doi-multi-success {' +
          'margin-top: 10px;' +
        '}' +
        '</style>';
      
      $('head').append(styles);
    },

    /**
     * Add a small note above the upload widget to clarify DOI behaviour
     */
    addUploadGuidance: function() {
      var $wrapper = this.form.find('.schemingdcat-upload-wrapper').first();
      if (!$wrapper.length || $wrapper.data('doi-guidance-added')) {
        return;
      }
      var $note = $('<div>', {
        class: 'alert alert-info doi-upload-note',
        html: '<i class="fa fa-info-circle"></i> Links from the DOI are added as remote resources. You can still upload a local file below for this resource.'
      });
      $wrapper.prepend($note);
      $wrapper.data('doi-guidance-added', true);
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
      if ($urlField.length) {
        $urlField.val(url).trigger('change');
        console.log('[schemingdcat-resource-auto-fields] Set URL field:', url);
      }
      
      // Try to set name/title field
      if (filename) {
        var $nameField = this.form.find('input[name="name"]');
        if ($nameField.length) {
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
        html: '<i class="fa fa-check-circle"></i> Link from DOI applied to the form. You can still upload a local file.'
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
