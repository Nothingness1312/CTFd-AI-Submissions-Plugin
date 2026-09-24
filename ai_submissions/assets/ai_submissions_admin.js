// ai_submissions_admin.js
// Plugin-owned script: injects an "AI Link" column into the Admin
// Submissions table (/admin/submissions) for ALL views (all/correct/
// incorrect), placed right after the "Provided" column.
// Only runs on the admin submissions page; no core/theme files touched.
(function () {
  "use strict";

  // Runs on the base view (/admin/submissions) plus the filtered views
  // (/admin/submissions/correct and /admin/submissions/incorrect).
  if (
    window.location.pathname !== "/admin/submissions" &&
    !window.location.pathname.startsWith("/admin/submissions/")
  ) {
    return;
  }

  function init() {
    var table = document.querySelector("table");
    if (!table) return;
    if (table.querySelector("th.ai-link-col")) return; // already injected

    // Locate "Provided" header cell
    var headers = table.querySelectorAll("thead th");
    var providedHeader = null;
    for (var i = 0; i < headers.length; i++) {
      if (headers[i].textContent.trim() === "Provided") {
        providedHeader = headers[i];
        break;
      }
    }
    if (!providedHeader) return;

    // Insert <th>AI Link</th> right after Provided
    var aiHeader = document.createElement("th");
    aiHeader.className = "ai-link-col";
    aiHeader.innerHTML = "<b>AI Link</b>";
    providedHeader.parentNode.insertBefore(aiHeader, providedHeader.nextSibling);

    // Gather submission ids per row (checkbox data-submission-id is authoritative)
    var rows = table.querySelectorAll("tbody tr");
    var ids = [];
    var rowMap = {}; // submission_id -> tr
    for (var r = 0; r < rows.length; r++) {
      var box = rows[r].querySelector("input[data-submission-id]");
      var sid = box ? box.getAttribute("data-submission-id") : null;
      if (!sid) continue;
      ids.push(sid);
      rowMap[sid] = rows[r];
    }

    if (ids.length === 0) return;

    fetch("/admin/ai-submissions/links?submission_ids=" + ids.join(","), {
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    })
      .then(function (resp) {
        return resp.json();
      })
      .then(function (data) {
        for (var j = 0; j < ids.length; j++) {
          var sid = ids[j];
          var link = data[sid];
          var tr = rowMap[sid];
          if (!tr) continue;
          var flagTd = tr.querySelector("td.flag");
          if (!flagTd) continue;
          var td = document.createElement("td");
          td.className = "ai-link-col";
          if (link) {
            var a = document.createElement("a");
            a.href = link;
            a.target = "_blank";
            a.rel = "noopener noreferrer";
            a.textContent = link;
            td.appendChild(a);
          }
          flagTd.parentNode.insertBefore(td, flagTd.nextSibling);
        }
      })
      .catch(function () {
        // Leave the column empty on transient errors
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();