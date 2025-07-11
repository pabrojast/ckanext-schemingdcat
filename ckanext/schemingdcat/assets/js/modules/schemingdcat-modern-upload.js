ckan.module('schemingdcat-modern-upload', function ($) {
  return {
    initialize: function () {
      var self = this;
      var container = this.el;
      var wrapper = container.closest('.schemingdcat-upload-wrapper');
      
      if (!wrapper.length) return;
      
      var dropzone = wrapper.find('.upload-dropzone');
      var fileInput = wrapper.find('.upload-file-input');
      var browseButton = wrapper.find('.browse-button');
      var dropzoneContent = wrapper.find('.dropzone-content');
      var filePreview = wrapper.find('.file-preview');
      var removeButton = wrapper.find('.remove-file');
      var clearCheckbox = wrapper.find('input[type="checkbox"][id*="clear"]');
      var urlInput = wrapper.find('.url-input');
      var previewSyncTimer = null;
      
      // Get field URL from data attribute
      var fieldUrl = wrapper.data('field-url') || 'url';
      
      if (!fileInput.length || !dropzone.length) return;
      
      console.log('[schemingdcat-modern-upload] Initializing upload module');
      
      // Auto-fill date fields on initialization
      self._autoFillDateFields();
      
      // Enable multiple file selection
      fileInput.attr('multiple', 'multiple');
      
      // Add visual indicator for multiple file support
      self._addMultipleFileIndicator();
      
      // Browse button click
      browseButton.on('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        fileInput.trigger('click');
      });
      
      // Alternative click on dropzone
      dropzone.on('click', function(e) {
        if ($(e.target).closest('.browse-button').length === 0 && 
            $(e.target).closest('.remove-file').length === 0 &&
            $(e.target).closest('.file-preview').length === 0) {
          fileInput.trigger('click');
        }
      });
      
      // File input change
      fileInput.on('change', function(e) {
        var files = e.target.files;
        if (files && files.length > 0) {
          if (files.length === 1) {
            // Single file - normal display
            self.displayFile(files[0]);
          } else {
            // Multiple files - show first file but indicate multiple selection
            self.displayFile(files[0]);
            self._showMultipleFileIndicator(files.length);
          }
          
          // Auto-fill format field
          self._autoFillFormat(files[0]);
        }
      });
      
      // Remove file button
      removeButton.on('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        self.clearFile();
      });
      
      // Drag and drop events
      self._setupDragAndDrop();
      
      // URL input change for format detection
      if (urlInput.length) {
        urlInput.on('blur', function(e) {
          self._autoFillFormatFromUrl(e.target.value);
        });
      }
    },
    
    _autoFillDateFields: function() {
      // Auto-fill date fields if they exist and are empty
      var dateFields = $('input[type="date"]');
      dateFields.each(function() {
        var field = $(this);
        if ((field.attr('name').indexOf('created') !== -1 || 
             field.attr('name').indexOf('__0__created') !== -1) && !field.val()) {
          var today = new Date();
          var yyyy = today.getFullYear();
          var mm = today.getMonth() + 1;
          var dd = today.getDate();
          
          if (dd < 10) dd = '0' + dd;
          if (mm < 10) mm = '0' + mm;
          
          field.val(yyyy + '-' + mm + '-' + dd);
        }
      });
    },
    
    _addMultipleFileIndicator: function() {
      var wrapper = this.el.closest('.schemingdcat-upload-wrapper');
      var helpText = wrapper.find('.text-muted');
      
      if (helpText.length && !helpText.find('.multi-support-note').length) {
        var note = $('<span class="multi-support-note" style="display: block; font-weight: bold; color: #007bff; margin-top: 5px;">' +
          '<i class="fa fa-magic" style="margin-right: 5px;"></i>' +
          'Select multiple files to create several resources at once!' +
          '</span>');
        helpText.append(note);
      }
    },
    
    _setupDragAndDrop: function() {
      var self = this;
      var wrapper = this.el.closest('.schemingdcat-upload-wrapper');
      var dropzone = wrapper.find('.upload-dropzone');
      var fileInput = wrapper.find('.upload-file-input');
      
      // Prevent default drag behaviors
      $(document).on('dragenter dragover', function(e) {
        e.preventDefault();
        e.stopPropagation();
      });
      
      // Drag enter
      dropzone.on('dragenter', function(e) {
        e.preventDefault();
        e.stopPropagation();
        $(this).addClass('dragover');
      });
      
      // Drag over
      dropzone.on('dragover', function(e) {
        e.preventDefault();
        e.stopPropagation();
        var dt = e.originalEvent.dataTransfer;
        if (dt && dt.files && dt.files.length > 1) {
          $(this).addClass('multiple-dragover');
        } else {
          $(this).removeClass('multiple-dragover');
        }
        $(this).addClass('dragover');
      });
      
      // Drag leave
      dropzone.on('dragleave', function(e) {
        e.preventDefault();
        e.stopPropagation();
        // Check if we're really leaving the dropzone
        var rect = this.getBoundingClientRect();
        var x = e.originalEvent.clientX;
        var y = e.originalEvent.clientY;
        if (x < rect.left || x >= rect.right || y < rect.top || y >= rect.bottom) {
          $(this).removeClass('dragover multiple-dragover');
        }
      });
      
      // Drop
      dropzone.on('drop', function(e) {
        e.preventDefault();
        e.stopPropagation();
        $(this).removeClass('dragover multiple-dragover');
        
        var files = e.originalEvent.dataTransfer.files;
        if (files && files.length > 0) {
          // Try to set files to input using DataTransfer
          try {
            if (typeof DataTransfer !== 'undefined') {
              var dt = new DataTransfer();
              for (var i = 0; i < files.length; i++) {
                dt.items.add(files[i]);
              }
              fileInput[0].files = dt.files;
            }
          } catch (err) {
            console.warn('[schemingdcat-modern-upload] DataTransfer not supported, using fallback');
          }
          
          if (files.length === 1) {
            self.displayFile(files[0]);
          } else {
            self.displayFile(files[0]);
            self._showMultipleFileIndicator(files.length);
          }
          
          // Trigger change event for validation and other modules
          fileInput.trigger('change');
          
          // Auto-fill format
          self._autoFillFormat(files[0]);
        }
      });
    },
    
    _autoFillFormat: function(file) {
      var formatFields = $('input[name*="format"]');
      var formatField = null;
      
      formatFields.each(function() {
        var field = $(this);
        if (field.attr('name').indexOf('resources') !== -1 || field.attr('name') === 'format') {
          formatField = field;
          return false; // break
        }
      });
      
      if (formatField && formatField.length && !formatField.val()) {
        var fileName = file.name;
        var ext = fileName.split('.').pop().toUpperCase();
        
        var formatMap = {
          'CSV': 'CSV',
          'XLS': 'XLS', 
          'XLSX': 'XLS',
          'JSON': 'JSON',
          'GEOJSON': 'GeoJSON',
          'XML': 'XML',
          'RDF': 'RDF',
          'PDF': 'PDF',
          'DOC': 'DOC',
          'DOCX': 'DOC',
          'TXT': 'TXT',
          'ZIP': 'ZIP'
        };
        
        formatField.val(formatMap[ext] || ext);
        formatField.trigger('change');
      }
    },
    
    _autoFillFormatFromUrl: function(url) {
      if (!url) return;
      
      var formatFields = $('input[name*="format"]');
      var formatField = null;
      
      formatFields.each(function() {
        var field = $(this);
        if (field.attr('name').indexOf('resources') !== -1 || field.attr('name') === 'format') {
          formatField = field;
          return false; // break
        }
      });
      
      if (formatField && formatField.length && !formatField.val()) {
        // Extract extension from URL
        var urlParts = url.split('?')[0].split('.');
        if (urlParts.length > 1) {
          var ext = urlParts[urlParts.length - 1].toUpperCase();
          
          var formatMap = {
            'CSV': 'CSV',
            'XLS': 'XLS', 
            'XLSX': 'XLS',
            'JSON': 'JSON',
            'GEOJSON': 'GeoJSON',
            'XML': 'XML',
            'RDF': 'RDF',
            'PDF': 'PDF',
            'DOC': 'DOC',
            'DOCX': 'DOC',
            'TXT': 'TXT',
            'ZIP': 'ZIP'
          };
          
          formatField.val(formatMap[ext] || ext);
          formatField.trigger('change');
        }
      }
    },
    
    _showMultipleFileIndicator: function(fileCount) {
      var wrapper = this.el.closest('.schemingdcat-upload-wrapper');
      var dropzone = wrapper.find('.upload-dropzone');
      
      // Remove any existing indicator
      wrapper.find('.multi-upload-counter').remove();
      
      // Create new indicator
      var indicator = $('<div class="multi-upload-counter">' + fileCount + '</div>');
      
      // Position it relative to the dropzone
      dropzone.css('position', 'relative');
      dropzone.append(indicator);
      
      // Show temporary message
      var message = $('<div class="multi-upload-message alert alert-info" style="margin-top: 10px;">' +
        '<i class="fa fa-info-circle" style="margin-right: 8px;"></i>' +
        fileCount + ' files selected. The first file is shown above, ' +
        'others will be created as additional resources automatically.' +
        '</div>');
      
      dropzone.after(message);
      
      // Remove message after 5 seconds
      setTimeout(function() {
        message.fadeOut(500, function() {
          message.remove();
        });
      }, 5000);
    },
    
    displayFile: function(file) {
      var wrapper = this.el.closest('.schemingdcat-upload-wrapper');
      var dropzoneContent = wrapper.find('.dropzone-content');
      var filePreview = wrapper.find('.file-preview');
      var fileName = filePreview.find('.file-name');
      var fileSize = filePreview.find('.file-size');
      var fileIcon = filePreview.find('.file-icon');
      var fileInput = wrapper.find('.upload-file-input');
      
      // Check if there are multiple files selected
      var totalFiles = fileInput[0].files ? fileInput[0].files.length : 1;
      
      if (totalFiles > 1) {
        fileName.text(file.name + ' (+ ' + (totalFiles - 1) + ' more files)');
      } else {
        fileName.text(file.name);
      }
      
      // Update file size
      var size = this.formatFileSize(file.size);
      fileSize.text(size);
      
      // Update icon based on file type
      var iconClass = this.getFileIcon(file.name);
      fileIcon.removeClass().addClass('fa fa-2x file-icon ' + iconClass);
      
      // Show preview, hide dropzone content
      dropzoneContent.hide();
      filePreview.show();
      
      // If there's a clear checkbox for existing file, check it
      var clearCheckbox = wrapper.find('input[type="checkbox"][id*="clear"]');
      if (clearCheckbox.length) {
        clearCheckbox.prop('checked', true);
      }
      
      // Show progress animation
      var progressBar = filePreview.find('.upload-progress');
      var progressText = filePreview.find('.progress-text');
      
      if (progressBar.length) {
        progressBar.show();
        var progressFill = progressBar.find('.progress-fill');
        
        // After 2s (end of CSS animation), set bar to 100% and change text
        setTimeout(function() {
          if (progressFill.length) {
            progressFill.css({
              'animation': 'none',
              'width': '100%'
            });
          }
          if (progressText.length) {
            progressText.text('Done');
          }
        }, 2000);
      }
    },
    
    clearFile: function() {
      var wrapper = this.el.closest('.schemingdcat-upload-wrapper');
      var dropzoneContent = wrapper.find('.dropzone-content');
      var filePreview = wrapper.find('.file-preview');
      var fileInput = wrapper.find('.upload-file-input');
      
      // Clear file input
      fileInput.val('');
      
      // Show dropzone content, hide preview
      dropzoneContent.show();
      filePreview.hide();
      
      // Uncheck clear checkbox if exists
      var clearCheckbox = wrapper.find('input[type="checkbox"][id*="clear"]');
      if (clearCheckbox.length) {
        clearCheckbox.prop('checked', false);
      }
      
      // Remove multiple file indicators
      wrapper.find('.multi-upload-counter, .multi-upload-message').remove();
    },
    
    formatFileSize: function(bytes) {
      if (bytes === 0) return '0 Bytes';
      
      var k = 1024;
      var sizes = ['Bytes', 'KB', 'MB', 'GB'];
      var i = Math.floor(Math.log(bytes) / Math.log(k));
      
      var result = (bytes / Math.pow(k, i)).toFixed(2);
      return result + ' ' + sizes[i];
    },
    
    getFileIcon: function(filename) {
      var ext = filename.split('.').pop().toLowerCase();
      var iconMap = {
        'pdf': 'fa-file-pdf-o',
        'doc': 'fa-file-word-o',
        'docx': 'fa-file-word-o',
        'xls': 'fa-file-excel-o',
        'xlsx': 'fa-file-excel-o',
        'csv': 'fa-file-text-o',
        'txt': 'fa-file-text-o',
        'json': 'fa-file-code-o',
        'xml': 'fa-file-code-o',
        'zip': 'fa-file-archive-o',
        'jpg': 'fa-file-image-o',
        'jpeg': 'fa-file-image-o',
        'png': 'fa-file-image-o',
        'gif': 'fa-file-image-o'
      };
      return iconMap[ext] || 'fa-file-o';
    }
  };
});