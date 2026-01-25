/* Add CKAN CSRF token to all same-origin jQuery AJAX requests */
(function (jq) {
  if (!jq) {
    return;
  }

  function getCsrfToken() {
    var input = document.querySelector('input[name="csrf_token"]');
    if (input && input.value) {
      return input.value;
    }

    var match = document.cookie.match(/(?:^|; )csrf_token=([^;]+)/);
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
