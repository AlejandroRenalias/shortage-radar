// Medicines: one page for a verified group of register packages, from its id in the address (medicines.html?id=...).
// The data comes from one small file for the id (m/<id>.json). What the page may say is set in docs/medicine-groups-spec.md:
// the packages share register fields, and that is all. Each package keeps its own notices, source and history; nothing here
// says that one package can replace another, or that any package is in stock.
function idFromSearch(search) { try { return (new URLSearchParams(search).get('id') || '').trim().slice(0, 20); } catch (_) { return ''; } }
function validId(v) { return /^m[0-9a-f]{12}$/.test(v); }
let medicineId = '', page = null;
const noticeStatus = e => e.removed_on ? 'left' : statusOf(e);
// What Fimea's register gives for the packages on this page. The route, the form and the container are Fimea's own words, in Finnish.
function registerMarkup(m) {
  const t = copy[language];
  const rows = [[t.substance, (m.substances || []).join(', ')], [t.strength, strengthText(m)], [t.form, formText(m.form)], [t.formRaw, m.form], [t.mdRoute, (m.routes || []).join(', ')], ['ATC', m.atc], [t.mdContainer, m.container], [t.mdUnit, m.unit_size], [t.mdDevice, m.device]];
  return `<section class="panel md-src md-src-fimea" aria-labelledby="md-reg"><h2 id="md-reg">${esc(t.mdRegisterTitle)}</h2><dl class="details md-dl">${rows.filter(([, v]) => v).map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join('')}</dl>`
    + `<p class="note md-ours">${esc(t.mdReading)}</p></section>`;
}
// Our reading of one notice: its status line and its timeline, with the stretches that were not observed.
function readingMarkup(e) {
  const t = copy[language], status = noticeStatus(e);
  const line = {now: t.medNow, soon: t.medSoon, unknown: t.medUnknown, left: t.medLeftText(dateText(e.last_seen))}[status];
  return `<p class="status-line">${esc(line)}</p>${timelineMarkup(e, status === 'left', {bare: true, level: 5})}`;
}
function factsMarkup(e, vnr, withPack) {
  const t = copy[language];
  const rows = [[t.vnr, vnr], withPack ? [t.pack, packText(e)] : null, [t.company, e.Company], [t.reported, e.DateOfTheNotification ? dateText(e.DateOfTheNotification) : '']].filter(Boolean);
  return `<dl class="details md-dl">${rows.filter(([, v]) => v).map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join('')}</dl>`;
}
// One package: the newest notice in full, earlier or other notices of the same package folded under it.
function packageMarkup(pkg) {
  const t = copy[language], [first, ...rest] = pkg.events, status = noticeStatus(first), id = `pk-${pkg.vnr}`;
  const tab = status === 'left' ? [t.medLeft, 'ended'] : [statusLabel(status), status === 'soon' ? 'soon' : status === 'unknown' ? 'unknown' : 'now'];
  const more = rest.length ? `<details class="md-more"><summary>${esc(t.mdOtherNotices(rest.length))}</summary>${rest.map(e => `<div class="md-notice"><p class="md-notice-head"><strong>${esc(t.reported)}: ${esc(e.DateOfTheNotification ? dateText(e.DateOfTheNotification) : '—')}</strong>${e.Company ? `<span>${esc(e.Company)}</span>` : ''}</p>${readingMarkup(e)}</div>`).join('')}</details>` : '';
  return `<article class="panel med-pkg is-${status}" aria-labelledby="${id}"><p class="pkg-tab md-tab pkg-${status === 'left' ? 'ended' : status}">${uiIcon(tab[1], 18)}<span>${esc(tab[0])}</span></p>`
    + `<h3 id="${id}" class="med-pkg-name">${esc(packText(first) || `${t.vnr} ${pkg.vnr}`)}</h3><p class="md-link"><a href="medicine.html?vnr=${esc(pkg.vnr)}">${esc(t.mdPackagePage)}</a></p>`
    + `<section class="md-src md-src-fimea" aria-label="${esc(t.mdFimea)}"><h4>${esc(t.mdFimea)}</h4>${factsMarkup(first, pkg.vnr, true)}</section>`
    + `<section class="md-src md-src-ours" aria-label="${esc(t.mdOurs)}"><h4>${esc(t.mdOurs)}</h4>${readingMarkup(first)}${more}</section></article>`;
}
function notFound(root) {
  const t = copy[language];
  document.title = `${t.mdNfTitle} | ${t.brand}`;
  root.innerHTML = `<section class="not-found"><a class="back" href="shortages.html">${uiIcon('back', 18)}<span>${esc(t.medBack)}</span></a><h1>${esc(t.mdNfTitle)}</h1><p class="lead">${esc(t.mdNfText)}</p>`
    + `<form class="bigsearch" action="shortages.html" method="get" role="search"><label for="q">${esc(t.homeSearchLabel)}</label><div class="searchrow">${uiIcon('search', 22)}<input id="q" name="q" type="search" autocomplete="off" maxlength="100" placeholder="${esc(t.placeholder)}"><button type="submit" class="btn">${esc(t.searchButton)}</button></div><p class="hint">${esc(t.hint)}</p></form>`
    + `<p><a href="shortages.html">${esc(t.nfSearch)}</a></p></section>`;
}
function render() {
  const t = copy[language], root = $('medicines');
  if (!page) return;
  if (page.missing) return notFound(root);
  const m = page.medicine, title = nameWithStrength(m) || t.unavailable;
  document.title = `${title} | ${t.brand}`;
  root.innerHTML = `<a class="back" href="shortages.html">${uiIcon('back', 18)}<span>${esc(t.medBack)}</span></a><div class="med-single"><h1 class="md-title">${esc(title)}</h1>`
    + `<p class="md-sub">${[formText(m.form), (m.substances || []).join(', ')].filter(Boolean).map(x => `<span>${esc(x)}</span>`).join('')}</p>`
    + registerMarkup(m)
    + `<section aria-labelledby="md-pk"><h2 id="md-pk">${esc(t.mdPackagesTitle)}</h2><p class="note">${esc(t.mdPackagesNote)}</p><div class="med-pkgs">${page.packages.map(packageMarkup).join('')}</div></section>`
    + `<p class="source-note">${esc(t.mdSourceNote(dateText(page.snapshot_date)))} <a href="https://fimea.fi/en/about_us/open-data">${esc(t.sourceLink)}</a></p></div>`;
}
// A missing file is an unknown address, not a load error.
const loadPage = id => fetch(`m/${id}.json`).then(r => r.status === 404 ? null : r.ok ? r.json() : Promise.reject(Error(id)));
if (typeof document !== 'undefined' && document.documentElement.dataset && document.documentElement.dataset.page === 'medicines') {
  medicineId = idFromSearch(location.search);
  start(render);
  (validId(medicineId) ? loadPage(medicineId) : Promise.resolve(null)).then(d => d || fetchJson('summary.json').then(s => ({missing: true, snapshot_date: s.snapshot_date, source_metadata: s.source_metadata, generated_at: s.generated_at, last_checked: s.last_checked})))
    .then(d => { page = d; renderChrome(d); render(); }).catch(showLoadError);
}
