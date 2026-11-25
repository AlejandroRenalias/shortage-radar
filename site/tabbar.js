// Tab bar motion. The green mark slides from the old tab to the new one.
// Browsers with cross-document View Transitions do it in CSS (see style.css).
// Other browsers use the fallback here: a tap stores the old tab in sessionStorage and the next page animates the mark (transform only).
(function () {
  var KEY = 'sr-tab-from';
  var MAX_AGE = 5000;

  // Pure: returns the tab-width steps to start from (old index minus new index), or 0 for no slide.
  function slideSteps(stored, current, navType, now, reduced, tabs) {
    if (reduced || !stored || navType !== 'navigate') return 0;
    if (typeof stored.from !== 'number' || typeof stored.at !== 'number') return 0;
    if (stored.from === current || stored.from < 0 || stored.from >= tabs || current < 0 || current >= tabs) return 0;
    var age = now - stored.at;
    if (age < 0 || age > MAX_AGE) return 0;
    return stored.from - current;
  }

  if (typeof module !== 'undefined' && module.exports) { module.exports = { slideSteps: slideSteps }; return; }

  var nav = document.querySelector('nav.nav');
  if (!nav) return;
  var links = Array.prototype.slice.call(nav.querySelectorAll('a'));
  var current = links.findIndex(function (a) { return a.getAttribute('aria-current') === 'page'; });
  var store = null;
  try { store = window.sessionStorage; } catch (e) { store = null; }
  if (!store) return;

  var native = typeof window.CSSViewTransitionRule !== 'undefined';
  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var raw = null;
  try { raw = store.getItem(KEY); store.removeItem(KEY); } catch (e) { return; }

  // Tap: remember the tab we leave. Plain left clicks only.
  nav.addEventListener('click', function (ev) {
    if (ev.defaultPrevented || ev.button || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
    var a = ev.target.closest && ev.target.closest('a');
    var i = links.indexOf(a);
    if (current < 0 || i < 0 || i === current) return;
    try { store.setItem(KEY, JSON.stringify({ from: current, at: Date.now() })); } catch (e) { /* storage full or blocked: no motion */ }
  });

  if (native || reduced || !raw || current < 0) return;
  var stored = null;
  try { stored = JSON.parse(raw); } catch (e) { return; }
  var nt = (performance.getEntriesByType && performance.getEntriesByType('navigation')[0] || {}).type;
  var steps = slideSteps(stored, current, nt, Date.now(), reduced, links.length);
  var mark = links[current].querySelector('.nav-mark');
  if (!steps || !mark || !mark.animate || getComputedStyle(mark).display === 'none') return;
  var dx = steps * links[current].getBoundingClientRect().width;
  mark.animate([{ transform: 'translateX(' + dx + 'px)' }, { transform: 'translateX(0)' }], { duration: 250, easing: 'cubic-bezier(.3,0,.2,1)' });
})();
