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
      console.log('[group-multiselect] rebuildHiddenInputs: no container, returning');
      return;
    }

    console.log('[group-multiselect] rebuildHiddenInputs: instances count =', instances.length);
    instances.forEach(function (inst, idx) {
      console.log('[group-multiselect]   instance[' + idx + ']: type=' + inst.type + ', order=' + inst.order + ', inDOM=' + (inst.$select && inst.$select.closest('body').length > 0));
    });

    $hiddenContainer.empty();

    var orderedInstances = instances.slice().sort(function (a, b) {
      return a.order - b.order;
    });

    var index = 0;

    orderedInstances.forEach(function (instance) {
      // Re-query the element in case DOM was manipulated
      var $currentEl = instance.$el;
      if (!$currentEl || !$currentEl.closest('body').length) {
        console.log('[group-multiselect] rebuildHiddenInputs: skipping instance type=' + instance.type + ' ($el not in DOM)');
        return;
      }
      
      // Re-query the select element
      var $currentSelect = $currentEl.find('select[data-group-multiselect]');
      if (!$currentSelect.length) {
        console.log('[group-multiselect] rebuildHiddenInputs: skipping instance type=' + instance.type + ' (select not found)');
        return;
      }
      instance.$select = $currentSelect;
      
      var values = instance.getSelected();
      console.log('[group-multiselect] rebuildHiddenInputs: instance type=' + instance.type + ', values=', values);
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
    console.log('[group-multiselect] rebuildHiddenInputs: total hidden inputs created =', index);
  }

  return {
    initialize: function () {
      this.$el = $(this.el);
      this.$select = this.$el.find('select[data-group-multiselect]');
      this.$tokens = this.$el.find('.group-token-list');
      this.order = parseInt(this.$el.data('groupOrder'), 10) || 0;
      this.type = this.$el.data('groupType') || 'member';
      this.instanceId = this.$el.attr('id') || this.type + '-' + this.order;

      console.log('[group-multiselect] initialize: type=' + this.type + ', order=' + this.order);

      // Clean up stale instances from previous page loads
      cleanupStaleInstances();

      console.log('[group-multiselect] after cleanupStaleInstances: instances count =', instances.length);

      // Prevent duplicate registration of the same element
      var isDuplicate = instances.some(function (inst) {
        return inst.$el && inst.$el.is(this.$el);
      }.bind(this));

      if (isDuplicate) {
        console.log('[group-multiselect] initialize: duplicate detected, returning');
        return;
      }

      var containerSelector = this.$el.data('hiddenContainer') || '#groups-hidden-inputs';
      ensureHiddenContainer(containerSelector);

      instances.push(this);
      console.log('[group-multiselect] initialize: registered, instances count =', instances.length);

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
      // Re-query the select in case DOM was manipulated
      var $currentSelect = this.$el.find('select[data-group-multiselect]');
      if ($currentSelect.length) {
        this.$select = $currentSelect;
      }
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
