(function () {
  "use strict";

  var $ = window.jQuery || window.$ || (window.CTFd && CTFd.lib && CTFd.lib.$);
  if (!$) return;

  var ezAlert =
    window.CTFd && CTFd.ui && CTFd.ui.ezq ? CTFd.ui.ezq.ezAlert : null;

  function isValidHttpUrl(value) {
    try {
      var url = new URL(value);
      return url.protocol === "http:" || url.protocol === "https:";
    } catch (e) {
      return false;
    }
  }

  function showAlert(message) {
    if (typeof ezAlert === "function") {
      ezAlert({ title: "Error", body: message, button: "OK" });
    } else {
      window.alert(message);
    }
  }

  function ensureAiLinkRow() {
    var modal = $("#challenge-window");
    if (modal.length === 0) return;

    // Only inject once per modal lifetime.
    if ($("#challenge-ai-link").length > 0) return;

    var submitRow = modal.find(".submit-row");
    if (submitRow.length === 0) return;

    var row = $(
      '<div class="form-group ai-link-row">' +
        '<label for="challenge-ai-link">AI Link' +
        '<span class="text-danger">*</span></label>' +
        '<input class="form-control" type="url" id="challenge-ai-link"' +
        ' name="ai_link" placeholder="https://chatgpt.com/..." autocomplete="off">' +
        '<small class="form-text text-muted">' +
        "URL AI yang digunakan untuk mengerjakan challenge ini wajib diisi.</small>" +
        "</div>"
    );
    submitRow.before(row);
  }

  // view.js re-assigns CTFd._internal.challenge.submit on every modal open, so
  // the stable interception point is CTFd.api.post_challenge_attempt, which is
  // defined once by the core API bundle.
  var original = window.CTFd && CTFd.api && CTFd.api.post_challenge_attempt;
  if (typeof original !== "function") return;

  CTFd.api.post_challenge_attempt = function (parameters, body) {
    // Admin challenge previews must not require an AI Link.
    if (parameters && parameters.preview) {
      return original.call(this, parameters, body);
    }

    var input = $("#challenge-ai-link");
    var ai_link = input.length ? String(input.val() || "").trim() : "";

    if (ai_link === "") {
      showAlert("AI Link wajib diisi sebelum submit.");
      // Return a benign response: pixo/core renderSubmissionResponse falls
      // through on unknown statuses and re-enables the submit button ~3s later.
      return Promise.resolve({
        success: true,
        data: { status: "unknown", message: "" },
      });
    }

    if (!isValidHttpUrl(ai_link)) {
      showAlert("AI Link harus berupa URL yang valid (http/https).");
      return Promise.resolve({
        success: true,
        data: { status: "unknown", message: "" },
      });
    }

    body = body || {};
    body.ai_link = ai_link;

    return original.call(this, parameters, body);
  };

  $(document).on("shown.bs.modal", "#challenge-window", ensureAiLinkRow);

  // Safety net: also inject when the submit button is clicked and the shown
  // event raced. No-op if the row is already present.
  $(document).on("click", "#challenge-input, .challenge-solve", ensureAiLinkRow);
})();