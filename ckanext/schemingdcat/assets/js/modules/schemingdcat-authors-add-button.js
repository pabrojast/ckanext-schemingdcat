ckan.module('schemingdcat-authors-add-button', function ($) {
  'use strict';

  return {
    initialize: function () {
      this.$authorGroup = $('.author-group').first();

      if (!this.$authorGroup.length) {
        return;
      }

      this.$addButton = this._findAddButton();

      if (!this.$addButton.length) {
        return;
      }

      this._boundUpdate = this._updateLabel.bind(this);

      this._updateLabel();
      this._initObserver();
      this._bindEvents();
    },

    teardown: function () {
      if (this._observer) {
        this._observer.disconnect();
        this._observer = null;
      }

      if (this.$addButton) {
        this.$addButton.off('.schemingdcatAuthors');
      }

      if (this.$authorGroup) {
        this.$authorGroup.off('.schemingdcatAuthors');
      }
    },

    _findAddButton: function () {
      var selectors = [
        'button[data-module="scheming-repeating-subfields-add"]',
        'a[data-module="scheming-repeating-subfields-add"]',
        'button.scheming-repeating-add',
        'a.scheming-repeating-add',
        '.scheming-add-subfield'
      ];

      for (var i = 0; i < selectors.length; i += 1) {
        var $candidate = this.$authorGroup.find(selectors[i]);
        if ($candidate.length) {
          return $candidate.first();
        }
      }

      return this.$authorGroup.find('button, a').filter(function () {
        var text = ($(this).text() || '').replace(/\s+/g, '').toLowerCase();
        return text === '+add' || text === 'add';
      }).first();
    },

    _bindEvents: function () {
      var self = this;

      this.$addButton.on('click.schemingdcatAuthors', function () {
        window.setTimeout(self._boundUpdate, 0);
      });

      this.$authorGroup.on(
        'click.schemingdcatAuthors',
        '[data-module="scheming-repeating-subfields-remove"], ' +
          '.scheming-repeating-remove, ' +
          '.remove-scheming-subfield',
        function () {
          window.setTimeout(self._boundUpdate, 0);
        }
      );
    },

    _initObserver: function () {
      var Observer = window.MutationObserver || window.WebKitMutationObserver;

      if (!Observer) {
        return;
      }

      this._observer = new Observer(this._boundUpdate);
      this._observer.observe(this.$authorGroup.get(0), {
        childList: true,
        subtree: true
      });
    },

    _countAuthors: function () {
      var indexes = Object.create(null);

      this.$authorGroup.find('[name^="authors__"]').each(function () {
        var nameAttr = this.getAttribute('name');

        if (!nameAttr) {
          return;
        }

        var match = nameAttr.match(/^authors__([0-9a-fA-F-]+)__/);

        if (match) {
          indexes[match[1]] = true;
        }
      });

      var count = 0;

      for (var key in indexes) {
        if (Object.prototype.hasOwnProperty.call(indexes, key)) {
          count += 1;
        }
      }

      return count;
    },

    _updateLabel: function () {
      if (!this.$addButton || !this.$addButton.length) {
        return;
      }

      var authorCount = this._countAuthors();
      var label = authorCount > 0 ? 'Add Another Author' : 'Add Author';
      var current = (this.$addButton.text() || '').trim();

      if (current === label) {
        return;
      }

      this.$addButton.text(label);
    }
  };
});
