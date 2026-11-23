// Critical medicines: the table is plain HTML; this adds a filter by text, match type and status, and pages of rows.
const PAGE_SIZE = 12;
const rows = [...document.querySelectorAll('#eu-body tr[data-type]')];
const input = $('eu-q'), select = $('eu-type'), status = $('eu-status'), shown = $('eu-shown'), pager = $('eu-pager'), heading = $('eu-table-title');
let matching = rows, page = 1;
function pageButton(label, target, extra = {}) {
  const b = document.createElement('button');
  b.type = 'button'; b.textContent = label; b.dataset.page = target;
  if (extra.current) b.setAttribute('aria-current', 'page');
  if (extra.aria) b.setAttribute('aria-label', extra.aria);
  if (extra.disabled) b.disabled = true;
  return b;
}
function render() {
  const pages = pageCount(matching.length, PAGE_SIZE);
  page = clampPage(page, pages);
  const first = (page - 1) * PAGE_SIZE, visible = new Set(matching.slice(first, first + PAGE_SIZE));
  rows.forEach(tr => { tr.hidden = !visible.has(tr); });
  shown.textContent = matching.length ? `Showing ${first + 1}–${first + visible.size} of ${matching.length}${matching.length < rows.length ? ` (${rows.length} in all)` : ''}.` : 'No packages match.';
  pager.replaceChildren();
  pager.hidden = pages < 2;
  if (pages < 2) return;
  const list = document.createElement('div'); list.className = 'eu-pages';
  pageNumbers(page, pages).forEach(n => {
    if (n === '…') { const gap = document.createElement('span'); gap.textContent = n; gap.setAttribute('aria-hidden', 'true'); list.append(gap); }
    else list.append(pageButton(String(n), n, {current: n === page, aria: `Page ${n}`}));
  });
  pager.append(pageButton('Previous', page - 1, {disabled: page === 1}), list, pageButton('Next', page + 1, {disabled: page === pages}));
}
function filter() {
  const q = fold(input.value.trim()), type = select.value, when = status.value;
  matching = rows.filter(tr => (!type || tr.dataset.type === type) && (!when || tr.dataset.status === when) && (!q || fold(tr.dataset.text).includes(q)));
  page = 1;
  render();
}
// The pages are in English only; their content carries lang="en", so the page language the visitor chose stays on the menu and footer.
start();
if (input) {
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
  filter();
}
