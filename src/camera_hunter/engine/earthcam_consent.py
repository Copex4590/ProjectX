"""Dismiss EarthCam Cookiebot consent UI without accepting marketing cookies.

Does not replace or restyle the map. Only the Cookiebot dialog/underlay/widget
are hidden so the original EarthCam map remains usable.
"""

from __future__ import annotations

from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEngineScript

SCRIPT_NAME = "camera-hunter-earthcam-consent"

# Cookiebot on earthcam.com/mapsearch/. Necessary-only; never Allow All.
EARTHCAM_CONSENT_JS = r"""
(function () {
  if (window.__chEarthcamConsentWatch) return;
  const host = String(location.hostname || "");
  const href = String(location.href || "");
  const earthcam = /(^|\.)earthcam\.com$/i.test(host);
  const listing = /mapsearch/i.test(href);
  if (!earthcam && !listing) return;
  window.__chEarthcamConsentWatch = true;

  let necessaryOnlyDone = false;
  const styleId = "camera-hunter-earthcam-consent-style";

  const injectStyle = () => {
    if (document.getElementById(styleId)) return;
    const root = document.documentElement || document.head || document.body;
    if (!root) return;
    const css = document.createElement("style");
    css.id = styleId;
    css.textContent = [
      "#CybotCookiebotDialog,",
      "#CybotCookiebotDialogBodyUnderlay,",
      "#CookiebotWidget,",
      "#CookiebotWidget-widget,",
      "div[id^='CybotCookiebotDialog'] {",
      "  display: none !important;",
      "  visibility: hidden !important;",
      "  opacity: 0 !important;",
      "  pointer-events: none !important;",
      "  height: 0 !important;",
      "  max-height: 0 !important;",
      "}"
    ].join(" ");
    if (root.nodeName === "HTML") {
      (document.head || root).appendChild(css);
    } else {
      root.appendChild(css);
    }
  };

  const hideNode = (el) => {
    if (!el || !el.style) return;
    el.style.setProperty("display", "none", "important");
    el.style.setProperty("visibility", "hidden", "important");
    el.style.setProperty("opacity", "0", "important");
    el.style.setProperty("pointer-events", "none", "important");
    el.setAttribute("aria-hidden", "true");
  };

  const hideConsentUi = () => {
    injectStyle();
    hideNode(document.getElementById("CybotCookiebotDialog"));
    hideNode(document.getElementById("CybotCookiebotDialogBodyUnderlay"));
    hideNode(document.getElementById("CookiebotWidget"));
    document.querySelectorAll("div[id^='CybotCookiebotDialog']").forEach(hideNode);
    const html = document.documentElement;
    if (html && html.classList.contains("CybotCookiebotDialogActive")) {
      html.classList.remove("CybotCookiebotDialogActive");
    }
  };

  const applyNecessaryOnly = () => {
    if (necessaryOnlyDone) return;
    try {
      if (window.Cookiebot && typeof Cookiebot.submitCustomConsent === "function") {
        Cookiebot.submitCustomConsent(true, false, false, false);
        necessaryOnlyDone = true;
        if (typeof Cookiebot.hide === "function") Cookiebot.hide();
        return;
      }
    } catch (e) {}
    const decline = document.getElementById("CybotCookiebotDialogBodyButtonDecline");
    if (decline) {
      necessaryOnlyDone = true;
      try { decline.click(); } catch (e) {}
    }
  };

  const tick = () => {
    hideConsentUi();
    applyNecessaryOnly();
    hideConsentUi();
  };

  tick();
  [200, 600, 1500, 4000, 8000].forEach((ms) => {
    try { setTimeout(tick, ms); } catch (e) {}
  });
  try {
    const mo = new MutationObserver(tick);
    mo.observe(document.documentElement, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ["class", "style", "id"],
    });
  } catch (e) {}
})();
"""

CONSENT_BLOCKING_CHECK_JS = r"""
(function () {
  const isVisible = (el) => {
    if (!el) return false;
    let st = null;
    try { st = window.getComputedStyle(el); } catch (e) { return false; }
    if (!st) return false;
    if (st.display === "none" || st.visibility === "hidden") return false;
    if (Number(st.opacity) === 0) return false;
    const r = el.getBoundingClientRect();
    return r.width > 8 && r.height > 8;
  };
  const dlg = document.getElementById("CybotCookiebotDialog");
  const underlay = document.getElementById("CybotCookiebotDialogBodyUnderlay");
  const widget = document.getElementById("CookiebotWidget");
  const map = document.getElementById("map_canvas")
    || document.getElementById("outside-map-container")
    || document.querySelector(".leaflet-container");
  return JSON.stringify({
    consentBlocking: isVisible(dlg) || isVisible(underlay) || isVisible(widget),
    dialogVisible: isVisible(dlg),
    underlayVisible: isVisible(underlay),
    mapPresent: !!map,
    mapVisible: isVisible(map),
  });
})();
"""


def install_consent_script(profile: QWebEngineProfile) -> None:
    for point in (
        QWebEngineScript.InjectionPoint.DocumentCreation,
        QWebEngineScript.InjectionPoint.DocumentReady,
    ):
        script = QWebEngineScript()
        script.setName(f"{SCRIPT_NAME}-{point.name}")
        script.setSourceCode(EARTHCAM_CONSENT_JS)
        script.setInjectionPoint(point)
        script.setWorldId(int(QWebEngineScript.ScriptWorldId.MainWorld))
        script.setRunsOnSubFrames(False)
        profile.scripts().insert(script)
