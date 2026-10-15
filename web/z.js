/* Zaptu anonymous visit counter: nothing stored in the browser, no third parties. */
(function () {
  if (navigator.doNotTrack === "1" || navigator.globalPrivacyControl) return;
  if (!/(^|\.)zaptu\.ai$/.test(location.hostname)) return;
  // Render host, not api.zaptu.ai: the *.zaptu.ai Netlify cert lets browsers reuse the
  // zaptu.ai connection for api.zaptu.ai (HTTP/2 coalescing) and the beacon 404s at Netlify.
  var URL_ = "https://zaptu.onrender.com/v1/hit";
  function send(e) {
    var body = JSON.stringify({ e: e, p: location.pathname, r: document.referrer || "" });
    try {
      if (navigator.sendBeacon && navigator.sendBeacon(URL_, new Blob([body], { type: "text/plain" }))) return;
    } catch (_) {}
    try { fetch(URL_, { method: "POST", body: body, keepalive: true, mode: "no-cors" }); } catch (_) {}
  }
  send("pageview");
  document.addEventListener("click", function (ev) {
    var a = ev.target && ev.target.closest && ev.target.closest('a[href^="tel:"]');
    if (a) send("call_click");
  }, true);
})();
