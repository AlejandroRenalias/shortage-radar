// EU critical medicines pages (the list, one page for each code, the methods page).
// Every text is in the page in English and Finnish and the style sheet shows the one that matches <html lang>; a language change needs no reload.
// This script swaps what a span cannot hold (option labels, placeholders, aria-labels, SVG titles, the document title and description) and,
// on the list page, adds the filter by text, match type and status, and pages of rows. The table is plain HTML.
const PAGE_SIZE = 12;
const EU_COPY = {
  en: {showing: (from, to, n, all) => `Showing ${from}–${to} of ${n}${n < all ? ` (${all} in all)` : ''}.`, none: 'No packages match.', previous: 'Previous', next: 'Next', page: n => `Page ${n}`},
  fi: {showing: (from, to, n, all) => `Näytetään ${from}–${to} / ${n}${n < all ? ` (${all} yhteensä)` : ''}.`, none: 'Ei hakua vastaavia pakkauksia.', previous: 'Edellinen', next: 'Seuraava', page: n => `Sivu ${n}`},
};
const euText = () => EU_COPY[language === 'fi' ? 'fi' : 'en'];
function applyEuLanguage() {
  const l = language === 'fi' ? 'fi' : 'en', cap = l === 'fi' ? 'Fi' : 'En';
  document.querySelectorAll('[data-en][data-fi]').forEach(el => { el.textContent = el.dataset[l]; });
  document.querySelectorAll('[data-eu-attr]').forEach(el => el.dataset.euAttr.split(' ').forEach(name => { const value = el.getAttribute(`data-${l}-${name}`); if (value !== null) el.setAttribute(name, value); }));
  const head = document.querySelector('[data-title-en]');
  if (head && head.dataset) {
    document.title = head.dataset['title' + cap];
    const description = document.querySelector('meta[name="description"]');
    if (description) description.content = head.dataset['desc' + cap];
  }
}
let listReady = false, redrawList = () => {}, runFilter = () => {};
const input = $('eu-q');
if (input) {
  const select = $('eu-type'), status = $('eu-status'), shown = $('eu-shown'), pager = $('eu-pager'), heading = $('eu-table-title');
  const rows = [...document.querySelectorAll('#eu-body tr[data-type]')];
  const allowed = {match: [...select.options].map(o => o.value).filter(Boolean), status: [...status.options].map(o => o.value).filter(Boolean)};
  const start_ = listFromUrl(location.search, allowed);   // a reload or a shared link keeps the search, filters and page together
  input.value = start_.q; select.value = start_.match; status.value = start_.status;
  let matching = rows, page = start_.page;
  let reset = false;   // true once the visitor changes a filter: the next list starts at page 1
  const pageButton = (label, target, extra = {}) => {
    const b = document.createElement('button');
    b.type = 'button'; b.textContent = label; b.dataset.page = target;
    if (extra.current) b.setAttribute('aria-current', 'page');
    if (extra.aria) b.setAttribute('aria-label', extra.aria);
    if (extra.disabled) b.disabled = true;
    return b;
  };
  // replaceState keeps Back simple: one page of the list is one history entry, not a dozen.
  const syncUrl = () => {
    const search = listToUrl(location.search, {q: input.value, match: select.value, status: status.value, page});
    if (search !== location.search) history.replaceState(null, '', location.pathname + search + location.hash);
  };
  const render = () => {
    const pages = pageCount(matching.length, PAGE_SIZE), t = euText();
    page = clampPage(page, pages);
    syncUrl();
    const first = (page - 1) * PAGE_SIZE, visible = new Set(matching.slice(first, first + PAGE_SIZE));
    rows.forEach(tr => { tr.hidden = !visible.has(tr); });
    shown.textContent = matching.length ? t.showing(first + 1, first + visible.size, matching.length, rows.length) : t.none;
    pager.replaceChildren();
    pager.hidden = pages < 2;
    if (pages < 2) return;
    const list = document.createElement('div'); list.className = 'eu-pages';
    pageNumbers(page, pages).forEach(n => {
      if (n === '…') { const gap = document.createElement('span'); gap.textContent = n; gap.setAttribute('aria-hidden', 'true'); list.append(gap); }
      else list.append(pageButton(String(n), n, {current: n === page, aria: t.page(n)}));
    });
    pager.append(pageButton(t.previous, page - 1, {disabled: page === 1}), list, pageButton(t.next, page + 1, {disabled: page === pages}));
  };
  const filter = () => {
    const q = fold(input.value.trim()), type = select.value, when = status.value;
    matching = rows.filter(tr => (!type || tr.dataset.type === type) && (!when || tr.dataset.status === when) && (!q || fold(tr.dataset.text).includes(q) || searchMatches({substances: tr.dataset.text, substance_fi: tr.dataset.fi || ''}, input.value)));
    if (reset) page = 1;
    reset = true;
    render();
  };
  redrawList = render; runFilter = filter;
  if (matchMedia('(max-width:719px)').matches) $('eu-charts-fold').open = false;   // charts start closed on a phone, so the list is near the top
  [input, select, status].forEach(el => el.addEventListener(el === input ? 'input' : 'change', filter));
  pager.addEventListener('click', e => {
    const b = e.target.closest('button[data-page]');
    if (!b) return;
    page = +b.dataset.page; render();
    heading.focus({preventScroll: true}); heading.scrollIntoView({block: 'start'});   // the new page starts at the top of the list; focus follows, so the count is read out
  });
  // An open "i" note closes on Escape or a tap outside it.
  const closeInfo = except => document.querySelectorAll('details.eu-info[open]').forEach(d => { if (d !== except) d.open = false; });
  document.addEventListener('click', e => closeInfo(e.target.closest('details.eu-info')));
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeInfo(null); });
}
// A language change swaps the attributes and redraws the count line and the page buttons; the table is not rebuilt.
start(() => { applyEuLanguage(); if (listReady) redrawList(); });
loadSource().then(renderChrome).catch(() => {});
if (input) { runFilter(); listReady = true; }
