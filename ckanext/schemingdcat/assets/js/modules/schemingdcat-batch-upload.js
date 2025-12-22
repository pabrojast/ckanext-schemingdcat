/**
 * Batch Upload Module for CKAN Datasets
 * 
 * Allows uploading multiple files at once to create multiple resources
 * for a dataset. Provides drag-and-drop functionality, progress tracking,
 * and automatic metadata extraction.
 * 
 * Supports both direct upload to Azure (if available) and standard CKAN upload.
 */
ckan.module('schemingdcat-batch-upload', function ($) {
  'use strict';

  return {
    options: {
      i18n: {
        dropzone_title: 'Drag and drop multiple files here',
        dropzone_hint: 'or click to browse',
        dropzone_info: 'Each file will be created as a separate resource',
        uploading: 'Uploading...',
        uploading_to_azure: 'Uploading to cloud...',
        creating_resource: 'Creating resource...',
        processing: 'Processing...',
        complete: 'Complete',
        error: 'Error',
        remove: 'Remove',
        cancel: 'Cancel',
        retry: 'Retry',
        upload_all: 'Upload All',
        clear_all: 'Clear All',
        files_selected: 'files selected',
        file_selected: 'file selected'
      },
      maxFileSize: 500 * 1024 * 1024, // 500MB default
      allowedExtensions: null, // null = all allowed
      autoUpload: false,
      extractMetadata: true,
      packageId: null,
      useDirectUpload: true // Try to use Azure direct upload if available
    },

    initialize: function () {
      var self = this;
      
      console.log('[schemingdcat-batch-upload] Initializing batch upload module');
      
      // Get package ID from data attribute or URL
      this.packageId = this.options.packageId || this._getPackageIdFromUrl();
      
      if (!this.packageId) {
        console.warn('[schemingdcat-batch-upload] No package ID found, batch upload disabled');
        return;
      }
      
      // File queue
      this.fileQueue = [];
      this.uploadInProgress = false;
      this.azureAvailable = null; // Will be checked on first upload
      
      // Create UI
      this._createBatchUploadUI();
      
      // Bind events
      this._bindEvents();
      
      // Check Azure availability
      this._checkAzureAvailability();
    },

    _getPackageIdFromUrl: function() {
      // Try to get package ID from URL path
      var path = window.location.pathname;
      var match = path.match(/\/dataset\/([^\/]+)/);
      if (match) {
        return match[1];
      }
      
      // Try from form action
      var form = this.el.closest('form');
      if (form.length) {
        var action = form.attr('action') || '';
        match = action.match(/\/dataset\/([^\/]+)/);
        if (match) {
          return match[1];
        }
      }
      
      return null;
    },

    _checkAzureAvailability: function() {
      var self = this;
      
      // Test Azure endpoint with a dummy request
      $.ajax({
        url: '/api/get-azure-upload-url',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ filename: 'test.txt' }),
        success: function(response) {
          self.azureAvailable = response.success === true;
          console.log('[schemingdcat-batch-upload] Azure direct upload available:', self.azureAvailable);
        },
        error: function() {
          self.azureAvailable = false;
          console.log('[schemingdcat-batch-upload] Azure direct upload not available, using standard upload');
        }
      });
    },

    _createBatchUploadUI: function() {
      var self = this;
      var i18n = this.options.i18n;
      
      var html = `
        <div class="batch-upload-container">
          <div class="batch-dropzone" id="batch-dropzone">
            <div class="dropzone-content">
              <div class="dropzone-icon">
                <i class="fa fa-cloud-upload fa-3x"></i>
              </div>
              <h4>${i18n.dropzone_title}</h4>
              <p class="drop-hint">${i18n.dropzone_hint}</p>
              <p class="text-muted small">${i18n.dropzone_info}</p>
              <input type="file" 
                     id="batch-file-input" 
                     class="batch-file-input" 
                     multiple 
                     style="display: none;">
            </div>
          </div>
          
          <div class="batch-file-list" style="display: none;">
            <div class="batch-file-header">
              <span class="file-count"></span>
              <div class="batch-actions">
                <button type="button" class="btn btn-sm btn-primary batch-upload-all">
                  <i class="fa fa-upload"></i> ${i18n.upload_all}
                </button>
                <button type="button" class="btn btn-sm btn-default batch-clear-all">
                  <i class="fa fa-trash"></i> ${i18n.clear_all}
                </button>
              </div>
            </div>
            <div class="batch-files"></div>
          </div>
          
          <div class="batch-upload-progress" style="display: none;">
            <div class="progress">
              <div class="progress-bar progress-bar-striped active" role="progressbar" style="width: 0%">
                <span class="progress-text">0%</span>
              </div>
            </div>
            <p class="upload-status"></p>
          </div>
        </div>
      `;
      
      this.el.html(html);
      
      // Cache elements
      this.$dropzone = this.el.find('.batch-dropzone');
      this.$fileInput = this.el.find('.batch-file-input');
      this.$fileList = this.el.find('.batch-file-list');
      this.$fileCount = this.el.find('.file-count');
      this.$filesContainer = this.el.find('.batch-files');
      this.$progressContainer = this.el.find('.batch-upload-progress');
      this.$progressBar = this.el.find('.progress-bar');
      this.$progressText = this.el.find('.progress-text');
      this.$uploadStatus = this.el.find('.upload-status');
    },

    _bindEvents: function() {
      var self = this;
      
      // Dropzone click
      this.$dropzone.on('click', function(e) {
        if (!$(e.target).is('input')) {
          self.$fileInput.trigger('click');
        }
      });
      
      // File input change
      this.$fileInput.on('change', function(e) {
        self._handleFileSelection(e.target.files);
      });
      
      // Drag and drop
      this.$dropzone.on('dragenter dragover', function(e) {
        e.preventDefault();
        e.stopPropagation();
        $(this).addClass('dragover');
      });
      
      this.$dropzone.on('dragleave', function(e) {
        e.preventDefault();
        e.stopPropagation();
        $(this).removeClass('dragover');
      });
      
      this.$dropzone.on('drop', function(e) {
        e.preventDefault();
        e.stopPropagation();
        $(this).removeClass('dragover');
        
        var dt = e.originalEvent.dataTransfer;
        if (dt && dt.files) {
          self._handleFileSelection(dt.files);
        }
      });
      
      // Upload all button
      this.el.find('.batch-upload-all').on('click', function() {
        self._uploadAllFiles();
      });
      
      // Clear all button
      this.el.find('.batch-clear-all').on('click', function() {
        self._clearAllFiles();
      });
    },

    _handleFileSelection: function(files) {
      var self = this;
      
      if (!files || files.length === 0) return;
      
      Array.prototype.forEach.call(files, function(file) {
        // Check file size
        if (self.options.maxFileSize && file.size > self.options.maxFileSize) {
          console.warn('[schemingdcat-batch-upload] File too large:', file.name);
          return;
        }
        
        // Check if already in queue
        var exists = self.fileQueue.some(function(f) {
          return f.name === file.name && f.size === file.size;
        });
        
        if (!exists) {
          self._addFileToQueue(file);
        }
      });
      
      this._updateUI();
      
      // Clear input for re-selection of same files
      this.$fileInput.val('');
    },

    _addFileToQueue: function(file) {
      var fileItem = {
        id: this._generateId(),
        file: file,
        name: file.name,
        size: file.size,
        status: 'pending', // pending, uploading, creating, complete, error
        progress: 0,
        error: null,
        resourceId: null,
        metadata: null,
        azureUrl: null,
        blobPath: null,
        resourceName: null // Will be set during render
      };
      
      // Pre-calculate resource name
      fileItem.resourceName = this._getResourceName(file.name);
      
      this.fileQueue.push(fileItem);
      this._renderFileItem(fileItem);
      
      // Extract metadata if enabled
      if (this.options.extractMetadata) {
        this._extractFileMetadata(fileItem);
      }
    },

    _renderFileItem: function(fileItem) {
      var self = this;
      var i18n = this.options.i18n;
      
      var ext = fileItem.name.split('.').pop().toUpperCase();
      var iconClass = this._getFileIcon(fileItem.name);
      var sizeFormatted = this._formatFileSize(fileItem.size);
      var resourceName = fileItem.resourceName || this._getResourceName(fileItem.name);
      var originalName = fileItem.name;
      
      // Debug logging
      console.log('[schemingdcat-batch-upload] Rendering file:', {
        originalName: originalName,
        resourceName: resourceName,
        ext: ext
      });
      
      // Build HTML using DOM methods to avoid escaping issues
      var $item = $('<div class="batch-file-item"></div>').attr('data-file-id', fileItem.id);
      
      var $icon = $('<div class="file-icon"></div>').append($('<i class="fa"></i>').addClass(iconClass));
      
      var $info = $('<div class="file-info"></div>');
      var $fileName = $('<div class="file-name"></div>').text(resourceName).attr('title', originalName);
      var $fileMeta = $('<div class="file-meta"></div>');
      $fileMeta.append($('<span class="file-size"></span>').text(sizeFormatted));
      $fileMeta.append($('<span class="file-format badge"></span>').text(ext));
      $fileMeta.append($('<span class="file-original text-muted small"></span>').text('(' + originalName + ')'));
      
      var $progress = $('<div class="file-progress" style="display: none;"></div>');
      $progress.append('<div class="progress progress-sm"><div class="progress-bar" style="width: 0%"></div></div>');
      
      var $status = $('<div class="file-status"></div>');
      
      $info.append($fileName).append($fileMeta).append($progress).append($status);
      
      var $actions = $('<div class="file-actions"></div>');
      var $removeBtn = $('<button type="button" class="btn btn-sm btn-danger file-remove"></button>')
        .attr('title', i18n.remove)
        .append('<i class="fa fa-times"></i>');
      $actions.append($removeBtn);
      
      $item.append($icon).append($info).append($actions);
      
      // Bind remove button
      $removeBtn.on('click', function() {
        self._removeFileFromQueue(fileItem.id);
      });
      
      this.$filesContainer.append($item);
    },

    _updateUI: function() {
      var i18n = this.options.i18n;
      var count = this.fileQueue.length;
      
      if (count > 0) {
        this.$fileList.show();
        this.$fileCount.text(count + ' ' + (count === 1 ? i18n.file_selected : i18n.files_selected));
      } else {
        this.$fileList.hide();
      }
    },

    _removeFileFromQueue: function(fileId) {
      var self = this;
      
      // Remove from queue
      this.fileQueue = this.fileQueue.filter(function(f) {
        return f.id !== fileId;
      });
      
      // Remove from UI
      this.$filesContainer.find('[data-file-id="' + fileId + '"]').remove();
      
      this._updateUI();
    },

    _clearAllFiles: function() {
      this.fileQueue = [];
      this.$filesContainer.empty();
      this._updateUI();
    },

    _uploadAllFiles: function() {
      var self = this;
      
      if (this.uploadInProgress) {
        console.log('[schemingdcat-batch-upload] Upload already in progress');
        return;
      }
      
      var pendingFiles = this.fileQueue.filter(function(f) {
        return f.status === 'pending';
      });
      
      if (pendingFiles.length === 0) {
        console.log('[schemingdcat-batch-upload] No pending files to upload');
        return;
      }
      
      this.uploadInProgress = true;
      this.$progressContainer.show();
      
      // Disable buttons during upload
      this.el.find('.batch-upload-all, .batch-clear-all').prop('disabled', true);
      
      // Upload files sequentially
      this._uploadNextFile(0, pendingFiles);
    },

    _uploadNextFile: function(index, files) {
      var self = this;
      
      if (index >= files.length) {
        // All files uploaded
        this._onAllUploadsComplete();
        return;
      }
      
      var fileItem = files[index];
      var totalFiles = files.length;
      
      this._updateOverallProgress(index, totalFiles);
      this.$uploadStatus.text('Uploading ' + (index + 1) + ' of ' + totalFiles + ': ' + fileItem.name);
      
      // Decide upload method
      if (this.options.useDirectUpload && this.azureAvailable) {
        this._uploadFileDirectToAzure(fileItem, function(success) {
          setTimeout(function() {
            self._uploadNextFile(index + 1, files);
          }, 300);
        });
      } else {
        this._uploadFileToCkan(fileItem, function(success) {
          setTimeout(function() {
            self._uploadNextFile(index + 1, files);
          }, 300);
        });
      }
    },

    /**
     * Upload file directly to Azure, then create CKAN resource
     */
    _uploadFileDirectToAzure: function(fileItem, callback) {
      var self = this;
      var $item = this.$filesContainer.find('[data-file-id="' + fileItem.id + '"]');
      var $progress = $item.find('.file-progress');
      var $progressBar = $item.find('.progress-bar');
      var $status = $item.find('.file-status');
      var $removeBtn = $item.find('.file-remove');
      var i18n = this.options.i18n;
      
      // Update status
      fileItem.status = 'uploading';
      $item.addClass('uploading');
      $progress.show();
      $removeBtn.hide();
      $status.html('<i class="fa fa-spinner fa-spin"></i> ' + i18n.uploading_to_azure);
      
      // Step 1: Get Azure SAS URL
      $.ajax({
        url: '/api/get-azure-upload-url',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
          filename: fileItem.name,
          content_type: fileItem.file.type || 'application/octet-stream'
        }),
        success: function(response) {
          if (!response.success) {
            self._handleUploadError(fileItem, $item, $progress, $status, $removeBtn, response.error || 'Failed to get upload URL');
            callback(false);
            return;
          }
          
          fileItem.azureUrl = response.upload_url;
          fileItem.blobPath = response.blob_path;
          
          // Step 2: Upload to Azure
          self._uploadToAzureBlob(fileItem, $progressBar, function(uploadSuccess) {
            if (!uploadSuccess) {
              self._handleUploadError(fileItem, $item, $progress, $status, $removeBtn, 'Failed to upload to cloud storage');
              callback(false);
              return;
            }
            
            // Step 3: Create CKAN resource with the blob URL
            $status.html('<i class="fa fa-spinner fa-spin"></i> ' + i18n.creating_resource);
            fileItem.status = 'creating';
            
            self._createResourceWithBlobUrl(fileItem, function(createSuccess, resourceData) {
              if (createSuccess) {
                fileItem.status = 'complete';
                fileItem.resourceId = resourceData.id;
                $item.removeClass('uploading').addClass('complete');
                $progress.hide();
                $status.html('<i class="fa fa-check text-success"></i> ' + i18n.complete);
                console.log('[schemingdcat-batch-upload] Resource created:', resourceData.id);
              } else {
                self._handleUploadError(fileItem, $item, $progress, $status, $removeBtn, 'Failed to create resource');
              }
              callback(createSuccess);
            });
          });
        },
        error: function(xhr, status, error) {
          // Fallback to standard upload
          console.log('[schemingdcat-batch-upload] Azure URL failed, falling back to standard upload');
          self.azureAvailable = false;
          self._uploadFileToCkan(fileItem, callback);
        }
      });
    },

    /**
     * Upload file directly to Azure Blob Storage
     */
    _uploadToAzureBlob: function(fileItem, $progressBar, callback) {
      var self = this;
      
      var xhr = new XMLHttpRequest();
      
      xhr.upload.addEventListener('progress', function(e) {
        if (e.lengthComputable) {
          var percent = Math.round((e.loaded / e.total) * 100);
          $progressBar.css('width', percent + '%');
          fileItem.progress = percent;
        }
      });
      
      xhr.addEventListener('load', function() {
        if (xhr.status >= 200 && xhr.status < 300) {
          callback(true);
        } else {
          console.error('[schemingdcat-batch-upload] Azure upload failed:', xhr.status, xhr.statusText);
          callback(false);
        }
      });
      
      xhr.addEventListener('error', function() {
        console.error('[schemingdcat-batch-upload] Azure upload error');
        callback(false);
      });
      
      xhr.open('PUT', fileItem.azureUrl, true);
      xhr.setRequestHeader('x-ms-blob-type', 'BlockBlob');
      xhr.setRequestHeader('Content-Type', fileItem.file.type || 'application/octet-stream');
      xhr.send(fileItem.file);
    },

    /**
     * Create CKAN resource pointing to the Azure blob
     * Includes retry with exponential backoff for transient errors
     */
    _createResourceWithBlobUrl: function(fileItem, callback, retryCount) {
      var self = this;
      retryCount = retryCount || 0;
      var maxRetries = 3;
      
      // Construct the blob URL (without SAS token)
      var blobUrl = fileItem.azureUrl.split('?')[0];
      
      var resourceData = this._buildResourceData(fileItem, blobUrl);
      
      // CRITICAL: Add Azure-specific fields for ResourceCloudStorage to detect the direct upload
      // and move the blob from temp path to final resources path
      if (fileItem.blobPath) {
        resourceData.azure_blob_path = fileItem.blobPath;
        resourceData.azure_upload = true;
      }
      
      $.ajax({
        url: '/api/3/action/resource_create',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(resourceData),
        success: function(response) {
          if (response.success) {
            callback(true, response.result);
          } else {
            console.error('[schemingdcat-batch-upload] Resource creation failed:', response.error);
            // Check if we should retry
            if (retryCount < maxRetries) {
              var delay = Math.pow(2, retryCount) * 1000; // 1s, 2s, 4s
              console.log('[schemingdcat-batch-upload] Retrying in ' + delay + 'ms (attempt ' + (retryCount + 1) + '/' + maxRetries + ')');
              setTimeout(function() {
                self._createResourceWithBlobUrl(fileItem, callback, retryCount + 1);
              }, delay);
            } else {
              callback(false, null);
            }
          }
        },
        error: function(xhr, status, error) {
          console.error('[schemingdcat-batch-upload] Resource creation error:', error, 'status:', xhr.status);
          
          // Retry on 5xx errors or network errors
          if (retryCount < maxRetries && (xhr.status >= 500 || xhr.status === 0)) {
            var delay = Math.pow(2, retryCount) * 1000; // 1s, 2s, 4s
            console.log('[schemingdcat-batch-upload] Server error, retrying in ' + delay + 'ms (attempt ' + (retryCount + 1) + '/' + maxRetries + ')');
            setTimeout(function() {
              self._createResourceWithBlobUrl(fileItem, callback, retryCount + 1);
            }, delay);
          } else {
            callback(false, null);
          }
        }
      });
    },

    /**
     * Standard CKAN upload (fallback when Azure is not available)
     */
    _uploadFileToCkan: function(fileItem, callback) {
      var self = this;
      var $item = this.$filesContainer.find('[data-file-id="' + fileItem.id + '"]');
      var $progress = $item.find('.file-progress');
      var $progressBar = $item.find('.progress-bar');
      var $status = $item.find('.file-status');
      var $removeBtn = $item.find('.file-remove');
      var i18n = this.options.i18n;
      
      // Update status
      fileItem.status = 'uploading';
      $item.addClass('uploading');
      $progress.show();
      $removeBtn.hide();
      $status.html('<i class="fa fa-spinner fa-spin"></i> ' + i18n.uploading);
      
      // Build resource data using helper function
      var resourceData = this._buildResourceData(fileItem, null);
      
      // Prepare form data
      var formData = new FormData();
      formData.append('upload', fileItem.file);
      
      // Add all resource data to form
      Object.keys(resourceData).forEach(function(key) {
        if (resourceData[key] !== null && resourceData[key] !== undefined) {
          formData.append(key, resourceData[key]);
        }
      });
      
      // Upload via CKAN API
      $.ajax({
        url: '/api/3/action/resource_create',
        type: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        xhr: function() {
          var xhr = new window.XMLHttpRequest();
          xhr.upload.addEventListener('progress', function(e) {
            if (e.lengthComputable) {
              var percent = Math.round((e.loaded / e.total) * 100);
              $progressBar.css('width', percent + '%');
              fileItem.progress = percent;
            }
          }, false);
          return xhr;
        },
        success: function(response) {
          if (response.success) {
            fileItem.status = 'complete';
            fileItem.resourceId = response.result.id;
            $item.removeClass('uploading').addClass('complete');
            $progress.hide();
            $status.html('<i class="fa fa-check text-success"></i> ' + i18n.complete);
            
            console.log('[schemingdcat-batch-upload] Resource created:', response.result.id);
          } else {
            self._handleUploadError(fileItem, $item, $progress, $status, $removeBtn, response.error);
          }
          callback(response.success);
        },
        error: function(xhr, status, error) {
          var errorMsg = error;
          try {
            var response = JSON.parse(xhr.responseText);
            errorMsg = response.error && response.error.message ? response.error.message : error;
          } catch(e) {}
          
          self._handleUploadError(fileItem, $item, $progress, $status, $removeBtn, errorMsg);
          callback(false);
        }
      });
    },

    _handleUploadError: function(fileItem, $item, $progress, $status, $removeBtn, error) {
      fileItem.status = 'error';
      fileItem.error = error;
      $item.removeClass('uploading').addClass('error');
      $progress.hide();
      $removeBtn.show();
      $status.html('<i class="fa fa-exclamation-triangle text-danger"></i> ' + this.options.i18n.error + ': ' + error);
      
      console.error('[schemingdcat-batch-upload] Upload error:', error);
    },

    _updateOverallProgress: function(current, total) {
      var percent = Math.round((current / total) * 100);
      this.$progressBar.css('width', percent + '%');
      this.$progressText.text(percent + '%');
    },

    _onAllUploadsComplete: function() {
      var self = this;
      this.uploadInProgress = false;
      
      // Re-enable buttons
      this.el.find('.batch-upload-all, .batch-clear-all').prop('disabled', false);
      
      // Count results
      var completed = this.fileQueue.filter(function(f) { return f.status === 'complete'; }).length;
      var errors = this.fileQueue.filter(function(f) { return f.status === 'error'; }).length;
      
      this.$progressBar.css('width', '100%');
      this.$progressText.text('100%');
      this.$uploadStatus.html(
        '<i class="fa fa-check-circle text-success"></i> ' +
        completed + ' resources created' +
        (errors > 0 ? ', <span class="text-danger">' + errors + ' errors</span>' : '')
      );
      
      // Reload page after delay if all successful
      if (errors === 0 && completed > 0) {
        setTimeout(function() {
          // Redirect to dataset page instead of reloading
          var datasetUrl = '/dataset/' + self.packageId;
          window.location.href = datasetUrl;
        }, 2000);
      }
    },

    _extractFileMetadata: function(fileItem) {
      var self = this;
      
      // Check if it's a spatial file
      var ext = fileItem.name.split('.').pop().toLowerCase();
      var spatialExts = ['shp', 'geojson', 'kml', 'gpkg', 'tif', 'tiff', 'zip'];
      
      if (spatialExts.indexOf(ext) === -1) {
        return;
      }
      
      // Try to extract spatial extent
      var formData = new FormData();
      formData.append('file', fileItem.file);
      
      $.ajax({
        url: '/schemingdcat/api/extract-spatial-extent',
        type: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
          if (response.success && response.extent) {
            fileItem.metadata = fileItem.metadata || {};
            fileItem.metadata.spatial = JSON.stringify(response.extent);
            
            // Add spatial_uri if detected
            if (response.spatial_uri) {
              fileItem.metadata.spatial_uri = response.spatial_uri;
            }
            
            console.log('[schemingdcat-batch-upload] Extracted metadata for:', fileItem.name);
          }
        },
        error: function() {
          // Silent fail - metadata extraction is optional
        }
      });
    },

    _getResourceName: function(filename) {
      // Remove extension and clean up name
      var name = filename.replace(/\.[^/.]+$/, '').replace(/[_-]/g, ' ').trim();
      
      // Ensure we always return a valid name
      if (!name || name.length === 0) {
        name = 'Resource ' + new Date().toISOString().slice(0, 10);
      }
      
      return name;
    },

    _getFileFormat: function(filename) {
      var ext = filename.split('.').pop().toUpperCase();
      var formatMap = {
        'XLSX': 'XLS',
        'GEOJSON': 'GeoJSON',
        'TIF': 'GeoTIFF',
        'TIFF': 'GeoTIFF'
      };
      return formatMap[ext] || ext;
    },

    _getTodayDate: function() {
      return new Date().toISOString().slice(0, 10);
    },

    _buildResourceData: function(fileItem, blobUrl) {
      // Use pre-calculated resourceName if available, otherwise generate it
      var resourceName = fileItem.resourceName || this._getResourceName(fileItem.name);
      
      var resourceData = {
        package_id: this.packageId,
        name: resourceName,
        format: this._getFileFormat(fileItem.name)
      };
      
      // Add URL if provided (for Azure upload)
      if (blobUrl) {
        resourceData.url = blobUrl;
        resourceData.url_type = 'upload';
      }
      
      // Add created date
      resourceData.created = this._getTodayDate();
      
      // Add extracted metadata if available
      if (fileItem.metadata) {
        Object.keys(fileItem.metadata).forEach(function(key) {
          if (fileItem.metadata[key] !== null && fileItem.metadata[key] !== undefined) {
            resourceData[key] = fileItem.metadata[key];
          }
        });
      }
      
      console.log('[schemingdcat-batch-upload] Resource data:', resourceData);
      return resourceData;
    },

    _getFileIcon: function(filename) {
      var ext = filename.split('.').pop().toLowerCase();
      var iconMap = {
        'pdf': 'fa-file-pdf-o',
        'doc': 'fa-file-word-o',
        'docx': 'fa-file-word-o',
        'xls': 'fa-file-excel-o',
        'xlsx': 'fa-file-excel-o',
        'csv': 'fa-file-text-o',
        'json': 'fa-file-code-o',
        'xml': 'fa-file-code-o',
        'zip': 'fa-file-archive-o',
        'shp': 'fa-map-o',
        'geojson': 'fa-map-o',
        'kml': 'fa-map-o',
        'gpkg': 'fa-map-o',
        'tif': 'fa-map-o',
        'tiff': 'fa-map-o'
      };
      return iconMap[ext] || 'fa-file-o';
    },

    _formatFileSize: function(bytes) {
      if (bytes === 0) return '0 Bytes';
      var k = 1024;
      var sizes = ['Bytes', 'KB', 'MB', 'GB'];
      var i = Math.floor(Math.log(bytes) / Math.log(k));
      return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i];
    },

    _generateId: function() {
      return 'file_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    },

    _escapeHtml: function(text) {
      var div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }
  };
});

