ckan.module('schemingdcat-group-multiselect', function ($) {
  'use strict';

  var instances = [];
  var $hiddenContainer = null;

  function ensureHiddenContainer(selector) {
    if ($hiddenContainer && $hiddenContainer.length) {
      return $hiddenContainer;
    }

    $hiddenContainer = $(selector);

    if (!$hiddenContainer.length) {
      $hiddenContainer = $('<div>', { id: 'groups-hidden-inputs', css: { display: 'none' } });
      $('form').first().append($hiddenContainer);
    }

    return $hiddenContainer;
  }

  function rebuildHiddenInputs() {
    if (!$hiddenContainer || !$hiddenContainer.length) {
      return;
    }

    $hiddenContainer.empty();

    var orderedInstances = instances.slice().sort(function (a, b) {
      return a.order - b.order;
    });

    var index = 0;

    orderedInstances.forEach(function (instance) {
      var values = instance.getSelected();
      values.forEach(function (value) {
        $('<input>', {
          type: 'hidden',
          name: 'groups__' + index + '__id',
          value: value
        }).appendTo($hiddenContainer);
        index += 1;
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

      var containerSelector = this.$el.data('hiddenContainer') || '#groups-hidden-inputs';
      ensureHiddenContainer(containerSelector);

      instances.push(this);

      var self = this;

      this.$select.on('change', function () {
        self.renderTokens();
        rebuildHiddenInputs();
      });

      this.$tokens.on('click', '[data-remove-value]', function (event) {
        event.preventDefault();
        var value = $(this).data('removeValue');
        self.$select.find('option[value="' + value + '"]').prop('selected', false);
        self.$select.trigger('change');
      });

      this.renderTokens();
      rebuildHiddenInputs();
    },

    teardown: function () {
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
