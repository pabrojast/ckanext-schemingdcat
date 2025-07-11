ckan.module('schemingdcat-multi-resource-upload', function ($) {
  return {
    initialize: function () {
      var self = this;
      
      console.log('[schemingdcat-multi-upload] Initializing multiple file upload module');

      // Enable multiple selection in all resource file inputs
      self._enableMultipleSelection();
      
      // Add drag & drop support for multiple files
      self._enableMultipleDragDrop();

      // Delegate change event to capture multiple selections
      $(document).on('change', 'input[type="file"][id^="field-resource-upload"]', function (e) {
        var $input = $(this);
        var files = e.target.files;
        if (!files || files.length <= 1) {
          // Normal case (single file): let CKAN handle with its usual flow
          return;
        }
        self._handleMultipleFiles($input, files);
      });
      
      // Enhance existing button if present
      self._enhanceAddButton();
    },

    /* Add multiple attribute to existing inputs */
    _enableMultipleSelection: function () {
      $('input[type="file"][id^="field-resource-upload"]').attr('multiple', 'multiple');
      console.log('[schemingdcat-multi-upload] Enabled multiple selection on file inputs');
    },
    
    /* Enable multiple drag & drop in upload zones */
    _enableMultipleDragDrop: function () {
      var self = this;
      
      // Find all existing upload zones
      $('.upload-dropzone, .schemingdcat-upload-wrapper').each(function() {
        var $dropzone = $(this);
        
        $dropzone.on('drop', function(e) {
          var dt = e.originalEvent.dataTransfer;
          if (dt && dt.files && dt.files.length > 1) {
            e.preventDefault();
            e.stopPropagation();
            
            // Find associated file input
            var $fileInput = $dropzone.find('input[type="file"]').first();
            if (!$fileInput.length) {
              $fileInput = $dropzone.closest('.form-group').find('input[type="file"]').first();
            }
            
            if ($fileInput.length) {
              console.log('[schemingdcat-multi-upload] Detected ' + dt.files.length + ' files in drag & drop');
              self._handleMultipleFiles($fileInput, dt.files);
            }
          }
        });
      });
    },
    
    /* Enhance existing add resource button */
    _enhanceAddButton: function () {
      var $addBtn = this._findAddButton();
      if ($addBtn.length) {
        console.log('[schemingdcat-multi-upload] Add resource button found and enhanced');
        
        // Add icon if it doesn't have one
        if (!$addBtn.find('i').length) {
          var icon = document.createElement('i');
          icon.className = 'fa fa-plus';
          icon.style.marginRight = '5px';
          $addBtn.prepend(icon);
        }
        
        // Add tooltip
        $addBtn.attr('title', 'Click to add another resource, or select multiple files above to create them automatically');
      }
    },
    
    /* Find add resource button with better logic */
    _findAddButton: function () {
      var selectors = [
        '#add-resource',
        '.add-resource',
        'button[data-module="add-resource"]',
        'button[data-action="add-resource"]',
        'button.resource-add',
        '.multi-resource-controls button'
      ];
      
      for (var i = 0; i < selectors.length; i++) {
        var $btn = $(selectors[i]);
        if ($btn.length) {
          console.log('[schemingdcat-multi-upload] Button found with selector: ' + selectors[i]);
          return $btn;
        }
      }
      
      console.warn('[schemingdcat-multi-upload] No add resource button found');
      return $();
    },

    /* Handle multiple selection by splitting files into resource blocks */
    _handleMultipleFiles: function ($originInput, files) {
      var filesArr = Array.prototype.slice.call(files);
      if (!filesArr.length) return;
      
      console.log('[schemingdcat-multi-upload] Processing ' + filesArr.length + ' files');
      
      // Show visual feedback
      this._showProcessingFeedback(filesArr.length);

      // Keep first file in current block
      var firstFile = filesArr.shift();
      this._setInputFile($originInput, firstFile);
      this._autoFillFields($originInput.closest('.resource-upload-field, .form-group'), firstFile);

      var self = this;
      var processed = 1;
      
      // Process remaining files with delay
      filesArr.forEach(function (file, index) {
        setTimeout(function() {
          self._addResourceWithFile(file, function() {
            processed++;
            self._updateProcessingFeedback(processed, filesArr.length + 1);
            
            if (processed === filesArr.length + 1) {
              self._hideProcessingFeedback();
              self._showSuccessFeedback(processed);
            }
          });
        }, (index + 1) * 300); // Staggered delay for better UX
      });
    },

    /* Create new resource block by clicking standard button and fill data */
    _addResourceWithFile: function (file, callback) {
      var self = this;
      var $addBtn = this._findAddButton();
      
      if (!$addBtn.length) {
        console.error('[schemingdcat-multi-upload] Add resource button not found');
        if (callback) callback(false);
        return;
      }

      $addBtn.trigger('click');

      // Wait for DOM to update with longer timeout if needed
      var attempts = 0;
      var maxAttempts = 10;
      
      function tryFindNewResource() {
        attempts++;
        var $wrapper = $('.resource-upload-field').last();
        
        if ($wrapper.length) {
          var $fileInput = $wrapper.find('input[type="file"][id^="field-resource-upload"]');
          if ($fileInput.length) {
            // Force multiple attribute in case template doesn't have it
            $fileInput.attr('multiple', 'multiple');
            self._setInputFile($fileInput, file);
            self._autoFillFields($wrapper, file);
            console.log('[schemingdcat-multi-upload] Resource added successfully: ' + file.name);
            if (callback) callback(true);
            return;
          }
        }
        
        if (attempts < maxAttempts) {
          setTimeout(tryFindNewResource, 250);
        } else {
          console.error('[schemingdcat-multi-upload] Could not create new resource after ' + maxAttempts + ' attempts');
          if (callback) callback(false);
        }
      }
      
      setTimeout(tryFindNewResource, 250);
    },

    /* Assign File object to input using DataTransfer */
    _setInputFile: function ($input, file) {
      if (typeof DataTransfer !== 'undefined') {
        try {
          var dt = new DataTransfer();
          dt.items.add(file);
          $input[0].files = dt.files;
          
          // Trigger change event for other modules to respond
          $input.trigger('change');
        } catch (err) {
          console.warn('[schemingdcat-multi-upload] DataTransfer not supported in this browser: ' + err.message);
        }
      }
    },

    /* Auto-fill basic fields (name, format, created) with better logic */
    _autoFillFields: function ($wrapper, file) {
      // Name (without extension)
      var baseName = file.name.replace(/\.[^.]+$/, '');
      var $nameField = $wrapper.find('input[name$="name"], input[name*="name"]').first();
      if ($nameField.length && !$nameField.val()) {
        $nameField.val(baseName);
      }

      // Format (extension) with improved mapping
      var ext = file.name.split('.').pop().toUpperCase();
      var formatMap = {
        'XLSX': 'XLS',
        'GEOJSON': 'GeoJSON',
        'JPEG': 'JPEG',
        'JPG': 'JPEG',
        'HTM': 'HTML',
        'TXT': 'TXT',
        'DOC': 'DOC',
        'DOCX': 'DOC',
        'PPT': 'PPT',
        'PPTX': 'PPT'
      };
      var format = formatMap[ext] || ext;
      
      var $formatField = $wrapper.find('input[name$="format"], input[name*="format"]').first();
      if ($formatField.length && !$formatField.val()) {
        $formatField.val(format);
      }

      // Date (created) if exists and empty
      var $created = $wrapper.find('input[name$="created"], input[name*="created"]').first();
      if ($created.length && !$created.val()) {
        var today = new Date().toISOString().slice(0, 10);
        $created.val(today);
      }
      
      // Automatic description
      var $description = $wrapper.find('textarea[name$="description"], textarea[name*="description"]').first();
      if ($description.length && !$description.val()) {
        $description.val('Uploaded file: ' + file.name + ' (' + this._formatFileSize(file.size) + ')');
      }
    },
    
    /* Format file size */
    _formatFileSize: function (bytes) {
      if (bytes === 0) return '0 Bytes';
      var k = 1024;
      var sizes = ['Bytes', 'KB', 'MB', 'GB'];
      var i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    /* Show visual feedback during processing */
    _showProcessingFeedback: function (totalFiles) {
      // Create feedback container
      var feedbackDiv = document.createElement('div');
      feedbackDiv.className = 'multi-upload-feedback alert alert-info';
      
      // Create spinner icon
      var spinner = document.createElement('i');
      spinner.className = 'fa fa-spinner fa-spin';
      spinner.style.marginRight = '8px';
      
      // Create text
      var text = document.createTextNode('Processing ' + totalFiles + ' files...');
      
      // Create progress container
      var progressContainer = document.createElement('div');
      progressContainer.className = 'progress';
      progressContainer.style.marginTop = '10px';
      
      // Create progress bar
      var progressBar = document.createElement('div');
      progressBar.className = 'progress-bar';
      progressBar.style.width = '0%';
      
      // Assemble elements
      progressContainer.appendChild(progressBar);
      feedbackDiv.appendChild(spinner);
      feedbackDiv.appendChild(text);
      feedbackDiv.appendChild(progressContainer);
      
      // Add to DOM
      var controlsElement = document.querySelector('.multi-resource-controls');
      if (controlsElement && controlsElement.parentNode) {
        controlsElement.parentNode.insertBefore(feedbackDiv, controlsElement.nextSibling);
      }
    },
    
    /* Update progress feedback */
    _updateProcessingFeedback: function (processed, total) {
      var percentage = (processed / total) * 100;
      var feedbackElement = document.querySelector('.multi-upload-feedback');
      
      if (feedbackElement) {
        // Update progress bar
        var progressBar = feedbackElement.querySelector('.progress-bar');
        if (progressBar) {
          progressBar.style.width = percentage + '%';
        }
        
        // Clear and rebuild content
        feedbackElement.innerHTML = '';
        
        // Create spinner
        var spinner = document.createElement('i');
        spinner.className = 'fa fa-spinner fa-spin';
        spinner.style.marginRight = '8px';
        
        // Create text
        var text = document.createTextNode('Processing files: ' + processed + '/' + total);
        
        // Create progress container
        var progressContainer = document.createElement('div');
        progressContainer.className = 'progress';
        progressContainer.style.marginTop = '10px';
        
        // Create progress bar
        var newProgressBar = document.createElement('div');
        newProgressBar.className = 'progress-bar';
        newProgressBar.style.width = percentage + '%';
        
        // Assemble
        progressContainer.appendChild(newProgressBar);
        feedbackElement.appendChild(spinner);
        feedbackElement.appendChild(text);
        feedbackElement.appendChild(progressContainer);
      }
    },
    
    /* Hide processing feedback */
    _hideProcessingFeedback: function () {
      setTimeout(function() {
        var feedbackElement = document.querySelector('.multi-upload-feedback');
        if (feedbackElement) {
          $(feedbackElement).fadeOut(500, function() {
            if (feedbackElement.parentNode) {
              feedbackElement.parentNode.removeChild(feedbackElement);
            }
          });
        }
      }, 1000);
    },
    
    /* Show success feedback */
    _showSuccessFeedback: function (totalProcessed) {
      // Create success container
      var successDiv = document.createElement('div');
      successDiv.className = 'multi-upload-success alert alert-success';
      
      // Create check icon
      var checkIcon = document.createElement('i');
      checkIcon.className = 'fa fa-check';
      checkIcon.style.marginRight = '8px';
      
      // Create text
      var text = document.createTextNode('Success! Created ' + totalProcessed + ' resources.');
      
      // Assemble elements
      successDiv.appendChild(checkIcon);
      successDiv.appendChild(text);
      
      // Add to DOM
      var controlsElement = document.querySelector('.multi-resource-controls');
      if (controlsElement && controlsElement.parentNode) {
        controlsElement.parentNode.insertBefore(successDiv, controlsElement.nextSibling);
      }
      
      // Remove after delay
      setTimeout(function() {
        $(successDiv).fadeOut(500, function() {
          if (successDiv.parentNode) {
            successDiv.parentNode.removeChild(successDiv);
          }
        });
      }, 3000);
    }
  };
}); 