// Home for everyone: one question, one search box and one answer card for each matching package.
// A card has exactly one of three states: Fimea lists a shortage, not on Fimea's list now, or the name was not found.
// The page says nothing about stock, other packages or what to do with a medicine; each card ends with one next step.
const SHOWN = 5;
let currentRows = null, pastRows = null, snapshotDate = '', query = '', shown = SHOWN, typing;

const byName = (a, b) => (a.name || '').localeCompare(b.name || '', language) || (a.strength || '').localeCompare(b.strength || '', language, {numeric: true}) || (a.NordicArticleNumber || '').localeCompare(b.NordicArticleNumber || '');
// The newest ended notice of each package (one card for a package, whatever its history), for packages that are not on the list now.
function latestPast(rows, listed) {
  const latest = new Map();
  for (const e of rows) {
    if (listed.has(e.NordicArticleNumber)) continue;
    const old = latest.get(e.NordicArticleNumber);
    if (!old || (e.removed_on || '') > (old.removed_on || '')) latest.set(e.NordicArticleNumber, e);
  }
  return [...latest.values()];
}
// What to show for a typed name: the packages on the list now, then the packages that left it. The exact search comes first;
// a tolerant match on names runs only when the exact search finds nothing in either list.
function answerFor(text, now, past) {
  const q = String(text || '').trim();
  if (!q) return [];
  const listed = new Set(now.map(e => e.NordicArticleNumber)), ended = latestPast(past, listed);
  let a = now.filter(e => searchMatches(e, q)), b = ended.filter(e => searchMatches(e, q));
  if (!a.length && !b.length) { a = now.filter(e => fuzzyMatches(e, q)); b = ended.filter(e => fuzzyMatches(e, q)); }
  const items = [...a.sort(byName).map(e => ({state: 'shortage', e})), ...b.sort(byName).map(e => ({state: 'notlisted', e}))];
  return items.length ? items : [{state: 'notfound'}];
}
const stateLine = (icon, text) => `<p class="pt-state">${uiIcon(icon, 26)}<span>${esc(text)}</span></p>`;
function packageHead(e, id) {
  const t = copy[language], pack = packText(e);
  return `<h3 class="pt-name" id="${id}">${esc(nameWithStrength(e) || t.unavailable)}</h3>` + (pack ? `<p class="pt-pack">${esc(pack)}</p>` : '');
}
// The source line of every card carries the data date of the list, not the date of the visit.
const sourceLine = () => `<p class="pt-source">${esc(copy[language].ptSource(dateText(snapshotDate)))}</p>`;
function cardMarkup(item, i) {
  const t = copy[language], id = `pt-card-${i}`;
  if (item.state === 'notfound') return `<article class="pt-card pt-notfound">${stateLine('unknown', t.ptNotFound)}<p class="pt-next">${esc(t.ptNotFoundNext)}</p>${sourceLine()}</article>`;
  const e = item.e;
  if (item.state === 'shortage') {
    return `<article class="pt-card pt-shortage" aria-labelledby="${id}">${stateLine('now', t.ptShortage)}${packageHead(e, id)}`
      + `<dl class="pt-dates"><div><dt>${esc(t.ptStartLabel)}</dt><dd>${esc(dateText(e.UnavailableFrom))}</dd></div><div><dt>${esc(t.ptEndLabel)}</dt><dd>${e.EndingDate ? esc(dateText(e.EndingDate)) : esc(t.notKnown)}</dd></div></dl>`
      + `<p class="pt-next">${esc(t.ptShortageNext)}</p>${sourceLine()}</article>`;
  }
  return `<article class="pt-card pt-notlisted" aria-labelledby="${id}">${stateLine('info', t.ptNotListed)}${packageHead(e, id)}`
    + `<p class="pt-earlier">${esc(t.ptEarlier(dateText(e.last_seen)))} ${esc(t.pastNote)}</p><p class="pt-next">${esc(t.ptNotListedNote)}</p>${sourceLine()}</article>`;
}
function render() {
  const box = $('pt-results'), ready = Boolean(currentRows && pastRows);
  $('loading').hidden = !query || ready || !$('load-error').hidden;
  if (!query || !ready) { box.innerHTML = ''; $('pt-more-row').hidden = true; return; }
  const items = answerFor(query, currentRows, pastRows);
  box.innerHTML = items.slice(0, shown).map(cardMarkup).join('');
  $('pt-more-row').hidden = shown >= items.length;
}
function readQuery(text, fromSubmit) {
  const next = String(text || '').trim().slice(0, 100);
  if (next !== query) shown = SHOWN;
  query = fromSubmit || next.length >= 2 ? next : '';
  try { const url = new URL(location.href); if (query) url.searchParams.set('q', query); else url.searchParams.delete('q'); history.replaceState(null, '', url); } catch (_) {}
  render();
}
if (typeof document !== 'undefined' && document.documentElement.dataset && document.documentElement.dataset.page === 'index') {
  const input = $('q');
  input.value = queryFromUrl(location.search);
  query = input.value.trim();
  $('pt-form').addEventListener('submit', e => { e.preventDefault(); clearTimeout(typing); readQuery(input.value, true); input.blur(); $('pt-results').scrollIntoView({block: 'nearest'}); });
  input.addEventListener('input', () => { clearTimeout(typing); typing = setTimeout(() => readQuery(input.value, false), 350); });
  $('pt-more').addEventListener('click', () => { shown += SHOWN; render(); });
  start(render);
  loadCurrent().then(d => { currentRows = relevant(d.events); snapshotDate = d.snapshot_date; renderChrome(d); render(); }).catch(showLoadError);
  loadRemoved().then(d => { pastRows = d.events || []; render(); }).catch(() => { pastRows = []; render(); });
}
