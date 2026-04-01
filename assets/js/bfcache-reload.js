// Fix "blank page on back" issues caused by BFCache restoring pages where JS-driven
// components (charts/maps) don't rehydrate correctly. Only reload on back/forward.
(function () {
  "use strict";
  const key = `bfcacheReloaded:${window.location.pathname}`;

  function isBackForwardNavigation(event) {
    if (event && event.persisted) return true;
    try {
      const nav = performance.getEntriesByType && performance.getEntriesByType("navigation");
      const entry = nav && nav[0];
      return entry && entry.type === "back_forward";
    } catch (_) {
      return false;
    }
  }

  window.addEventListener("pageshow", function (event) {
    const backForward = isBackForwardNavigation(event);
    if (!backForward) {
      try { window.sessionStorage.removeItem(key); } catch (_) {}
      return;
    }

    // Avoid loops: only force one reload per BFCache restore.
    try {
      if (window.sessionStorage.getItem(key) === "1") {
        window.sessionStorage.removeItem(key);
        return;
      }
      window.sessionStorage.setItem(key, "1");
    } catch (_) {}

    window.location.reload();
  });
})();
