/* Zaptu anonymous visit counter: nothing stored in the browser, no third parties. */
(function () {
  if (navigator.doNotTrack === "1" || navigator.globalPrivacyControl) return;
  if (!/(^|\.)zaptu\.ai$/.test(location.hostname)) return;
  var URL_ = "https://api.zaptu.ai/v1/hit";
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
