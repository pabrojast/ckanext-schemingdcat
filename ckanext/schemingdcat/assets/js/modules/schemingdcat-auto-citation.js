ckan.module('schemingdcat-auto-citation', function ($) {
  'use strict';

  return {
    initialize: function () {
      $.proxyAll(this, /_/);
      this.$citationField = $('[name="citation"]');
      if (!this.$citationField.length) {
        return;
      }
      this.$customCitationField = $('[name="custom_citation"]');
      this._bindEvents();
      this._updateCitation();
    },

    _bindEvents: function () {
      var self = this;
      var selectors = [
        '[name="title_translated-en"]',
        '[name^="title_translated-"]',
        '[name="title"]',
        '[name="publication_year"]',
        '[name="publisher_name"]',
        '[name="custom_doi"]',
        '[name="document_doi"]',
        '[name="author"]'
      ];

      selectors.forEach(function (sel) {
        $(document).on('input change', sel, self._updateCitation);
      });

      $(document).on('input change', '[name^="authors_json"]', this._updateCitation);
    },

    _collectAuthors: function () {
      var authors = [];
      $('[name^="authors_json"][name$="name"]').each(function () {
        var val = ($(this).val() || '').trim();
        if (val) {
          authors.push(val);
        }
      });

      if (!authors.length) {
        var fallback = ($('[name="author"]').val() || '').trim();
        if (fallback) {
          authors = fallback.split(/[;,]/).map(function (item) {
            return item.trim();
          }).filter(Boolean);
        }
      }
      return authors;
    },

    _pickTitle: function () {
      var $titleEn = $('[name="title_translated-en"]');
      if ($titleEn.length && $titleEn.val().trim()) {
        return $titleEn.val().trim();
      }

      var $translated = $('[name^="title_translated-"]').filter(function () {
        return ($(this).val() || '').trim().length;
      }).first();
      if ($translated.length) {
        return ($translated.val() || '').trim();
      }

      return ($('[name="title"]').val() || '').trim();
    },

    _cleanDoi: function (raw) {
      if (!raw) return '';
      var doi = raw.trim();
      var prefixes = ['https://doi.org/', 'http://doi.org/', 'https://dx.doi.org/', 'http://dx.doi.org/', 'doi:', 'DOI:'];
      prefixes.forEach(function (prefix) {
        if (doi.toLowerCase().indexOf(prefix.toLowerCase()) === 0) {
          doi = doi.substring(prefix.length);
        }
      });
      if (!doi) return '';
      if (doi.indexOf('10.') === 0) {
        return 'https://doi.org/' + doi;
      }
      return doi;
    },

    _buildCitation: function () {
      if (this.$customCitationField && this.$customCitationField.length) {
        var customVal = (this.$customCitationField.val() || '').trim();
        if (customVal) {
          return customVal;
        }
      }

      var authors = this._collectAuthors();
      var year = ($('[name="publication_year"]').val() || '').trim();
      var title = this._pickTitle();
      var publisher = ($('[name="publisher_name"]').val() || '').trim();
      var doi = this._cleanDoi(($('[name="custom_doi"]').val() || $('[name="document_doi"]').val() || '').trim());

      var parts = [];
      if (authors.length) {
        parts.push(authors.join('; '));
      }
      if (year) {
        parts.push('(' + year + ').');
      }
      if (title) {
        parts.push(title + '.');
      }
      parts.push('[Document].');
      if (publisher) {
        parts.push(publisher + '.');
      }
      if (doi) {
        parts.push(doi);
      }

      return parts.join(' ').replace(/\s+/g, ' ').trim();
    },

    _updateCitation: function () {
      if (!this.$citationField || !this.$citationField.length) return;
      var citation = this._buildCitation();
      this.$citationField.val(citation).trigger('change');
    }
  };
});
