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
      var urlInput = container.find('input[type="url"]');
      var clearCheckbox = container.find('input[type="checkbox"][id*="clear"]');
      
      // Tab switching functionality
      container.find('.nav-link').on('click', function(e) {
        e.preventDefault();
        var target = $(this).attr('href');
        
        // Update active states
        container.find('.nav-item').removeClass('active');
        $(this).parent().addClass('active');
        
        container.find('.tab-pane').removeClass('active in');
        $(target).addClass('active in');
        
        // Enable/disable URL input based on active tab
        if (target.indexOf('url-tab') !== -1) {
          urlInput.prop('disabled', false);
          fileInput.val(''); // Clear file input when switching to URL
        } else {
          urlInput.prop('disabled', true);
        }
      });
      
      // Browse button click
      browseButton.on('click', function(e) {
        e.preventDefault();
        fileInput.click();
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
        self.clearFile();
      });
      
      // Drag and drop functionality
      dropzone.on('dragover dragenter', function(e) {
        e.preventDefault();
        e.stopPropagation();
        $(this).addClass('dragover');
      });
      
      dropzone.on('dragleave dragend', function(e) {
        e.preventDefault();
        e.stopPropagation();
        $(this).removeClass('dragover');
      });
      
      dropzone.on('drop', function(e) {
        e.preventDefault();
        e.stopPropagation();
        $(this).removeClass('dragover');
        
        var files = e.originalEvent.dataTransfer.files;
        if (files && files.length > 0) {
          // Update the file input
          fileInput[0].files = files;
          self.displayFile(files[0]);
          
          // Trigger change event for other modules
          fileInput.trigger('change');
        }
      });
      
      // If there's a clear checkbox and it's checked on load, uncheck it
      if (clearCheckbox.length && clearCheckbox.is(':checked')) {
        clearCheckbox.prop('checked', false);
      }
    },
    
    displayFile: function(file) {
      var dropzoneContent = this.el.find('.dropzone-content');
      var filePreview = this.el.find('.file-preview');
      var fileName = filePreview.find('.file-name');
      var fileSize = filePreview.find('.file-size');
      var fileIcon = filePreview.find('.file-icon');
      
      // Update file name
      fileName.text(file.name);
      
      // Update file size
      var size = this.formatFileSize(file.size);
      fileSize.text(size);
      
      // Update icon based on file type
      var iconClass = this.getFileIcon(file.type, file.name);
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
      
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    getFileIcon: function(mimeType, fileName) {
      // Get extension from filename
      var ext = fileName.split('.').pop().toLowerCase();
      
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
    }
  };
});