/**
 * schemingdcat-org-autofill.js
 *
 * Auto-fills the author (legacy) and the first "authors" repeating-subfield
 * entry with the title of the selected organization.
 *
 * Behaviour:
 *  - Only active on dataset *creation* forms (not edit).
 *  - On page load: waits a short tick so that auto-contact /
 *    autofill-responsible-party run first, then overrides the author fields
 *    with the currently selected org title.
 *  - On owner_org change: updates the author fields with the new org title.
 *  - Publisher and maintainer fields are intentionally NOT modified.
 *
 * DOI creator priority (ckanext-doi):
 *  1. "authors" repeating subfield (enhanced) — authors-<index>-name
 *  2. "author" legacy field — fallback only when "authors" is empty
 *
 * Scheming repeating-subfield naming conventions (both supported):
 *  - authors-<index>-<subfield>    (scheming 3.x hyphen format)
 *  - authors__<index>__<subfield>  (older double-underscore format)
 */
ckan.module('schemingdcat-org-autofill', function ($) {
  'use strict';

  // Selectors for the first "name" input inside the authors repeating subfield
  // covering both scheming naming conventions.
  var AUTHORS_NAME_SELECTORS = [
    'input[name^="authors-"][name$="-name"]',
    'input[name^="authors__"][name$="__name"]',
    'input[name^="authors_json"][name$="name"]'
  ].join(', ');

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

      // 1) Enhanced "authors" repeating subfield — primary DOI creator source
      this._setFirstAuthorsName(orgTitle);

      // 2) Legacy author field (admin-only, but acts as fallback for DOI)
      this._setField('input[name="author"]', orgTitle);
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
     * Supports both scheming naming conventions:
     *   authors-0-name      (scheming 3.x)
     *   authors__0__name    (older format)
     */
    _setFirstAuthorsName: function (orgTitle) {
      var $nameInputs = $(AUTHORS_NAME_SELECTORS);
      if (!$nameInputs.length) {
        return;
      }
      var $first = $nameInputs.first();
      // Always set on org change in create mode; the org IS the dataset creator
      $first.val(orgTitle).trigger('change');
    }
  };
});
