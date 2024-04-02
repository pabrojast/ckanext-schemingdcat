/**
 * A CKAN module that provides functionality for copying a permanent URL to the clipboard.
 *
 * @module schemingdcat-table-permament-url
 * @param {Object} $ - The jQuery object.
 * @param {Object} _ - The underscore object.
 */
(function () {
  var debug = $.proxy(window.console, "debug");
  var warn = $.proxy(window.console, "warn");
  var error = $.proxy(window.console, "error");

  this.ckan.module("schemingdcat-table-permament-url", function ($, _) {
    function copy() {
      var copyText = document.querySelector("#input");
      copyText.select();

      return new Promise((resolve, reject) => {
        navigator.permissions
          .query({ name: "clipboard-write" })
          .then((result) => {
            if (result.state == "granted" || result.state == "prompt") {
              if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard
                  .writeText(copyText.value)
                  .then(() => {
                    resolve(true);
                  })
                  .catch((err) => {
                    error("Error copying text: ", err);
                    document.execCommand("copy");
                    resolve(true);
                  });
              } else {
                document.execCommand("copy");
                resolve(true);
              }
            } else {
              error("Permission to access the clipboard denied");
              document.execCommand("copy");
              resolve(true);
            }
          });
      });
    }

    document.querySelector("#copy").addEventListener("click", () => {
      copy().then((result) => {
        if (result) {
          var input = document.querySelector("#input");
          var span = document.createElement("span");
          span.innerHTML = '<i class="fa fa-clipboard"></i>';
          span.classList.add("permalink-copy");
          input.parentNode.replaceChild(span, input);

          setTimeout(() => {
            span.parentNode.replaceChild(input, span);
          }, 1000);
        } else {
          error("Error copying text");
        }
      });
    });
  });
}).apply(this);
