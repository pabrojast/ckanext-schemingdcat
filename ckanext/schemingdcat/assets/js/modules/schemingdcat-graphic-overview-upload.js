ckan.module('schemingdcat-graphic-overview-upload', function ($) {
  return {
    initialize: function () {
      var self = this;
      var $form = $('form.dataset-form');
      if (!$form.length) {
        return;
      }

      var $field = $form.find('input[name="graphic_overview"]');
      if (!$field.length || $field.data('graphic-overview-enhanced')) {
        return;
      }

      $field.data('graphic-overview-enhanced', true);

      var MAX_SIZE = 10 * 1024 * 1024; // 10MB
      var $fileInput = $('<input>', {
        type: 'file',
        accept: 'image/*',
        class: 'graphic-overview-file-input',
        style: 'display:none;'
      });

      var $dropzone = $('<div>', {
        class: 'upload-dropzone graphic-overview-dropzone',
        tabindex: 0,
        role: 'button',
        'aria-label': this._('Upload a graphic overview image')
      });

      $dropzone.append(
        '<div class="dropzone-content">' +
          '<i class="fa fa-image fa-3x"></i>' +
          '<p>' + this._('Drag an image here or click to upload') + '</p>' +
          '<p class="text-muted">' + this._('The asset URL will be stored in “Graphic overview of the dataset”.') + '</p>' +
        '</div>'
      );

      var $progress = $(
        '<div class="graphic-overview-progress" style="display:none;">' +
          '<div class="progress">' +
            '<div class="progress-bar"></div>' +
          '</div>' +
          '<p class="progress-text"></p>' +
        '</div>'
      );

      var $preview = $(
        '<div class="graphic-overview-preview" style="display:none;">' +
          '<img alt="' + this._('Graphic overview preview') + '" />' +
          '<div class="preview-actions">' +
            '<button type="button" class="btn btn-default btn-xs graphic-overview-replace">' +
              '<i class="fa fa-refresh"></i> ' + this._('Replace') +
            '</button>' +
            '<button type="button" class="btn btn-danger btn-xs graphic-overview-remove">' +
              '<i class="fa fa-trash"></i> ' + this._('Remove') +
            '</button>' +
            '<a class="btn btn-link btn-xs graphic-overview-open" target="_blank" rel="noopener">' +
              '<i class="fa fa-external-link"></i> ' + this._('Open') +
            '</a>' +
          '</div>' +
        '</div>'
      );

      var $error = $('<div class="graphic-overview-error text-danger" style="display:none;"></div>');
      var $wrapper = $('<div class="graphic-overview-upload"></div>');

      $wrapper.append($fileInput, $dropzone, $progress, $preview, $error);
      $field.after($wrapper);

      function clearError() {
        $error.hide().text('');
      }

      function showError(message) {
        $error.text(message || self._('Upload failed. Please try again.')).show();
      }

      function hidePreview() {
        $preview.hide();
        $preview.find('img').attr('src', '');
      }

      function showPreview(url) {
        $preview.find('img').attr('src', url);
        $preview.find('.graphic-overview-open').attr('href', url);
        $preview.show();
      }

      function setValue(url) {
        $field.val(url || '');
        $field.trigger('change');
        if (url) {
          showPreview(url);
        } else {
          hidePreview();
        }
      }

      function handleFiles(fileList) {
        if (!fileList || !fileList.length) {
          return;
        }

        var file = fileList[0];
        clearError();

        if (!file.type || file.type.indexOf('image') !== 0) {
          showError(self._('Please choose an image file.'));
          return;
        }

        if (file.size && file.size > MAX_SIZE) {
          showError(self._('Image is too large (max 10MB).'));
          return;
        }

        uploadFile(file);
      }

      function uploadFile(file) {
        $dropzone.addClass('uploading');
        $progress.show();
        $progress.find('.progress-bar').css('width', '0%');
        $progress.find('.progress-text').text(
          self._('Uploading {name}...').replace('{name}', file.name || 'image')
        );

        var formData = new FormData();
        formData.append('upload', file, file.name || 'graphic-overview.jpg');

        $.ajax({
          url: '/pages_upload',
          type: 'POST',
          data: formData,
          processData: false,
          contentType: false,
          dataType: 'json',
          xhr: function () {
            var xhr = $.ajaxSettings.xhr();
            if (xhr.upload) {
              xhr.upload.addEventListener('progress', function (evt) {
                if (evt.lengthComputable) {
                  var percent = Math.round((evt.loaded / evt.total) * 100);
                  $progress.find('.progress-bar').css('width', percent + '%');
                }
              }, false);
            }
            return xhr;
          }
        }).done(function (resp) {
          $dropzone.removeClass('uploading');
          $progress.hide();

          if (resp && resp.uploaded === 1 && resp.url) {
            setValue(resp.url);
          } else {
            var message = (resp && resp.error && resp.error.message) ?
              resp.error.message :
              self._('Upload failed. Please try again.');
            showError(message);
          }
        }).fail(function (jqXHR) {
          $dropzone.removeClass('uploading');
          $progress.hide();

          var message = self._('Upload failed. Please try again.');
          try {
            var payload = jqXHR.responseJSON || JSON.parse(jqXHR.responseText);
            if (payload && payload.error && payload.error.message) {
              message = payload.error.message;
            }
          } catch (e) {
            // Ignore parse errors
          }
          showError(message);
        });
      }

      $dropzone.on('click', function (e) {
        e.preventDefault();
        $fileInput.trigger('click');
      });

      $dropzone.on('keypress', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          $fileInput.trigger('click');
        }
      });

      $dropzone.on('dragover dragenter', function (e) {
        e.preventDefault();
        e.stopPropagation();
        $dropzone.addClass('dragover');
      });

      $dropzone.on('dragleave', function (e) {
        e.preventDefault();
        e.stopPropagation();
        $dropzone.removeClass('dragover');
      });

      $dropzone.on('drop', function (e) {
        e.preventDefault();
        e.stopPropagation();
        $dropzone.removeClass('dragover');
        handleFiles(e.originalEvent.dataTransfer.files);
      });

      $fileInput.on('change', function (e) {
        handleFiles(e.target.files);
        $(this).val('');
      });

      $preview.on('click', '.graphic-overview-remove', function (e) {
        e.preventDefault();
        setValue('');
        clearError();
      });

      $preview.on('click', '.graphic-overview-replace', function (e) {
        e.preventDefault();
        $fileInput.trigger('click');
      });

      $field.on('input change', function () {
        var current = $(this).val();
        if (current) {
          showPreview(current);
        } else {
          hidePreview();
        }
      });

      if ($field.val()) {
        showPreview($field.val());
      }
    }
  };
});
