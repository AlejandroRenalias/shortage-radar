// Shortages: the full list with search, filters and sort. Everything is kept in the address, so a search can be shared.
// With the impact filter set to critical, the list shows one row for each medicine, which opens to its packages.
const PAGE_SIZE = 30;
let rows = [], filters = parseFilters(location.search), visible = PAGE_SIZE, loaded = false, urlTimer;
// Earlier packages for a search the current list cannot answer: 'idle' until needed, then 'loading', 'ready' or 'error'.
let past = {state: 'idle', rows: []};
function readControls() {
  filters.q = $('search').value.trim().slice(0, 100);
  filters.impact = document.querySelector('input[name="impact"]:checked').value;
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
// One row for a medicine without an interchangeable product: name and strengths, form, product names, and its packages inside.
function critRow(g, now) {
  const t = copy[language];
  return `<details class="crit-row"><summary><span class="pkg-icon" title="${esc(kindLabel(g.kind))}">${formIcon(g.kind, 40)}</span><span class="crit-id"><h2 class="crit-name">${esc([g.medicine, g.strength].filter(Boolean).join(' '))}</h2>`
    + `<span class="crit-form">${esc(g.form)}</span><span class="crit-names">${esc(g.names.join(', '))}</span></span><span class="crit-count">${esc(t.critPackages(g.packages.length))}</span>${uiIcon('chevron', 20).replace('class="uicon"', 'class="uicon crit-go"')}</summary>`
    + `<div class="pkg-list crit-packages">${g.packages.map(e => pkgCard(e, now, 3)).join('')}</div></details>`;
}
// Loads removed.json the first time a search finds nothing on the current list.
function loadPast() {
  if (past.state !== 'idle') return;
  past = {state: 'loading', rows: []};
  loadRemoved().then(d => { past = {state: 'ready', rows: d.events || []}; draw(); }).catch(() => { past = {state: 'error', rows: []}; draw(); });
}
function draw() {
  const t = copy[language], now = todayUTC(), grouped = filters.impact === 'critical';
  const found = sortPackages(filterPackages(rows, filters, now), filters.sort, now);
  const fallback = !found.length && Boolean(filters.q) && !activeFilters();
  if (fallback) loadPast();
  const earlier = fallback && past.state === 'ready' ? pastMatches(past.rows, filters.q) : [];
  const items = earlier.length ? earlier : grouped ? groupByMedicine(found) : found;
  const root = document.documentElement.dataset;
  if (filters.q) root.searching = 'true'; else delete root.searching;
  $('result-count').textContent = earlier.length ? t.pastCount(earlier.length) : grouped ? t.critCount(found.length, items.length) : t.count(found.length);
  $('list').className = grouped && !earlier.length ? 'crit-list' : 'pkg-list';
  const status = fallback && past.state === 'loading' ? `<p class="state" role="status">${esc(t.pastLoading)}</p>` : fallback && past.state === 'error' ? `<p class="state">${esc(t.pastError)}</p>` : '';
  const none = `<p class="state">${esc(filters.q ? t.empty : t.emptyFiltered)}</p>` + status;
  $('list').innerHTML = earlier.length ? `<p class="state past-note">${esc(t.pastNote)}</p>` + earlier.slice(0, visible).map(e => pastRow(e, 2)).join('')
    : items.slice(0, visible).map(x => grouped ? critRow(x, now) : pkgCard(x, now, 2)).join('') || none;
  $('more').hidden = visible >= items.length;
  $('more').parentElement.hidden = items.length <= PAGE_SIZE;
  $('more-count').textContent = items.length > PAGE_SIZE ? t.moreCount(Math.min(visible, items.length), items.length) : '';
  const critical = rows.filter(e => impactOf(e) === 'critical').length;
  $('crit-callout').hidden = grouped || !critical;
  $('crit-callout-text').textContent = t.critCallout(critical);
  $('crit-intro').hidden = !grouped;
  const n = activeFilters();
  $('filters-count').textContent = n ? ` (${n})` : '';
  $('clear').hidden = !n && !filters.sort;
}
function render() {
  if (!loaded) return;
  fillFilters(); $('search').value = filters.q; $('sort').value = filters.sort;
  document.querySelector(`input[name="status"][value="${filters.status}"]`).checked = true;
  document.querySelector(`input[name="impact"][value="${filters.impact}"]`).checked = true;
  draw();
}
function changed(resetPage = true) { if (past.state === 'error') past = {state: 'idle', rows: []}; readControls(); if (resetPage) visible = PAGE_SIZE; draw(); clearTimeout(urlTimer); urlTimer = setTimeout(syncUrl, 300); }
$('finder').addEventListener('submit', e => e.preventDefault());
$('search').addEventListener('input', () => changed());
$('finder').addEventListener('change', e => { if (e.target.id !== 'search') changed(); });
$('clear').addEventListener('click', () => { filters = {q: filters.q, impact: '', status: '', group: '', form: '', company: '', sort: ''}; render(); syncUrl(); });
$('crit-show').addEventListener('click', e => { e.preventDefault(); filters.impact = 'critical'; visible = PAGE_SIZE; render(); syncUrl(); });
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
