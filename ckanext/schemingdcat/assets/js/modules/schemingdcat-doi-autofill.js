/**
 * schemingdcat-doi-autofill.js
 * 
 * CKAN JavaScript module for DOI auto-fill functionality.
 * Fetches metadata from DOI providers (DataCite, CrossRef, Zenodo)
 * and populates form fields automatically.
 * 
 * @module schemingdcat-doi-autofill
 */

this.ckan.module('schemingdcat-doi-autofill', function($, _) {
  'use strict';

  // DOI validation regex
  var DOI_PATTERN = /^10\.\d{4,9}\/[-._;()/:A-Z0-9]+$/i;

  // Common DOI URL prefixes to clean
  var DOI_PREFIXES = [
    'https://doi.org/',
    'http://doi.org/',
    'https://dx.doi.org/',
    'http://dx.doi.org/',
    'doi.org/',
    'dx.doi.org/',
    'doi:',
    'DOI:'
  ];

  return {
    /**
     * Module options with defaults
     */
    options: {
      fieldId: null,
      fieldName: null,
      fieldMapping: {},
      debounceDelay: 500,
      apiEndpoint: '/api/doi/resolve',
      validateEndpoint: '/api/doi/validate',
      defaultMode: 'doi'
    },

    /**
     * Initialize the module
     */
    initialize: function() {
      $.proxyAll(this, /_on/);

      this.fieldId = this.options.fieldId;
      this.fieldName = this.options.fieldName;
      this.fieldMapping = this.options.fieldMapping || {};
      this.resolvedData = null;
      this.currentMode = null;
      this.pendingRequest = null;

      // Cache DOM elements
      this.$input = this.el.find('.doi-input');
      this.$fetchBtn = this.el.find('.doi-fetch-btn');
      this.$loading = this.el.find('.doi-loading');
      this.$error = this.el.find('.doi-error');
      this.$errorMessage = this.$error.find('.error-message');
      this.$preview = this.el.find('.doi-preview-panel');
      this.$validFeedback = this.el.find('.doi-valid');
      this.$invalidFeedback = this.el.find('.doi-invalid');
      this.$validationFeedback = this.el.find('.doi-validation-feedback');
      this.$modeButtons = this.el.find('.doi-mode-btn');
      this.$fetchSection = this.el.find('.doi-fetch-section');
      this.$manualSection = this.el.find('.doi-manual-section');

      // Bind events
      this.$input.on('input', this._onInputChange);
      this.$input.on('keypress', this._onInputKeypress);
      this.$fetchBtn.on('click', this._onFetchClick);
      this.$modeButtons.on('click', this._onModeToggle);
      this.el.find('.doi-apply-btn').on('click', this._onApplyClick);
      this.el.find('.doi-cancel-btn').on('click', this._onCancelClick);
      this.el.find('.doi-error-close').on('click', this._onErrorClose);

      // Set up debounced validation
      this._debouncedValidate = this._debounce(this._validateDoi.bind(this), this.options.debounceDelay);

      // Initialize mode (defaults to DOI unless configured otherwise)
      var initialMode = (this.options.defaultMode || 'doi').toString();
      if (initialMode !== 'manual' && initialMode !== 'doi') {
        initialMode = 'doi';
      }
      if (this.$input.val().trim()) {
        initialMode = 'doi';
      }
      this._setMode(initialMode);

      console.log('[DOI Autofill] Module initialized for field:', this.fieldName);
    },

    /**
     * Clean DOI string from URL prefixes
     * @param {string} doi - The DOI to clean
     * @returns {string} Cleaned DOI
     */
    _cleanDoi: function(doi) {
      if (!doi) return '';
      
      doi = doi.trim();
      
      for (var i = 0; i < DOI_PREFIXES.length; i++) {
        var prefix = DOI_PREFIXES[i];
        if (doi.toLowerCase().indexOf(prefix.toLowerCase()) === 0) {
          doi = doi.substring(prefix.length);
          break;
        }
      }
      
      return doi.trim();
    },

    /**
     * Validate DOI format locally
     * @param {string} doi - The DOI to validate
     * @returns {boolean} True if valid format
     */
    _isValidDoiFormat: function(doi) {
      return DOI_PATTERN.test(this._cleanDoi(doi));
    },

    /**
     * Handle input changes with debounced validation
     */
    _onInputChange: function() {
      var value = this.$input.val().trim();
      
      if (!value) {
        this._hideValidation();
        return;
      }
      
      this._debouncedValidate(value);
    },

    /**
     * Handle Enter key press
     */
    _onInputKeypress: function(e) {
      if (e.which === 13) {
        e.preventDefault();
        this._onFetchClick();
      }
    },

    /**
     * Handle mode toggle clicks (DOI vs manual)
     */
    _onModeToggle: function(e) {
      e.preventDefault();
      var mode = $(e.currentTarget).data('doiMode');
      this._setMode(mode);
    },

    /**
     * Set active mode for the UI
     * @param {string} mode - 'doi' or 'manual'
     */
    _setMode: function(mode) {
      if (mode !== 'manual' && mode !== 'doi') {
        mode = 'doi';
      }

      this.currentMode = mode;
      var isManual = mode === 'manual';

      if (this.$fetchSection.length) {
        this.$fetchSection.toggle(!isManual);
      }
      if (this.$manualSection.length) {
        this.$manualSection.toggle(isManual);
      }

      if (this.$modeButtons.length) {
        this.$modeButtons.removeClass('is-active').attr('aria-pressed', 'false');
        this.$modeButtons
          .filter('[data-doi-mode="' + mode + '"]')
          .addClass('is-active')
          .attr('aria-pressed', 'true');
      }

      if (isManual) {
        this._hideValidation();
        this._hideError();
        this._hidePreview();
        this._hideLoading();
        this.el.find('.doi-success').remove();

        if (this.pendingRequest && this.pendingRequest.abort) {
          this.pendingRequest.abort();
          this.pendingRequest = null;
        }
      }

      this.$input.prop('disabled', isManual);
      this.$fetchBtn.prop('disabled', isManual);
    },

    /**
     * Validate DOI and show feedback
     * @param {string} value - The DOI value to validate
     */
    _validateDoi: function(value) {
      var isValid = this._isValidDoiFormat(value);
      
      this.$validationFeedback.show();
      
      if (isValid) {
        this.$validFeedback.show();
        this.$invalidFeedback.hide();
      } else {
        this.$validFeedback.hide();
        this.$invalidFeedback.show();
      }
    },

    /**
     * Hide validation feedback
     */
    _hideValidation: function() {
      this.$validationFeedback.hide();
      this.$validFeedback.hide();
      this.$invalidFeedback.hide();
    },

    /**
     * Handle fetch button click
     */
    _onFetchClick: function() {
      if (this.currentMode === 'manual') {
        return;
      }

      var doi = this.$input.val().trim();
      
      if (!doi) {
        this._showError(this._('Please enter a DOI'));
        return;
      }
      
      if (!this._isValidDoiFormat(doi)) {
        this._showError(this._('Invalid DOI format. Expected format: 10.xxxx/xxxxx'));
        return;
      }
      
      this._fetchDoiMetadata(doi);
    },

    /**
     * Fetch metadata from DOI resolver API
     * @param {string} doi - The DOI to resolve
     */
    _fetchDoiMetadata: function(doi) {
      var self = this;
      
      console.log('[DOI Autofill] Fetching metadata for DOI:', doi);
      console.log('[DOI Autofill] API endpoint:', this.options.apiEndpoint);
      
      this._showLoading();
      this._hideError();
      this._hidePreview();
      
      this.pendingRequest = $.ajax({
        url: this.options.apiEndpoint,
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ doi: doi }),
        timeout: 30000
      })
      .done(function(response) {
        if (self.currentMode !== 'doi') {
          return;
        }

        console.log('[DOI Autofill] Response received:', response);
        self._hideLoading();
        
        if (response.success && response.data) {
          self.resolvedData = response.data;
          self._showPreview(response.data);
        } else {
          self._showError(response.error || self._('Could not resolve DOI'));
        }
      })
      .fail(function(xhr, status, error) {
        if (self.currentMode !== 'doi') {
          return;
        }

        console.error('[DOI Autofill] Request failed:', status, error);
        console.error('[DOI Autofill] XHR response:', xhr.responseText);
        self._hideLoading();
        
        var errorMessage = self._('Error fetching DOI metadata');
        
        if (xhr.responseJSON && xhr.responseJSON.error) {
          errorMessage = xhr.responseJSON.error;
        } else if (status === 'timeout') {
          errorMessage = self._('Request timed out. Please try again.');
        } else if (xhr.status === 404) {
          errorMessage = self._('DOI API endpoint not found. Please contact administrator.');
        } else if (xhr.status === 0) {
          errorMessage = self._('Network error. Please check your connection.');
        }
        
        self._showError(errorMessage);
      })
      .always(function() {
        self.pendingRequest = null;
      });
    },

    /**
     * Show loading state
     */
    _showLoading: function() {
      this.$loading.show();
      this.$fetchBtn.prop('disabled', true).addClass('loading');
      this.$fetchBtn.find('.fa').removeClass('fa-search').addClass('fa-spinner');
    },

    /**
     * Hide loading state
     */
    _hideLoading: function() {
      this.$loading.hide();
      this.$fetchBtn.prop('disabled', false).removeClass('loading');
      this.$fetchBtn.find('.fa').removeClass('fa-spinner').addClass('fa-search');
    },

    /**
     * Show error message
     * @param {string} message - Error message to display
     */
    _showError: function(message) {
      this.$errorMessage.text(message);
      this.$error.show();
    },

    /**
     * Hide error message
     */
    _hideError: function() {
      this.$error.hide();
    },

    /**
     * Handle error close button
     */
    _onErrorClose: function() {
      this._hideError();
    },

    /**
     * Show metadata preview
     * @param {Object} data - Resolved DOI metadata
     */
    _showPreview: function(data) {
      // Set source badge
      this.$preview.find('.doi-source').text(data.source || 'DOI');
      
      // Populate preview fields
      this.$preview.find('.preview-title').text(data.title || '-');
      this.$preview.find('.preview-year').text(data.publication_year || '-');
      this.$preview.find('.preview-publisher').text(data.publisher || '-');
      this.$preview.find('.preview-type').text(this._formatDocumentType(data.document_type) || '-');
      
      // Format authors
      var authorsText = this._formatAuthors(data.authors);
      this.$preview.find('.preview-authors').text(authorsText || '-');
      
      // Format abstract (truncate if too long)
      var abstract = data.abstract || '';
      if (abstract.length > 300) {
        abstract = abstract.substring(0, 300) + '...';
      }
      this.$preview.find('.preview-abstract').text(abstract || '-');
      
      // Format keywords
      var $keywords = this.$preview.find('.preview-keywords');
      $keywords.empty();
      
      if (data.keywords && data.keywords.length > 0) {
        data.keywords.slice(0, 10).forEach(function(keyword) {
          $keywords.append(
            $('<span class="keyword-tag">').text(keyword)
          );
        });
        
        if (data.keywords.length > 10) {
          $keywords.append(
            $('<span class="keyword-more">').text('+' + (data.keywords.length - 10) + ' more')
          );
        }
      } else {
        $keywords.text('-');
      }
      
      this.$preview.show();
    },

    /**
     * Hide preview panel
     */
    _hidePreview: function() {
      this.$preview.hide();
      this.resolvedData = null;
    },

    /**
     * Format authors list for display
     * @param {Array} authors - Array of author objects
     * @returns {string} Formatted author string
     */
    _formatAuthors: function(authors) {
      if (!authors || authors.length === 0) return '';
      
      return authors.map(function(author) {
        if (author.name) return author.name;
        
        var parts = [];
        if (author.family_name) parts.push(author.family_name);
        if (author.given_name) parts.push(author.given_name);
        
        return parts.join(', ');
      }).join('; ');
    },

    /**
     * Format document type for display
     * @param {string} type - Document type code
     * @returns {string} Human-readable type
     */
    _formatDocumentType: function(type) {
      var typeMap = {
        'scientific_paper': this._('Scientific Paper'),
        'technical_report': this._('Technical Report'),
        'book': this._('Book'),
        'book_chapter': this._('Book Chapter'),
        'conference_paper': this._('Conference Paper'),
        'thesis': this._('Thesis/Dissertation'),
        'preprint': this._('Preprint'),
        'dataset_documentation': this._('Dataset Documentation'),
        'software_documentation': this._('Software Documentation'),
        'policy_brief': this._('Policy Brief'),
        'poster': this._('Poster'),
        'presentation': this._('Presentation'),
        'other': this._('Other')
      };
      
      return typeMap[type] || type;
    },

    /**
     * Handle apply button click
     */
    _onApplyClick: function() {
      if (!this.resolvedData) {
        console.warn('[DOI Autofill] No resolved data to apply');
        return;
      }
      
      var overwrite = this.el.find('.doi-overwrite-option').is(':checked');
      this._applyMetadata(this.resolvedData, overwrite);
      
      // Store files info for resource form
      if (this.resolvedData.files && this.resolvedData.files.length > 0) {
        this._storeFilesForResourceForm(this.resolvedData);
      }
      
      this._hidePreview();
      
      // Show success message
      this._showSuccess(this._('Metadata applied successfully'));
    },

    /**
     * Store DOI files information for the resource form
     * @param {Object} data - Resolved DOI metadata with files
     */
    _storeFilesForResourceForm: function(data) {
      try {
        var resourceData = {
          doi: data.doi,
          title: data.title,
          source: data.source,
          files: data.files || [],
          url: data.url || '',
          timestamp: new Date().toISOString()
        };
        
        // Store in sessionStorage for the resource form to pick up
        sessionStorage.setItem('doi_resource_files', JSON.stringify(resourceData));
        console.log('[DOI Autofill] Stored', resourceData.files.length, 'files for resource form');
      } catch (e) {
        console.warn('[DOI Autofill] Could not store files in sessionStorage:', e);
      }
    },

    /**
     * Handle cancel button click
     */
    _onCancelClick: function() {
      this._hidePreview();
    },

    /**
     * Apply resolved metadata to form fields
     * @param {Object} data - Resolved DOI metadata
     * @param {boolean} overwrite - Whether to overwrite existing values
     */
    _applyMetadata: function(data, overwrite) {
      var self = this;
      
      // Default field mapping
      var defaultMapping = {
        'title': ['title_translated', 'title'],
        'abstract': ['notes_translated', 'notes', 'description'],
        'publication_year': ['publication_year', 'issued'],
        'publisher': ['publisher', 'publisher_name'],
        'document_type': ['document_type', 'dcat_type'],
        'keywords': ['tag_string', 'tags', 'keywords'],
        'license': ['license_id', 'license'],
        // Prefer structured authors; fall back to plain fields if needed
        'authors': ['authors_json', 'authors', 'author']
      };
      
      // Merge with custom mapping
      var mapping = $.extend({}, defaultMapping, this.fieldMapping);
      
      // Apply each field
      Object.keys(mapping).forEach(function(sourceField) {
        var targetFields = mapping[sourceField];
        if (!Array.isArray(targetFields)) {
          targetFields = [targetFields];
        }
        
        var value = data[sourceField];
        if (value === undefined || value === null || value === '') return;
        
        targetFields.forEach(function(targetField) {
          self._setFieldValue(targetField, value, sourceField, overwrite);
        });
      });
      
      // Auto-generate URL slug (name field) from title
      if (data.title) {
        this._generateSlugFromTitle(data.title, overwrite);
      }
      
      // Auto-generate identifier from DOI
      if (data.doi) {
        this._setIdentifierFromDoi(data.doi, overwrite, data.title);
        this._setCustomDoi(data.doi, overwrite);
        this._setCustomCitation(data, overwrite);
      }
      
      console.log('[DOI Autofill] Metadata applied to form');
    },

    /**
     * Set the identifier field based on DOI
     * Generates a UUID-like identifier from the DOI and sets alternate_identifier
     * @param {string} doi - The DOI string
     * @param {boolean} overwrite - Whether to overwrite existing values
     */
     _setIdentifierFromDoi: function(doi, overwrite, title) {
      var self = this;
      var isDocumentsForm = this.fieldName === 'document_doi';
      
      // Set the main identifier field (UUID generated from DOI)
      var $identifierField = $('[name="identifier"]');
      
      if ($identifierField.length > 0) {
        // Check if field already has value
        if (overwrite || !$identifierField.val() || $identifierField.val().trim() === '') {
          // For documents we want to keep a human friendly identifier (paper title)
          // Limit to 100 characters to respect CKAN name field constraints
          var identifier = (isDocumentsForm && title ? title : this._generateUuidFromDoi(doi));
          if (identifier && identifier.length > 100) {
            identifier = identifier.substring(0, 100).trim();
          }
          $identifierField.val(identifier).trigger('change').trigger('input');
          console.log('[DOI Autofill] Generated identifier:', identifier);
        } else {
          console.log('[DOI Autofill] Identifier field already has value, skipping');
        }
      } else {
        console.log('[DOI Autofill] Identifier field not found');
      }
      
      // Also set the alternate_identifier field with the DOI URL
      var doiUrl = 'https://doi.org/' + doi;
      var $alternateIdField = $('[name="alternate_identifier"]');
      
      if ($alternateIdField.length > 0) {
        if (overwrite || !$alternateIdField.val() || $alternateIdField.val().trim() === '') {
          $alternateIdField.val(doiUrl).trigger('change');
          console.log('[DOI Autofill] Set alternate_identifier:', doiUrl);
        }
      }
    },

    /**
     * Fill a custom DOI field (if present) with a DOI URL so it can be stored or edited
     * @param {string} doi - The DOI string
     * @param {boolean} overwrite - Whether to overwrite existing values
     */
    _setCustomDoi: function(doi, overwrite) {
      var $customDoiField = $('[name="custom_doi"]');
      if ($customDoiField.length === 0) {
        return;
      }

      var currentVal = ($customDoiField.val() || '').trim();
      if (!overwrite && currentVal) {
        console.log('[DOI Autofill] Custom DOI already set, skipping');
        return;
      }

      var cleaned = this._cleanDoi(doi);
      var doiUrl = cleaned;

      if (!/^https?:\/\//i.test(cleaned)) {
        doiUrl = 'https://doi.org/' + cleaned;
      }

      $customDoiField.val(doiUrl).trigger('change');
      console.log('[DOI Autofill] Set custom DOI:', doiUrl);
    },

    /**
     * Build and set a citation using DOI metadata (authors, year, title, publisher, DOI)
     * Targets the dedicated citation field when present, otherwise falls back to custom_citation
     * @param {Object} data - DOI metadata
     * @param {boolean} overwrite - Whether to overwrite existing values
     */
    _setCustomCitation: function(data, overwrite) {
      var $autoCitationField = $('[name="citation"]');
      var $customCitationField = $('[name="custom_citation"]');

      var $targetField = $autoCitationField.length ? $autoCitationField : $customCitationField;
      if ($targetField.length === 0) {
        return;
      }

      var currentVal = ($targetField.val() || '').trim();
      if (!overwrite && currentVal) {
        console.log('[DOI Autofill] Citation already set, skipping');
        return;
      }

      var authors = [];
      if (Array.isArray(data.authors)) {
        authors = data.authors.map(function(author) {
          if (author.name) return author.name;
          var parts = [];
          if (author.family_name) parts.push(author.family_name);
          if (author.given_name) parts.push(author.given_name);
          return parts.join(', ');
        }).filter(Boolean);
      }

      var year = data.publication_year || '';
      var title = data.title || '';
      var publisher = data.publisher || data.publisher_name || '';
      var doiUrl = data.doi ? ('https://doi.org/' + data.doi) : '';

      var pieces = [];
      if (authors.length) {
        pieces.push(authors.join('; '));
      }
      if (year) {
        pieces.push('(' + year + ').');
      }
      if (title) {
        pieces.push(title + '.');
      }
      pieces.push('[Document].');
      if (publisher) {
        pieces.push(publisher + '.');
      }
      if (doiUrl) {
        pieces.push(doiUrl);
      }

      var citation = pieces.join(' ').replace(/\s+/g, ' ').trim();
      if (citation) {
        $targetField.val(citation).trigger('change');
        console.log('[DOI Autofill] Set citation:', citation);
      }
    },

    /**
     * Generate a UUID-like string from a DOI
     * Uses a simple hash function to create a deterministic identifier
     * @param {string} doi - The DOI string
     * @returns {string} UUID-like identifier
     */
    _generateUuidFromDoi: function(doi) {
      // Simple hash function to generate consistent hex string from DOI
      var hash = 0;
      var str = 'doi:' + doi;
      for (var i = 0; i < str.length; i++) {
        var char = str.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash; // Convert to 32bit integer
      }
      
      // Convert hash to hex and pad
      var hex1 = Math.abs(hash).toString(16).padStart(8, '0').substring(0, 8);
      
      // Generate additional hex segments from DOI characters
      var hex2 = '';
      var hex3 = '';
      var hex4 = '';
      var hex5 = '';
      
      for (var j = 0; j < doi.length && hex2.length < 4; j++) {
        hex2 += doi.charCodeAt(j).toString(16);
      }
      hex2 = hex2.substring(0, 4).padStart(4, '0');
      
      for (var k = doi.length - 1; k >= 0 && hex3.length < 4; k--) {
        hex3 += doi.charCodeAt(k).toString(16);
      }
      hex3 = hex3.substring(0, 4).padStart(4, '0');
      
      // Use fixed segments for UUID v4 format compliance
      hex4 = '4' + hex2.substring(1, 4); // Version 4
      hex5 = (8 + Math.floor(Math.random() * 4)).toString(16) + hex3.substring(1, 4) + hex1.substring(0, 8);
      
      // Format as UUID: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
      return hex1 + '-' + hex2 + '-' + hex4 + '-' + hex5.substring(0, 4) + '-' + hex5.substring(4, 16).padEnd(12, '0');
    },

    /**
     * Generate URL slug from title and set the name field
     * @param {string} title - The title to slugify
     * @param {boolean} overwrite - Whether to overwrite existing values
     */
    _generateSlugFromTitle: function(title, overwrite) {
      var $nameField = $('[name="name"]');
      
      if ($nameField.length === 0) {
        console.log('[DOI Autofill] Name field not found');
        return;
      }
      
      // Check if field already has value
      if (!overwrite && $nameField.val() && $nameField.val().trim() !== '') {
        console.log('[DOI Autofill] Name field already has value, skipping');
        return;
      }
      
      // Generate slug from title
      var slug = this._slugify(title);
      
      // Limit slug length (CKAN has a max of 100 characters for name)
      if (slug.length > 100) {
        slug = slug.substring(0, 100);
        // Don't end with a hyphen
        slug = slug.replace(/-+$/, '');
      }
      
      $nameField.val(slug).trigger('change');
      console.log('[DOI Autofill] Generated slug:', slug);
      
      // Also trigger the slug preview module if it exists
      $nameField.trigger('input');
    },

    /**
     * Convert a string to a URL-safe slug
     * @param {string} text - Text to slugify
     * @returns {string} URL-safe slug
     */
    _slugify: function(text) {
      if (!text) return '';
      
      return text
        .toString()
        .toLowerCase()
        .trim()
        // Replace accented characters with non-accented equivalents
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        // Replace spaces and underscores with hyphens
        .replace(/[\s_]+/g, '-')
        // Remove invalid characters (keep only alphanumeric and hyphens)
        .replace(/[^a-z0-9\-]/g, '')
        // Replace multiple hyphens with single hyphen
        .replace(/-+/g, '-')
        // Remove leading/trailing hyphens
        .replace(/^-+|-+$/g, '');
    },

    /**
     * Set a form field value
     * @param {string} fieldName - Target field name
     * @param {*} value - Value to set
     * @param {string} sourceField - Source field name (for special handling)
     * @param {boolean} overwrite - Whether to overwrite existing values
     */
    _setFieldValue: function(fieldName, value, sourceField, overwrite) {
      if (sourceField === 'authors') {
        // Authors are repeating subfields and may not have a direct input
        this._setAuthorsValue(fieldName, value, overwrite);
        return;
      }

      var $field = $('[name="' + fieldName + '"]');
      
      if ($field.length === 0) {
        // Try with translated suffix for fluent fields
        $field = $('[name="' + fieldName + '-en"]');
        
        if ($field.length === 0) {
          console.log('[DOI Autofill] Field not found:', fieldName);
          return;
        }
      }
      
      // Check if field already has value
      if (!overwrite && $field.val() && $field.val().trim() !== '') {
        console.log('[DOI Autofill] Skipping field with existing value:', fieldName);
        return;
      }
      
      // Handle different field types
      if (sourceField === 'title' || sourceField === 'abstract') {
        // For fluent text fields, we may need to set multiple language inputs
        this._setFluentFieldValue(fieldName, value);
      } else if (sourceField === 'keywords') {
        // Keywords need special handling
        this._setKeywordsValue(fieldName, value);
      } else {
        // Simple value
        $field.val(value).trigger('change');
      }
      
      console.log('[DOI Autofill] Set field', fieldName, '=', value);
    },

    /**
     * Set value for fluent (multilingual) text fields
     * @param {string} fieldName - Base field name
     * @param {*} value - Value (string or object with translations)
     */
    _setFluentFieldValue: function(fieldName, value) {
      if (typeof value === 'string') {
        // Set English field if available
        var $enField = $('[name="' + fieldName + '-en"]');
        if ($enField.length > 0) {
          $enField.val(value).trigger('change').trigger('input');
        }
        
        // Also try the base field
        var $baseField = $('[name="' + fieldName + '"]');
        if ($baseField.length > 0 && $baseField.attr('type') !== 'hidden') {
          $baseField.val(value).trigger('change').trigger('input');
        }
      } else if (typeof value === 'object') {
        // Value has translations
        Object.keys(value).forEach(function(lang) {
          var $langField = $('[name="' + fieldName + '-' + lang + '"]');
          if ($langField.length > 0) {
            $langField.val(value[lang]).trigger('change');
          }
        });
      }
    },

    /**
     * Set keywords/tags value
     * @param {string} fieldName - Field name
     * @param {Array} keywords - Array of keywords
     */
    _setKeywordsValue: function(fieldName, keywords) {
      if (!Array.isArray(keywords)) return;
      
      var $field = $('[name="' + fieldName + '"]');
      if ($field.length === 0) return;
      
      // Join keywords as comma-separated string
      var value = keywords.join(', ');
      $field.val(value).trigger('change');
    },

    /**
     * Set authors value
     * @param {string} fieldName - Field name
     * @param {Array} authors - Array of author objects
     */
    _setAuthorsValue: function(fieldName, authors, overwrite) {
      if (!Array.isArray(authors) || authors.length === 0) return;
      
      var isPlainAuthorField = fieldName === 'authors' || fieldName === 'author';
      var targetsStructuredField = fieldName === 'authors_json';
      var $field = $('[name="' + fieldName + '"]');

      // Always try to populate structured authors first
      var structuredFilled = this._setAuthorsRepeatingSubfields(authors, overwrite);
      
      // If structured authors were populated, avoid filling the comma-separated field
      if (structuredFilled && (isPlainAuthorField || targetsStructuredField)) {
        return;
      }
      
      if ($field.length === 0) return;

      if (isPlainAuthorField) {
        var currentVal = ($field.val() || '').trim();
        if (!overwrite && currentVal) {
          console.log('[DOI Autofill] Skipping authors field with existing value:', fieldName);
          return;
        }
      }
      
      // Format authors as string
      var value = authors.map(function(author) {
        if (author.name) return author.name;
        var parts = [];
        if (author.family_name) parts.push(author.family_name);
        if (author.given_name) parts.push(author.given_name);
        return parts.join(', ');
      }).join('; ');
      
      $field.val(value).trigger('change');
    },

    /**
     * Populate authors_json repeating subfields with DOI author data
     * @param {Array} authors - Array of author objects from DOI
     */
    _setAuthorsRepeatingSubfields: function(authors, overwrite) {
      if (!Array.isArray(authors) || authors.length === 0) return false;
      
      var self = this;
      
      // Try multiple field names that could be used for structured authors
      var fieldNames = ['authors_json', 'authors'];
      var $container = $();
      var fieldName = null;
      
      for (var i = 0; i < fieldNames.length; i++) {
        var fname = fieldNames[i];

        $container = this._findRepeatingSubfieldsContainer(fname);
        if ($container.length > 0) {
          fieldName = fname;
          break;
        }
      }
      
      if (!$container || $container.length === 0) {
        console.log('[DOI Autofill] Structured authors container not found');
        return false;
      }
      
      console.log('[DOI Autofill] Found authors container for field:', fieldName);

      if (!overwrite && this._hasRepeatingSubfieldValues($container, fieldName)) {
        console.log('[DOI Autofill] Structured authors already present, skipping');
        return true;
      }
      
      // Find add button for the repeating subfields
      var $addButton = $container.find(
        '[data-module="scheming-repeating-subfields-add"], ' +
        '.scheming-repeating-add, ' +
        '.scheming-add-subfield, ' +
        '.btn-repeating-add, ' +
        '[name="repeating-add"], ' +
        'button:contains("Add"), ' +
        'a:contains("Add")'
      ).first();
      
      // Get existing subfield rows
      var $existingRows = $container.find(
        '.scheming-repeating-subfields-row, ' +
        '.scheming-subfield-row, ' +
        '.scheming-subfield-group, ' +
        '[class*="subfield-row"]'
      ).filter(function() {
        var $row = $(this);
        if ($row.closest('[name="repeating-template"]').length > 0) {
          return false;
        }
        var rowField = $row.data('field');
        if (rowField) {
          return rowField === fieldName;
        }
        return $row.find('[name^="' + fieldName + '__"], [name^="' + fieldName + '-"]').length > 0;
      });
      var existingCount = $existingRows.length;
      
      console.log('[DOI Autofill] Existing author rows:', existingCount, 'Authors to add:', authors.length);
      
      // Process each author from DOI
      authors.forEach(function(author, index) {
        var authorName = author.name || '';
        if (!authorName && (author.family_name || author.given_name)) {
          var parts = [];
          if (author.family_name) parts.push(author.family_name);
          if (author.given_name) parts.push(author.given_name);
          authorName = parts.join(', ');
        }
        
        var orcid = author.orcid || '';
        // Clean ORCID - remove URL prefix if present
        if (orcid && orcid.indexOf('http') === 0) {
          orcid = orcid.replace(/^https?:\/\/orcid\.org\//, '');
        }
        
        var affiliation = author.affiliation || '';
        
        // Check if we need to add a new row
        if (index >= existingCount) {
          // Click add button to create new row
          if ($addButton.length > 0) {
            $addButton.trigger('click');
            console.log('[DOI Autofill] Clicked add button for author', index);
          }
        }
        
        // Wait a moment for the DOM to update, then fill the fields
        setTimeout(function() {
          // Find input fields for this author by index
          var $nameInput = self._findRepeatingSubfieldInput(fieldName, index, 'name');
          var $orcidInput = self._findRepeatingSubfieldInput(fieldName, index, 'orcid');
          var $affiliationInput = self._findRepeatingSubfieldInput(fieldName, index, 'affiliation');
          
          if ($nameInput.length > 0 && authorName) {
            $nameInput.val(authorName).trigger('change').trigger('input');
            console.log('[DOI Autofill] Set author name:', authorName);
          }
          if ($orcidInput.length > 0 && orcid) {
            $orcidInput.val(orcid).trigger('change').trigger('input');
            console.log('[DOI Autofill] Set author ORCID:', orcid);
          }
          if ($affiliationInput.length > 0 && affiliation) {
            $affiliationInput.val(affiliation).trigger('change').trigger('input');
            console.log('[DOI Autofill] Set author affiliation:', affiliation);
          }
          
          console.log('[DOI Autofill] Processed author', index, ':', authorName);
        }, 150 * (index + 1));
      });
      
      return true;
    },
    
    /**
     * Find a repeating subfield input by field name, row index, and subfield name
     * @param {string} fieldName - Base field name (e.g., 'authors_json', 'authors')
     * @param {number} rowIndex - Row index
     * @param {string} subfieldName - Subfield name (e.g., 'name', 'orcid')
     * @returns {jQuery} The input element
     */
    _findRepeatingSubfieldInput: function(fieldName, rowIndex, subfieldName) {
      var $input;
      
      // Pattern 1: fieldname__index__subfield (numeric index)
      $input = $('[name="' + fieldName + '__' + rowIndex + '__' + subfieldName + '"]');
      if ($input.length > 0) {
        console.log('[DOI Autofill] Found input with numeric index pattern');
        return $input;
      }

      // Pattern 1b: fieldname-index-subfield (scheming repeating subfields)
      $input = $('[name="' + fieldName + '-' + rowIndex + '-' + subfieldName + '"]');
      if ($input.length > 0) {
        console.log('[DOI Autofill] Found input with hyphen index pattern');
        return $input;
      }
      
      // Pattern 2: Find by author-group container (used by schemingdcat)
      var $authorGroup = $('.author-group').first();
      if ($authorGroup.length > 0) {
        var $rows = $authorGroup.find('.scheming-repeating-subfields-row, .scheming-subfield-row, .scheming-subfield-group, [class*="subfield"]').filter(function() {
          if ($(this).closest('[name="repeating-template"]').length > 0) return false;
          return $(this).find('[name^="' + fieldName + '__"], [name^="' + fieldName + '-"]').length > 0;
        });
        if ($rows.length > rowIndex) {
          $input = $rows.eq(rowIndex).find('[name$="__' + subfieldName + '"], [name$="-' + subfieldName + '"]');
          if ($input.length > 0) {
            console.log('[DOI Autofill] Found input in author-group row');
            return $input;
          }
        }
      }
      
      // Pattern 3: Find by scheming-repeating-subfields-group with data-field-name
      var $container = $('.scheming-repeating-subfields-group[data-field-name="' + fieldName + '"]');
      if ($container.length > 0) {
        var $rows = $container.find('.scheming-repeating-subfields-row, .scheming-subfield-row, .scheming-subfield-group')
          .filter(function() {
            return $(this).closest('[name="repeating-template"]').length === 0;
          });
        if ($rows.length > rowIndex) {
          $input = $rows.eq(rowIndex).find('[name$="__' + subfieldName + '"], [name$="-' + subfieldName + '"]');
          if ($input.length > 0) {
            console.log('[DOI Autofill] Found input in scheming container row');
            return $input;
          }
          
          // Try with data-subfield attribute
          $input = $rows.eq(rowIndex).find('[data-subfield="' + subfieldName + '"]');
          if ($input.length > 0) return $input;
        }
      }
      
      // Pattern 4: Find all matching inputs and pick by index (handles UUID-based naming)
      $input = $('[name^="' + fieldName + '__"][name$="__' + subfieldName + '"], ' +
                 '[name^="' + fieldName + '-"][name$="-' + subfieldName + '"]')
        .filter(function() {
          return $(this).closest('[name="repeating-template"]').length === 0;
        });
      if ($input.length > rowIndex) {
        console.log('[DOI Autofill] Found input by pattern matching, total:', $input.length);
        return $input.eq(rowIndex);
      }
      
      // Pattern 5: Try with just the subfield name suffix in any container
      var $allContainers = $('.author-group, .scheming-repeating-subfields-group, fieldset[data-module="scheming-repeating-subfields"], [class*="authors"]');
      $allContainers.each(function() {
        var $cont = $(this);
        var $allSubfieldInputs = $cont.find('[name$="__' + subfieldName + '"], [name$="-' + subfieldName + '"]')
          .filter(function() {
            return $(this).closest('[name="repeating-template"]').length === 0;
          });
        if ($allSubfieldInputs.length > rowIndex) {
          $input = $allSubfieldInputs.eq(rowIndex);
          return false; // break loop
        }
      });
      
      if ($input && $input.length > 0) {
        console.log('[DOI Autofill] Found input in container with subfield suffix');
        return $input;
      }
      
      console.log('[DOI Autofill] Could not find input for', fieldName, rowIndex, subfieldName);
      return $();
    },

    /**
     * Find the repeating subfields container for a field name
     * @param {string} fieldName - Base field name
     * @returns {jQuery} Container element
     */
    _findRepeatingSubfieldsContainer: function(fieldName) {
      var $fieldset = $('fieldset[data-module="scheming-repeating-subfields"]').filter(function() {
        var $fs = $(this);
        if ($fs.find('.scheming-subfield-group[data-field="' + fieldName + '"]').length > 0) {
          return true;
        }
        if ($fs.find('[name^="' + fieldName + '-"]').length > 0) {
          return true;
        }
        if ($fs.find('[name^="' + fieldName + '__"]').length > 0) {
          return true;
        }
        return false;
      }).first();

      if ($fieldset.length > 0) {
        return $fieldset;
      }

      var $authorGroup = $('.author-group').filter(function() {
        return $(this).find('[name^="' + fieldName + '__"], [name^="' + fieldName + '-"]').length > 0;
      }).first();
      if ($authorGroup.length > 0) {
        return $authorGroup;
      }

      var $group = $('.scheming-repeating-subfields-group[data-field-name="' + fieldName + '"]').first();
      if ($group.length > 0) {
        return $group;
      }

      var $module = $('[data-module="scheming-repeating-subfields"][data-field-name="' + fieldName + '"]').first();
      if ($module.length > 0) {
        return $module;
      }

      var $existingInput = $('[name^="' + fieldName + '__"], [name^="' + fieldName + '-"]').first();
      if ($existingInput.length > 0) {
        var $closest = $existingInput.closest('fieldset[data-module="scheming-repeating-subfields"], .scheming-repeating-subfields-group, .author-group, .form-group');
        if ($closest.length > 0) {
          return $closest;
        }
      }

      return $();
    },

    /**
     * Check whether repeating subfields already contain values
     * @param {jQuery} $container - Container element
     * @param {string} fieldName - Base field name
     * @returns {boolean} True if any non-empty input exists
     */
    _hasRepeatingSubfieldValues: function($container, fieldName) {
      var hasValue = false;
      $container.find('[name^="' + fieldName + '__"], [name^="' + fieldName + '-"]').filter(function() {
        return $(this).closest('[name="repeating-template"]').length === 0;
      }).each(function() {
        var value = ($(this).val() || '').trim();
        if (value) {
          hasValue = true;
          return false;
        }
      });
      return hasValue;
    },

    /**
     * Show success message
     * @param {string} message - Success message
     */
    _showSuccess: function(message) {
      // Always show inline success alert to avoid theme mis-styling flash messages
      this.el.find('.doi-success').remove();
      this._hideError();

      var $success = $('<div class="alert alert-success doi-success">')
        .html('<i class="fa fa-check-circle"></i> ' + message)
        .insertAfter(this.$input.closest('.doi-input-group'));
      
      setTimeout(function() {
        $success.fadeOut(function() { $(this).remove(); });
      }, 3000);
    },

    /**
     * Debounce utility function
     * @param {Function} func - Function to debounce
     * @param {number} wait - Wait time in milliseconds
     * @returns {Function} Debounced function
     */
    _debounce: function(func, wait) {
      var timeout;
      return function() {
        var context = this;
        var args = arguments;
        clearTimeout(timeout);
        timeout = setTimeout(function() {
          func.apply(context, args);
        }, wait);
      };
    }
  };
});
