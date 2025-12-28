ckan.module('schemingdcat-group-multiselect', function ($) {
  'use strict';

  var instances = [];
  var $hiddenContainer = null;
  var initialized = false;

  function cleanupStaleInstances() {
    // Remove instances whose DOM elements no longer exist in the document
    instances = instances.filter(function (instance) {
      return instance.$el && instance.$el.closest('body').length > 0;
    });
  }

  function ensureHiddenContainer(selector) {
    // Always re-check the DOM to handle page reloads/navigation
    var $existing = $(selector);
    if ($existing.length) {
      $hiddenContainer = $existing;
      return $hiddenContainer;
    }

    // Create new container if not found
    $hiddenContainer = $('<div>', { id: 'groups-hidden-inputs', css: { display: 'none' } });
    $('form').first().append($hiddenContainer);

    return $hiddenContainer;
  }

  function rebuildHiddenInputs() {
    // Clean up stale instances first
    cleanupStaleInstances();

    if (!$hiddenContainer || !$hiddenContainer.length) {
      return;
    }

    $hiddenContainer.empty();

    var orderedInstances = instances.slice().sort(function (a, b) {
      return a.order - b.order;
    });

    var index = 0;

    orderedInstances.forEach(function (instance) {
      // Skip if the instance's select element is no longer in DOM
      if (!instance.$select || !instance.$select.closest('body').length) {
        return;
      }
      var values = instance.getSelected();
      values.forEach(function (value) {
        if (value) {
          $('<input>', {
            type: 'hidden',
            name: 'groups__' + index + '__id',
            value: value
          }).appendTo($hiddenContainer);
          index += 1;
        }
      });
    });
  }

  return {
    initialize: function () {
      this.$el = $(this.el);
      this.$select = this.$el.find('select[data-group-multiselect]');
      this.$tokens = this.$el.find('.group-token-list');
      this.order = parseInt(this.$el.data('groupOrder'), 10) || 0;
      this.type = this.$el.data('groupType') || 'member';
      this.instanceId = this.$el.attr('id') || this.type + '-' + this.order;

      // Clean up stale instances from previous page loads
      cleanupStaleInstances();

      // Prevent duplicate registration of the same element
      var isDuplicate = instances.some(function (inst) {
        return inst.$el && inst.$el.is(this.$el);
      }.bind(this));

      if (isDuplicate) {
        return;
      }

      var containerSelector = this.$el.data('hiddenContainer') || '#groups-hidden-inputs';
      ensureHiddenContainer(containerSelector);

      instances.push(this);

      var self = this;

      this.$select.on('change.groupMultiselect', function () {
        self.renderTokens();
        rebuildHiddenInputs();
      });

      this.$tokens.on('click.groupMultiselect', '[data-remove-value]', function (event) {
        event.preventDefault();
        var value = $(this).data('removeValue');
        self.$select.find('option[value="' + value + '"]').prop('selected', false);
        self.$select.trigger('change');
      });

      this.renderTokens();
      rebuildHiddenInputs();
    },

    teardown: function () {
      // Unbind namespaced events
      if (this.$select) {
        this.$select.off('.groupMultiselect');
      }
      if (this.$tokens) {
        this.$tokens.off('.groupMultiselect');
      }

      var index = instances.indexOf(this);
      if (index !== -1) {
        instances.splice(index, 1);
        rebuildHiddenInputs();
      }
    },

    getSelected: function () {
      return this.$select.find('option:selected').map(function () {
        return $(this).val();
      }).get();
    },

    renderTokens: function () {
      var self = this;
      var emptyText = this.$tokens.data('emptyText') || '';

      this.$tokens.empty();

      var selections = this.$select.find('option:selected');
      if (!selections.length) {
        if (emptyText) {
          $('<span>', { 'class': 'text-muted', text: emptyText }).appendTo(this.$tokens);
        }
        return;
      }

      selections.each(function () {
        var $option = $(this);
        var value = $option.val();
        var label = $option.text();
        var $token = $('<span>', { 'class': 'group-token', text: label });
        var $remove = $('<button>', {
          type: 'button',
          'class': 'group-token-remove',
          'data-remove-value': value,
          'aria-label': 'Remove ' + label
        }).html('&times;');

        $token.append($remove);
        self.$tokens.append($token);
      });
    }
  };
});
