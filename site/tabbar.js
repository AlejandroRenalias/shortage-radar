// Tab bar motion. The green mark slides from the old tab to the new one.
// A tap stores the old and new tab in sessionStorage. The next page reads it in the head, before the first paint,
// and sets --sr-steps on <html>. The slide itself is a CSS animation on the real mark (see style.css), so the bar
// is never covered by a transition layer and every tap during the slide navigates.
(function () {
  var KEY = 'sr-tab-from';
  var MAX_AGE = 5000;   // a saved tap older than this is ignored
  var CLEAR_AFTER = 1500; // the tapping page drops its own saved tap if it is still alive after this: the navigation did not happen

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
  var root = document.documentElement;
  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function tabs() {
    var nav = document.querySelector('nav.nav');
    var links = nav ? Array.prototype.slice.call(nav.querySelectorAll('a')) : [];
    return { links: links, current: links.findIndex(function (a) { return a.getAttribute('aria-current') === 'page'; }) };
  }

  var raw = null;
  try { raw = store.getItem(KEY); store.removeItem(KEY); } catch (e) { return; }

  // Tap: remember the tab we leave, the tab we go to and its path. Plain left clicks only.
  document.addEventListener('click', function (ev) {
    if (ev.defaultPrevented || ev.button || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
    var a = ev.target.closest && ev.target.closest('nav.nav a');
    if (!a) return;
    var t = tabs(), i = t.links.indexOf(a);
    if (t.current < 0 || i < 0 || i === t.current) return;
    try {
      store.setItem(KEY, JSON.stringify({ from: t.current, to: i, path: a.pathname, at: Date.now() }));
      // If this page is still here a moment later, the tap never became a navigation: forget it.
      setTimeout(function () { try { store.removeItem(KEY); } catch (e) { /* ignore */ } }, CLEAR_AFTER);
    } catch (e) { /* storage full or blocked: no motion */ }
  });

  if (reduced || !raw) return;
  var stored = null;
  try { stored = JSON.parse(raw); } catch (e) { return; }
  if (!stored || typeof stored.path !== 'string' || stored.path !== location.pathname) return;
  var nt = (performance.getEntriesByType && performance.getEntriesByType('navigation')[0] || {}).type;
  var steps = slideSteps(stored, stored.to, nt, Date.now(), false, 5);
  if (!steps) return;
  // Set before the first paint, so the mark starts at the old tab and never shows in the wrong place.
  root.style.setProperty('--sr-steps', String(steps));
  root.classList.add('sr-slide');
  // Once the bar exists, check that this page really is the target tab. If not, drop the slide.
  document.addEventListener('DOMContentLoaded', function () {
    if (tabs().current !== stored.to) root.classList.remove('sr-slide');
  });
})();
