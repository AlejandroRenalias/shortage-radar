// Group: one substitution group of interchangeable packages, from its code in the address (group.html?g=0733).
// The data comes from one small file for the last two digits of the code (g/NN.json), not from the whole archive. Today only: no history.
function codeFromSearch(search) { try { return (new URLSearchParams(search).get('g') || '').trim().slice(0, 8); } catch (_) { return ''; } }
function validCode(c) { return /^\d{4}$/.test(c); }
let code = '', shard = null;
const ROWS_SHOWN = 8;
// The title of a group in words: active substance, strength and form of the register.
function groupTitle(h) {
  const form = formText(h.form).toLocaleLowerCase(language);
  return [[h.substance, strengthText({strength: h.strength})].filter(Boolean).join(' '), form].filter(Boolean).join(', ');
}
// The label of the other interchangeable packages found in the data, and where they come from. Facts only.
function altMarkup(g) {
  const t = copy[language], n = g.counts.alternatives, label = n === 0 ? t.grpAlt0 : n === 1 ? t.grpAlt1 : t.grpAltMany(n);
  const from = n > 0 && g.alt_companies.length === 1 ? `<p class="grp-from">${esc(t.grpAllFrom(g.alt_companies[0]))}</p>` : '';
  return `<div class="panel grp-alt"><p class="grp-alt-label">${esc(label)}</p>${from}</div>`;
}
function rowMarkup(p) {
  const t = copy[language], spec = [packText(p), p.company].filter(Boolean);
  const vnr = p.link ? `<a href="medicine.html?vnr=${encodeURIComponent(p.link)}">${esc(p.vnr)}</a>` : esc(p.vnr);
  const mark = p.listed ? `<p class="grp-mark grp-on">${uiIcon('now', 18)}<span>${esc(t.grpOnList)}</span></p>` : `<p class="grp-mark grp-off"><span>${esc(t.grpOffList)}</span></p>`;
  return `<li class="grp-row${p.listed ? ' is-listed' : ''}">${mark}<p class="grp-name">${esc(nameWithStrength(p) || p.name)}</p>`
    + (spec.length ? `<p class="grp-spec">${spec.map(x => `<span>${esc(x)}</span>`).join('')}</p>` : '') + `<p class="grp-vnr"><span>${esc(t.vnr)}</span> ${vnr}</p></li>`;
}
// Packages on the shortage list come first (the data is in that order). A long group shows the listed ones and the first others; the rest opens on request.
function rowsMarkup(packages) {
  const t = copy[language], listed = packages.filter(p => p.listed), others = packages.filter(p => !p.listed);
  const shown = listed.concat(others.slice(0, ROWS_SHOWN)), rest = others.slice(ROWS_SHOWN);
  return `<ul class="grp-list">${shown.map(rowMarkup).join('')}</ul>`
    + (rest.length ? `<details class="alts-more grp-more"><summary>${esc(t.altAll(packages.length))}</summary><ul class="grp-list">${rest.map(rowMarkup).join('')}</ul></details>` : '');
}
// The same two lines on every group page: not a stock check, and the dates that this page is made from.
function footMarkup(d) {
  const t = copy[language], register = sourceDays(d.source_metadata || {}).register;
  return `<div class="grp-foot"><p class="grp-stock">${esc(t.grpStock)}</p><p class="source-note">${esc(t.grpCoverage(dateText(d.snapshot_date), register ? dateText(register) : t.dateUnknown))}</p></div>`;
}
function back() { return `<a class="back" href="shortages.html">${uiIcon('back', 18)}<span>${esc(copy[language].medBack)}</span></a>`; }
function foundMarkup(g, d) {
  const t = copy[language], c = g.counts;
  return `${back()}<div class="grp-page"><h1 class="grp-title">${esc(groupTitle(g.heading))}</h1><p class="grp-code">${esc(t.grpCode(code))}</p>`
    + `<p class="grp-summary">${esc(t.grpSummary(c.market, c.listed, c.alternatives, c.companies))}</p>${altMarkup(g)}`
    + `<section aria-labelledby="grp-packages"><h2 id="grp-packages">${esc(t.grpPackages)}</h2>${rowsMarkup(g.packages)}</section>${footMarkup(d)}</div>`;
}
// A code that is not on the list today, or not a code at all: a short neutral page, with no data of the group.
function unknownMarkup(d) {
  const t = copy[language];
  return `${back()}<div class="grp-page"><h1 class="grp-title">${esc(validCode(code) ? t.grpCode(code) : t.grpPackages)}</h1><p class="grp-summary">${esc(t.grpUnknown)}</p>`
    + `<p><a href="shortages.html">${esc(t.nfSearch)}</a></p>${footMarkup(d)}</div>`;
}
function render() {
  const t = copy[language], root = $('group');
  if (!shard) return;
  const g = validCode(code) ? (shard.groups || {})[code] : null;
  document.title = g ? `${groupTitle(g.heading)} | ${t.brand}` : t.title_group;
  root.innerHTML = g ? foundMarkup(g, shard) : unknownMarkup(shard);
}
if (typeof document !== 'undefined' && document.documentElement.dataset && document.documentElement.dataset.page === 'group') {
  code = codeFromSearch(location.search);
  start(render);
  // The page's own small file; a code that cannot be a group code loads the small source file only, for the dates.
  fetchJson(validCode(code) ? `g/${code.slice(-2)}.json` : 'source.json').then(d => { shard = d; renderChrome(d); render(); }).catch(showLoadError);
}
