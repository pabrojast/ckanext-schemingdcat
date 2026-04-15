/**
 * schemingdcat-org-autofill.js
 *
 * Auto-fills the author (legacy) and the first "authors" repeating-subfield
 * entry with the title of the selected organization.
 *
 * Behaviour:
 *  - Only active on dataset *creation* forms (not edit).
 *  - On page load: waits a short tick so that auto-contact /
 *    autofill-responsible-party run first, then overrides the author field
 *    with the currently selected org title.
 *  - On owner_org change: updates the author field with the new org title.
 *  - Publisher and maintainer fields are intentionally NOT modified.
 */
ckan.module('schemingdcat-org-autofill', function ($) {
  'use strict';

  return {
    initialize: function () {
      var isEditMode = window.location.href.indexOf('/edit/') !== -1;
      if (isEditMode) {
        return;
      }

      this.$orgSelect = $('select[name="owner_org"]');
      if (!this.$orgSelect.length) {
        return;
      }

      $.proxyAll(this, /_on/);

      this.$orgSelect.on('change', this._onOrgChange);

      // Delay so other autofill modules (auto-contact, autofill-responsible-party)
      // finish first; then override with the org-based value.
      var self = this;
      window.setTimeout(function () {
        self._onOrgChange();
      }, 300);
    },

    /**
     * Reads the selected org title and pushes it into author fields.
     */
    _onOrgChange: function () {
      var orgTitle = this._getSelectedOrgTitle();
      if (!orgTitle) {
        return;
      }

      // Legacy author field (admin-only, but harmless if absent)
      this._setField('input[name="author"]', orgTitle);

      // First entry of the "authors" repeating subfield (DOI Author Information)
      this._setFirstAuthorsName(orgTitle);
    },

    /**
     * Extracts the visible text of the selected <option> in the org dropdown.
     */
    _getSelectedOrgTitle: function () {
      var $selected = this.$orgSelect.find('option:selected');
      if (!$selected.length || !$selected.val()) {
        return null;
      }
      return ($selected.text() || '').trim();
    },

    /**
     * Sets a form field value (always overrides on org change in create mode).
     */
    _setField: function (selector, value) {
      var $field = $(selector);
      if ($field.length) {
        $field.val(value).trigger('change');
      }
    },

    /**
     * Sets the "name" sub-field of the first authors repeating entry.
     * The naming convention used by ckanext-scheming repeating subfields is
     * authors__<index-or-uuid>__name.
     */
    _setFirstAuthorsName: function (orgTitle) {
      var $nameInputs = $('input[name^="authors__"][name$="__name"]');
      if ($nameInputs.length) {
        var $first = $nameInputs.first();
        if (!$first.val()) {
          $first.val(orgTitle).trigger('change');
        }
      }
    }
  };
});
