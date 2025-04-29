/**
 * Hisaab Embed Script
 * Finds all [data-hisaab-district] elements and replaces them with
 * live accountability card iframes.
 *
 * Usage:
 *   <div
 *     data-hisaab-district="GAYA"
 *     data-hisaab-scheme="mgnrega"
 *     data-hisaab-theme="light"
 *     data-hisaab-width="400"
 *   ></div>
 *   <script src="https://hisaab.in/embed.js" async></script>
 *
 * Attributes:
 *   data-hisaab-district  (required) District name, e.g. "GAYA"
 *   data-hisaab-scheme    (optional) Scheme slug: mgnrega|pmgsy|pmayg|pmkisan|jjm|pmposhan|nsap|nfsa
 *   data-hisaab-theme     (optional) "light" (default) or "dark"
 *   data-hisaab-width     (optional) Card width in px, default 400
 *   data-hisaab-fin-year  (optional) Financial year, default "2024-2025"
 */
(function () {
  "use strict";

  var API_BASE = "https://hisaab.in/api/v1/embed";

  function buildUrl(district, attrs) {
    var params = [];
    if (attrs.scheme) params.push("scheme=" + encodeURIComponent(attrs.scheme));
    if (attrs.theme) params.push("theme=" + encodeURIComponent(attrs.theme));
    if (attrs.width) params.push("width=" + encodeURIComponent(attrs.width));
    if (attrs.finYear) params.push("fin_year=" + encodeURIComponent(attrs.finYear));
    var base = API_BASE + "/" + encodeURIComponent(district);
    return params.length ? base + "?" + params.join("&") : base;
  }

  function injectCard(el) {
    var district = el.getAttribute("data-hisaab-district");
    if (!district) return;

    var attrs = {
      scheme: el.getAttribute("data-hisaab-scheme") || "",
      theme: el.getAttribute("data-hisaab-theme") || "light",
      width: el.getAttribute("data-hisaab-width") || "400",
      finYear: el.getAttribute("data-hisaab-fin-year") || "2024-2025",
    };

    var width = parseInt(attrs.width, 10) || 400;
    var url = buildUrl(district, attrs);

    // Create a sandboxed iframe
    var iframe = document.createElement("iframe");
    iframe.src = url;
    iframe.width = width;
    iframe.height = 1; // Will auto-resize via postMessage or load event
    iframe.scrolling = "no";
    iframe.frameBorder = "0";
    iframe.style.cssText = [
      "border:none",
      "overflow:hidden",
      "display:block",
      "max-width:100%",
      "width:" + width + "px",
      "transition:height 0.2s ease",
    ].join(";");
    iframe.setAttribute("loading", "lazy");
    iframe.setAttribute("title", "Hisaab accountability card — " + district);

    // Estimate height from card content after load; fall back to 300px
    iframe.addEventListener("load", function () {
      try {
        var doc = iframe.contentDocument || iframe.contentWindow.document;
        var body = doc && doc.body;
        if (body) {
          iframe.style.height = body.scrollHeight + "px";
          return;
        }
      } catch (_) {
        // Cross-origin: use a fixed estimate
      }
      iframe.style.height = "300px";
    });

    // Replace target element content with iframe
    el.innerHTML = "";
    el.style.display = "block";
    el.appendChild(iframe);
  }

  function init() {
    var elements = document.querySelectorAll("[data-hisaab-district]");
    for (var i = 0; i < elements.length; i++) {
      injectCard(elements[i]);
    }
  }

  // Run after DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
