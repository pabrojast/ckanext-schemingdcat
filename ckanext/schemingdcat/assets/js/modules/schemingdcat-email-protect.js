ckan.module('schemingdcat-email-protect', function ($) {
  'use strict';

  function reverseString(value) {
    return (value || '').split('').reverse().join('');
  }

  return {
    initialize: function () {
      this.$el = $(this.el);
      this.email = this._composeEmail();
      this.$status = this.$el.find('.email-status');

      var self = this;

      this.$el.on('click', '[data-action="copy"]', function (event) {
        event.preventDefault();
        self.copyEmail();
      });

      this.$el.on('click', '[data-action="compose"]', function (event) {
        event.preventDefault();
        self.composeEmail();
      });
    },

    _composeEmail: function () {
      var local = reverseString(this.$el.data('emailLocal'));
      var domain = reverseString(this.$el.data('emailDomain'));

      if (!local || !domain) {
        return '';
      }

      return local + '@' + domain;
    },

    copyEmail: function () {
      var email = this.email;
      if (!email) {
        return;
      }

      var self = this;
      var notify = function (message, success) {
        if (!self.$status.length) {
          return;
        }
        self.$status
          .text(message)
          .toggleClass('text-success', !!success)
          .toggleClass('text-danger', !success);
        window.setTimeout(function () {
          self.$status.text('').removeClass('text-success text-danger');
        }, 3000);
      };

      var onSuccess = function () {
        self.revealEmail();
        notify(self._('Email copied to clipboard'), true);
      };

      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(email).then(onSuccess).catch(function () {
          self._fallbackCopy(email, notify, onSuccess);
        });
      } else {
        self._fallbackCopy(email, notify, onSuccess);
      }
    },

    _fallbackCopy: function (email, notify, onSuccess) {
      var tempInput = $('<input>', {
        type: 'text',
        value: email,
        css: { position: 'absolute', left: '-9999px', opacity: 0 }
      }).appendTo('body');

      tempInput[0].select();

      try {
        var successful = document.execCommand('copy');
        if (successful) {
          onSuccess();
        } else {
          throw new Error('copy command unsuccessful');
        }
      } catch (err) {
        notify(this._('Copy not supported. Email revealed below.'), false);
        this.revealEmail();
      } finally {
        tempInput.remove();
      }
    },

    composeEmail: function () {
      if (!this.email) {
        return;
      }
      this.revealEmail();
      window.location.href = 'mailto:' + this.email;
    },

    revealEmail: function () {
      if (!this.email) {
        return;
      }
      var $mask = this.$el.find('.email-mask');
      if ($mask.length) {
        $mask.text(this.email);
      }
    },

    _: function (message) {
      if (window.ckan && window.ckan.i18n) {
        return window.ckan.i18n(message);
      }
      return message;
    }
  };
});
