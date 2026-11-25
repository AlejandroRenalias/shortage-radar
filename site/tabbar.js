// Tab bar motion. The green mark slides from the old tab to the new one.
// Browsers with cross-document View Transitions do it in CSS (see style.css).
// Other browsers use the fallback here: a tap stores the old tab in sessionStorage and the next page animates the mark (transform only).
(function () {
  var KEY = 'sr-tab-from';
  var MAX_AGE = 5000;

  // Pure: returns the tab-width steps to start from (old index minus new index), or 0 for no slide.
  // The stored tap must name this page as its target, so a tap that never arrived cannot colour a later visit.
  function slideSteps(stored, current, navType, now, reduced, tabs) {
    if (reduced || !stored || navType !== 'navigate') return 0;
    if (typeof stored.from !== 'number' || typeof stored.to !== 'number' || typeof stored.at !== 'number') return 0;
    if (stored.to !== current || stored.from === current || stored.from < 0 || stored.from >= tabs || current < 0 || current >= tabs) return 0;
    var age = now - stored.at;
    if (age < 0 || age > MAX_AGE) return 0;
    return stored.from - current;
  }

  if (typeof module !== 'undefined' && module.exports) { module.exports = { slideSteps: slideSteps }; return; }

  var store = null;
  try { store = window.sessionStorage; } catch (e) { store = null; }
  if (!store) return;
  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function tabs() {
    var nav = document.querySelector('nav.nav');
    var links = nav ? Array.prototype.slice.call(nav.querySelectorAll('a')) : [];
    return { links: links, current: links.findIndex(function (a) { return a.getAttribute('aria-current') === 'page'; }) };
  }

  var raw = null;
  try { raw = store.getItem(KEY); store.removeItem(KEY); } catch (e) { return; }

  // Tap: remember the tab we leave and the tab we go to. Plain left clicks only. One listener on the document, so it works from the head.
  document.addEventListener('click', function (ev) {
    if (ev.defaultPrevented || ev.button || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
    var a = ev.target.closest && ev.target.closest('nav.nav a');
    if (!a) return;
    var t = tabs(), i = t.links.indexOf(a);
    if (t.current < 0 || i < 0 || i === t.current) return;
    try { store.setItem(KEY, JSON.stringify({ from: t.current, to: i, at: Date.now() })); } catch (e) { /* storage full or blocked: no motion */ }
  });

  var done = false;
  function slide() {
    if (done) return;
    var t = tabs();
    if (!t.links.length) return;
    done = true;
    var stored = null;
    try { stored = JSON.parse(raw); } catch (e) { return; }
    var nt = (performance.getEntriesByType && performance.getEntriesByType('navigation')[0] || {}).type;
    var steps = slideSteps(stored, t.current, nt, Date.now(), reduced, t.links.length);
    var mark = t.current >= 0 && t.links[t.current].querySelector('.nav-mark');
    if (!steps || !mark || !mark.animate || getComputedStyle(mark).display === 'none') return;
    var dx = steps * t.links[t.current].getBoundingClientRect().width;
    mark.animate([{ transform: 'translateX(' + dx + 'px)' }, { transform: 'translateX(0)' }], { duration: 250, easing: 'cubic-bezier(.3,0,.2,1)' });
  }

  if (reduced || !raw) return;
  // Ask the real navigation: if the browser runs a view transition, the CSS does the slide. Otherwise slide here.
  // This script sits in the head, so it hears pagereveal before the first paint and the mark never shows in the wrong place.
  var revealed = false;
  if ('onpagereveal' in window) window.addEventListener('pagereveal', function (ev) { if (ev.viewTransition) { done = true; return; } revealed = true; slide(); });
  document.addEventListener('DOMContentLoaded', function () { if (!('onpagereveal' in window) || revealed) slide(); });
})();
