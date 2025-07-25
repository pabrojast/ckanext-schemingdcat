ckan.module('schemingdcat-modern-upload', function ($) {
  return {
    initialize: function () {
      var self = this;
      var container = this.el;
      var dropzone = container.find('.upload-dropzone');
      var fileInput = dropzone.find('.upload-file-input');
      var browseButton = dropzone.find('.browse-button');
      var dropzoneContent = dropzone.find('.dropzone-content');
      var filePreview = dropzone.find('.file-preview');
      var removeButton = filePreview.find('.remove-file');
      var clearCheckbox = container.find('input[type="checkbox"][id*="clear"]');
      
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
          self.displayFile(files[0]);
        }
      });
      
      // Remove file button
      removeButton.on('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        self.clearFile();
      });
      
      // Prevent default drag behaviors
      $(document).on('dragenter dragover', function(e) {
        e.preventDefault();
        e.stopPropagation();
      });
      
      // Drag and drop functionality
      dropzone.on('dragenter dragover', function(e) {
        e.preventDefault();
        e.stopPropagation();
        $(this).addClass('dragover');
      });
      
      dropzone.on('dragleave', function(e) {
        e.preventDefault();
        e.stopPropagation();
        $(this).removeClass('dragover');
      });
      
      dropzone.on('drop', function(e) {
        e.preventDefault();
        e.stopPropagation();
        $(this).removeClass('dragover');
        
        var dt = e.originalEvent.dataTransfer;
        if (dt && dt.files && dt.files.length > 0) {
          // Try to set files to input (may not work in all browsers)
          try {
            if (typeof DataTransfer !== 'undefined') {
              var dataTransfer = new DataTransfer();
              dataTransfer.items.add(dt.files[0]);
              fileInput[0].files = dataTransfer.files;
            }
          } catch(err) {
            // Fallback: just display the file info
            // DataTransfer not supported, using fallback
          }
          
          self.displayFile(dt.files[0]);
          // Trigger change event for validation
          fileInput.trigger('change');
        }
      });
    },
    
    displayFile: function(file) {
      var dropzoneContent = this.el.find('.dropzone-content');
      var filePreview = this.el.find('.file-preview');
      var fileName = filePreview.find('.file-name');
      var fileSize = filePreview.find('.file-size');
      var fileIcon = filePreview.find('.file-icon');
      
      // Update file name
      fileName.text(file.name);
      
      // Auto-fill name field if exists and is empty
      this.autoFillNameField(file.name);
      
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
      var clearCheckbox = this.el.find('input[type="checkbox"][id*="clear"]');
      if (clearCheckbox.length) {
        clearCheckbox.prop('checked', true);
      }
    },
    
    clearFile: function() {
      var dropzoneContent = this.el.find('.dropzone-content');
      var filePreview = this.el.find('.file-preview');
      var fileInput = this.el.find('.upload-file-input');
      
      // Clear file input
      fileInput.val('');
      
      // Clear auto-filled form fields
      this.clearAutoFilledFields();
      
      // Show dropzone content, hide preview
      dropzoneContent.show();
      filePreview.hide();
      
      // Uncheck clear checkbox if exists
      var clearCheckbox = this.el.find('input[type="checkbox"][id*="clear"]');
      if (clearCheckbox.length) {
        clearCheckbox.prop('checked', false);
      }
    },
    
    formatFileSize: function(bytes) {
      if (bytes === 0) return '0 Bytes';
      
      var k = 1024;
      var sizes = ['Bytes', 'KB', 'MB', 'GB'];
      var i = Math.floor(Math.log(bytes) / Math.log(k));
      
      var result = (bytes / Math.pow(k, i)).toFixed(2);
      return result + ' ' + sizes[i];
    },
    
    getFileIcon: function(fileName) {
      // Get extension from filename
      var parts = fileName.split('.');
      var ext = parts.length > 1 ? parts[parts.length - 1].toLowerCase() : '';
      
      // Icon mapping
      var iconMap = {
        // Documents
        'pdf': 'fa-file-pdf-o',
        'doc': 'fa-file-word-o',
        'docx': 'fa-file-word-o',
        'xls': 'fa-file-excel-o',
        'xlsx': 'fa-file-excel-o',
        'ppt': 'fa-file-powerpoint-o',
        'pptx': 'fa-file-powerpoint-o',
        'txt': 'fa-file-text-o',
        
        // Data files
        'csv': 'fa-file-text-o',
        'json': 'fa-file-code-o',
        'xml': 'fa-file-code-o',
        'rdf': 'fa-file-code-o',
        
        // Archives
        'zip': 'fa-file-archive-o',
        'rar': 'fa-file-archive-o',
        '7z': 'fa-file-archive-o',
        'tar': 'fa-file-archive-o',
        'gz': 'fa-file-archive-o',
        
        // Images
        'jpg': 'fa-file-image-o',
        'jpeg': 'fa-file-image-o',
        'png': 'fa-file-image-o',
        'gif': 'fa-file-image-o',
        'bmp': 'fa-file-image-o',
        'svg': 'fa-file-image-o',
        
        // GIS files
        'shp': 'fa-map-o',
        'kml': 'fa-map-o',
        'kmz': 'fa-map-o',
        'geojson': 'fa-map-o',
        'gpx': 'fa-map-o'
      };
      
      return iconMap[ext] || 'fa-file-o';
    },
    
    autoFillNameField: function(fileName) {
      // Extract name without extension
      var nameWithoutExtension = fileName.replace(/\.[^/.]+$/, '');
      
      // Clean name: replace underscores and hyphens with spaces, normalize whitespace
      var cleanName = nameWithoutExtension.replace(/[_-]/g, ' ').replace(/\s+/g, ' ').trim();
      
      // Find form fields to populate
      var form = this.el.closest('form');
      if (form.length) {
        // Priority order for name field detection
        var nameSelectors = [
          'input[name="name"]',
          'input[name="title"]', 
          '#field-name',
          '#field-title',
          'input[id*="name"]',
          'input[id*="title"]',
          'input[name*="name"]',
          'input[name*="title"]'
        ];
        
        var nameField = null;
        for (var i = 0; i < nameSelectors.length; i++) {
          nameField = form.find(nameSelectors[i]);
          if (nameField.length) {
            nameField = nameField.first();
            break;
          }
          nameField = null;
        }
        
        if (nameField && nameField.length) {
          nameField.val(cleanName);
          nameField.attr('data-auto-filled', 'true'); // Mark as auto-filled
          nameField.trigger('change');
          nameField.trigger('input');
          
          // Add visual feedback
          nameField.css('background-color', '#d4edda');
          setTimeout(function() {
            nameField.css('background-color', '');
          }, 2000);
          
          console.log('[schemingdcat-modern-upload] Auto-populated name field:', cleanName);
        }
      }
    },
    
    clearAutoFilledFields: function() {
      var form = this.el.closest('form');
      if (form.length) {
        // Clear all fields marked as auto-filled (inputs and textareas)
        form.find('input[data-auto-filled], textarea[data-auto-filled]').each(function() {
          $(this).val('').removeAttr('data-auto-filled').trigger('change');
        });
        
        console.log('[schemingdcat-modern-upload] Cleared auto-filled fields');
      }
    }
  };
});