/* Add CKAN CSRF token to all same-origin jQuery AJAX requests */
(function (jq) {
  if (!jq) {
    return;
  }

  function getCsrfFieldName() {
    var metaField = document.querySelector('meta[name="csrf_field_name"]');
    if (metaField && metaField.getAttribute('content')) {
      return metaField.getAttribute('content');
    }
    return '_csrf_token';
  }

  function getCsrfToken() {
    var fieldName = getCsrfFieldName();

    var metaToken = document.querySelector('meta[name="' + fieldName + '"]');
    if (metaToken && metaToken.getAttribute('content')) {
      return metaToken.getAttribute('content');
    }

    var input = document.querySelector('input[name="' + fieldName + '"]');
    if (input && input.value) {
      return input.value;
    }

    var re = new RegExp('(?:^|; )' + fieldName + '=([^;]+)');
    var match = document.cookie.match(re);
    if (match) {
      return decodeURIComponent(match[1]);
    }

    return null;
  }

  jq.ajaxPrefilter(function (options, originalOptions, xhr) {
    if (options.crossDomain) {
      return;
    }

    var token = getCsrfToken();
    if (token) {
      xhr.setRequestHeader('X-CSRFToken', token);
    }
  });
})(window.jQuery);
