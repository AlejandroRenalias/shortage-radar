// Shortages: the full list with search, filters and sort. Everything is kept in the address, so a search can be shared.
const PAGE_SIZE = 30;
let rows = [], filters = parseFilters(location.search), visible = PAGE_SIZE, loaded = false, urlTimer;
function readControls() {
  filters.q = $('search').value.trim().slice(0, 100);
  filters.status = document.querySelector('input[name="status"]:checked').value;
  filters.group = $('f-group').value; filters.form = $('f-form').value; filters.company = $('f-company').value; filters.sort = $('sort').value;
}
function counts(key) { const map = new Map(); rows.forEach(e => { const k = key(e); if (k) map.set(k, (map.get(k) || 0) + 1); }); return map; }
function fillSelect(id, first, entries, value) {
  const el = $(id);
  el.innerHTML = `<option value="">${esc(first)}</option>` + entries.map(([v, label]) => `<option value="${esc(v)}">${esc(label)}</option>`).join('');
  el.value = entries.some(([v]) => v === value) ? value : '';
}
function fillFilters() {
  const t = copy[language], groups = counts(e => groupKey(e.atc)), forms = counts(e => formKind(e.form)), companies = counts(e => e.Company);
  fillSelect('f-group', t.anyGroup, [...groups].map(([k, n]) => [k, `${groupName(k === 'eye' ? 'S01' : k === 'ear' ? 'S02' : k)} (${numberText(n)})`]).sort((a, b) => a[1].localeCompare(b[1], language)), filters.group);
  fillSelect('f-form', t.anyForm, KINDS.filter(k => forms.has(k)).map(k => [k, `${kindLabel(k)} (${numberText(forms.get(k))})`]), filters.form);
  fillSelect('f-company', t.anyCompany, [...companies].map(([k]) => [k, k]).sort((a, b) => a[1].localeCompare(b[1], language)), filters.company);
}
function activeFilters() { return FILTER_KEYS.filter(k => filters[k]).length; }
function syncUrl() {
  try { const url = new URL(location.href); url.search = filtersToQuery(filters); history.replaceState(null, '', url); } catch (_) {}
}
function draw() {
  const t = copy[language], now = todayUTC();
  const found = sortPackages(filterPackages(rows, filters, now), filters.sort, now);
  $('result-count').textContent = t.count(found.length);
  $('list').innerHTML = found.slice(0, visible).map(e => pkgCard(e, now, 2)).join('') || `<p class="state">${esc(filters.q ? t.empty : t.emptyFiltered)}</p>`;
  $('more').hidden = visible >= found.length;
  $('more-count').textContent = found.length > PAGE_SIZE ? t.moreCount(Math.min(visible, found.length), found.length) : '';
  const n = activeFilters();
  $('filters-count').textContent = n ? ` (${n})` : '';
  $('clear').hidden = !n && !filters.sort;
}
function render() {
  if (!loaded) return;
  fillFilters(); $('search').value = filters.q; $('sort').value = filters.sort;
  document.querySelector(`input[name="status"][value="${filters.status}"]`).checked = true;
  draw();
}
function changed(resetPage = true) { readControls(); if (resetPage) visible = PAGE_SIZE; draw(); clearTimeout(urlTimer); urlTimer = setTimeout(syncUrl, 300); }
$('finder').addEventListener('submit', e => e.preventDefault());
$('search').addEventListener('input', () => changed());
$('finder').addEventListener('change', e => { if (e.target.id !== 'search') changed(); });
$('clear').addEventListener('click', () => { filters = {q: filters.q, status: '', group: '', form: '', company: '', sort: ''}; render(); syncUrl(); });
$('more').addEventListener('click', () => { visible += PAGE_SIZE; draw(); });
$('copy-link').addEventListener('click', () => {
  syncUrl();
  const done = () => { $('copy-status').textContent = copy[language].linkCopied; setTimeout(() => { $('copy-status').textContent = ''; }, 2500); };
  if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(location.href).then(done, () => {});
});
// The filter panel starts open on wide screens and whenever a filter is already set.
$('filters').open = matchMedia('(min-width: 760px)').matches || FILTER_KEYS.some(k => filters[k]) || Boolean(filters.sort);
start(render);
loadCurrent().then(d => { rows = relevant(d.events); loaded = true; renderChrome(d); render(); }).catch(showLoadError);
