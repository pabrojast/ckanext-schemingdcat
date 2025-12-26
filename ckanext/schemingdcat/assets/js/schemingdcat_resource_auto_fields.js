// ============================================================================
// SCHEMING DCAT RESOURCE AUTO FIELDS
// ============================================================================
// Auto-populate fields for DCAT resources in CKAN
// Included by upload_script.html (main) via standard JS includes
// ============================================================================

(function() {
    'use strict';
    
    // Prevent multiple initializations
    if (window._schemingdcatAutoFieldsInitialized) {
        console.log('[schemingdcat-resource-auto-fields] Already initialized, skipping');
        return;
    }
    window._schemingdcatAutoFieldsInitialized = true;

    // Function to initialize auto fields
    function initAutoFields() {
        // Check if already initialized on this form
        var form = document.querySelector('form.dataset-form, form.resource-form');
        if (!form || form.hasAttribute('data-auto-fields-initialized')) {
            console.log('[schemingdcat-resource-auto-fields] Form already initialized or not found');
            return;
        }
        form.setAttribute('data-auto-fields-initialized', 'true');

        // Auto-fill name field with filename (similar to CloudStorage functionality)
        function autoFillNameField(fileName, forceUpdate) {
          // Extract name without extension
          var nameWithoutExtension = fileName.replace(/\.[^/.]+$/, '');
          
          // Clean name: replace underscores and hyphens with spaces, normalize whitespace
          var cleanName = nameWithoutExtension.replace(/[_-]/g, ' ').replace(/\s+/g, ' ').trim();
          
          // Find form fields to populate
          var form = wrapper.closest('form');
          if (form) {
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
              nameField = form.querySelector(nameSelectors[i]);
              if (nameField) break;
            }
            
            // Update field if it's empty OR if we're forcing an update (new file upload)
            if (nameField && (!nameField.value.trim() || forceUpdate)) {
              nameField.value = cleanName;
              nameField.setAttribute('data-auto-filled', 'true'); // Mark as auto-filled
              nameField.dispatchEvent(new Event('change', { bubbles: true }));
              nameField.dispatchEvent(new Event('input', { bubbles: true }));
              
              // Add visual feedback
              nameField.style.backgroundColor = '#d4edda';
              setTimeout(function() {
                nameField.style.backgroundColor = '';
              }, 2000);
              
              console.log('[schemingdcat-upload] Auto-populated name field:', cleanName);
            }
          }
        }

        // Function to clear auto-filled fields when removing a file
        function clearAutoFilledFields() {
          var form = wrapper.closest('form');
          if (form) {
            // Clear name field if it was auto-filled
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
              nameField = form.querySelector(nameSelectors[i]);
              if (nameField) break;
            }
            
            if (nameField && nameField.hasAttribute('data-auto-filled')) {
              nameField.value = '';
              nameField.removeAttribute('data-auto-filled');
              nameField.dispatchEvent(new Event('change', { bubbles: true }));
              nameField.dispatchEvent(new Event('input', { bubbles: true }));
            }
            
            // Clear format field if it was auto-filled
            var formatFields = form.querySelectorAll('input[name$="format"], select[name$="format"]');
            formatFields.forEach(function(field) {
              if (field.hasAttribute('data-auto-filled')) {
                field.value = '';
                field.removeAttribute('data-auto-filled');
                field.dispatchEvent(new Event('change', { bubbles: true }));
              }
            });
            
            // Clear mimetype field if it was auto-filled
            var mimetypeFields = form.querySelectorAll('input[name$="mimetype"], select[name$="mimetype"]');
            mimetypeFields.forEach(function(field) {
              if (field.hasAttribute('data-auto-filled')) {
                field.value = '';
                field.removeAttribute('data-auto-filled');
                field.dispatchEvent(new Event('change', { bubbles: true }));
              }
            });
            
            // Clear encoding field if it was auto-filled
            var encodingFields = form.querySelectorAll('input[name$="encoding"], select[name$="encoding"]');
            encodingFields.forEach(function(field) {
              if (field.hasAttribute('data-auto-filled')) {
                field.value = '';
                field.removeAttribute('data-auto-filled');
                field.dispatchEvent(new Event('change', { bubbles: true }));
              }
            });
            
            // Clear description field if it was auto-filled
            var descriptionSelectors = [
              'textarea[name="description"]',
              'textarea[name*="description"]',
              '#field-description',
              'textarea[id*="description"]'
            ];
            
            var descriptionField = null;
            for (var i = 0; i < descriptionSelectors.length; i++) {
              descriptionField = form.querySelector(descriptionSelectors[i]);
              if (descriptionField) break;
            }
            
            if (descriptionField && descriptionField.hasAttribute('data-auto-filled')) {
              descriptionField.value = '';
              descriptionField.removeAttribute('data-auto-filled');
              descriptionField.dispatchEvent(new Event('change', { bubbles: true }));
              descriptionField.dispatchEvent(new Event('input', { bubbles: true }));
            }
            
            console.log('[schemingdcat-upload] Cleared auto-filled fields');
          }
        }

        // URL input change for format detection
        var urlInput = wrapper.querySelector('input[name="{{ field_url }}"]');
        if (urlInput) {
          urlInput.addEventListener('blur', function(e) {
            var url = e.target.value;
            if (url) {
              // Extract filename from URL for auto-fill name field
              var urlPath = url.split('?')[0].split('#')[0]; // Remove query params and fragments
              var fileName = urlPath.split('/').pop(); // Get last part of path
              if (fileName) {
                autoFillNameField(fileName);
              }
              
              // Extract extension from URL
              var urlParts = url.split('?')[0].split('.');
              if (urlParts.length > 1) {
                var ext = urlParts[urlParts.length - 1].toLowerCase();
                var extUpper = ext.toUpperCase();
                
                // Auto-fill format field
                var form = wrapper.closest('form') || document;
                var formatField = form.querySelector('input[name$="format"], select[name$="format"]');
                
                if (formatField && !formatField.value) {
                  // Format mapping
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
                    'PPT': 'PPT',
                    'PPTX': 'PPT',
                    'TXT': 'TXT',
                    'ZIP': 'ZIP',
                    'TAR': 'TAR',
                    'GZ': 'GZ',
                    'MP4': 'MP4',
                    'AVI': 'AVI',
                    'MOV': 'MOV',
                    'SHP': 'SHP',
                    'KML': 'KML',
                    'KMZ': 'KMZ',
                    'GML': 'GML',
                    'GPKG': 'GPKG',
                    'SLD': 'SLD'
                  };
                  
                  formatField.value = formatMap[extUpper] || extUpper;
                  // Trigger change event
                  var event = new Event('change', { bubbles: true });
                  formatField.dispatchEvent(event);
                }
                
                // Auto-fill mimetype field
                var mimetypeField = form.querySelector('input[name$="mimetype"], select[name$="mimetype"]');
                
                if (mimetypeField && !mimetypeField.value) {
                  getMimeTypeForExtension(ext, function(mimeType) {
                    if (mimeType) {
                      mimetypeField.value = mimeType;
                      // Trigger change event
                      var event = new Event('change', { bubbles: true });
                      mimetypeField.dispatchEvent(event);
                    }
                  });
                }
                
                // Auto-fill encoding field
                var encodingField = form.querySelector('input[name$="encoding"], select[name$="encoding"]');
                
                if (encodingField && !encodingField.value) {
                  var currentFormat = formatField ? formatField.value : '';
                  getCharsetForFormat(ext, currentFormat, function(charset) {
                    if (charset) {
                      encodingField.value = charset;
                      // Trigger change event
                      var event = new Event('change', { bubbles: true });
                      encodingField.dispatchEvent(event);
                    }
                  });
                }
              }
            }
          });
        }
    }

    // Initialize auto fields on document ready
    document.addEventListener('DOMContentLoaded', function() {
        initAutoFields();
    });
})();
