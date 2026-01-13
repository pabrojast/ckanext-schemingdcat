this.ckan.module('schemingdcat-dataset-notes', function ($) {
  'use strict';

  return {
    initialize: function () {
      this.$container = $(this.el);
      this.$toggle = this.$container.find('.dataset-notes__toggle');
      this.$preview = this.$container.find('.dataset-notes__preview');
      this.$full = this.$container.find('.dataset-notes__full');

      if (!this.$toggle.length || !this.$full.length) {
        return;
      }

      this.moreLabel = this.$container.attr('data-more-label') || this.$toggle.text() || 'Read more';
      this.lessLabel = this.$container.attr('data-less-label') || 'Show less';

      this.$container.addClass('dataset-notes--collapsed');
      this.$toggle.attr('aria-expanded', 'false');
      this.$full.attr('aria-hidden', 'true');

      this.$toggle.on('click', this.toggle.bind(this));
    },

    toggle: function (evt) {
      evt.preventDefault();

      var expanded = this.$container.hasClass('dataset-notes--expanded');
      expanded = !expanded;

      this.$container.toggleClass('dataset-notes--expanded', expanded);
      this.$container.toggleClass('dataset-notes--collapsed', !expanded);
      this.$toggle.attr('aria-expanded', expanded);
      this.$full.attr('aria-hidden', !expanded);
      this.$toggle.text(expanded ? this.lessLabel : this.moreLabel);
    }
  };
});
