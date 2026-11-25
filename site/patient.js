// Home for everyone: one question, one search box and one answer card for each matching package.
// A card has exactly one of three states: Fimea lists a shortage, not on Fimea's list now, or the name is not in the register.
// "Not on Fimea's list now" covers a package that left the list and a name that the register has but that was never on the list (names.json, built from the register).
// The page says nothing about stock, other packages or what to do with a medicine; each card ends with one next step.
const SHOWN = 5;
let currentRows = null, pastRows = null, registerNames = null, snapshotDate = '', query = '', shown = SHOWN, typing;

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
// The names of the register that no card of the lists already carries, as entries for the same search: trade names first, then active substances.
// A substance is shown only when nothing else was found, because a substance that has packages on or near the list must not read as "not on the list".
const EMPTY_NAMES = {};
const registerEntryCache = new WeakMap();
function registerEntries(names, taken, withSubstances) {
  let entries = registerEntryCache.get(names);
  if (!entries) registerEntryCache.set(names, entries = {trade: (names.names || []).map(name => ({name})), substances: (names.substances || []).map(name => ({name}))});
  const fresh = list => list.filter(e => !taken.has(fold(e.name)));
  return {trade: fresh(entries.trade), substances: withSubstances ? fresh(entries.substances) : []};
}
// What to show for a typed name: the packages on the list now, then the packages that left it, then the register names that were never on the list.
// The exact search comes first; a tolerant match on names runs only when the exact search finds nothing in any of them.
// `names` is the name index ({names, substances}); without it a name that is not on the lists cannot be told from a name that is not in the register.
function answerFor(text, now, past, names) {
  const q = String(text || '').trim();
  if (!q) return [];
  const listed = new Set(now.map(e => e.NordicArticleNumber)), ended = latestPast(past, listed);
  const look = match => {
    const a = now.filter(e => match(e, q)).sort(byName), b = ended.filter(e => match(e, q)).sort(byName);
    const taken = new Set([...a, ...b].map(e => fold(e.name)));
    const known = registerEntries(names || EMPTY_NAMES, taken, !a.length && !b.length);
    const r = [...known.trade, ...known.substances].filter(e => match(e, q));
    return [...a.map(e => ({state: 'shortage', e})), ...b.map(e => ({state: 'notlisted', e})), ...r.map(e => ({state: 'registered', e}))];
  };
  const items = look(searchMatches), result = items.length ? items : look(fuzzyMatches);
  return result.length ? result : [{state: 'notfound'}];
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
  if (item.state === 'notfound') return `<article class="pt-card pt-notfound">${stateLine('unknown', t.ptNotFound)}<p class="pt-earlier">${esc(t.ptNotFoundNote)}</p><p class="pt-next">${esc(t.ptNotFoundNext)}</p>${sourceLine()}</article>`;
  const e = item.e;
  if (item.state === 'registered') return `<article class="pt-card pt-notlisted" aria-labelledby="${id}">${stateLine('info', t.ptNotListed)}<h3 class="pt-name" id="${id}">${esc(e.name)}</h3><p class="pt-next">${esc(t.ptNotListedNote)}</p>${sourceLine()}</article>`;
  if (item.state === 'shortage') {
    return `<article class="pt-card pt-shortage" aria-labelledby="${id}">${stateLine('now', t.ptShortage)}${packageHead(e, id)}`
      + `<dl class="pt-dates"><div><dt>${esc(t.ptStartLabel)}</dt><dd>${esc(dateText(e.UnavailableFrom))}</dd></div><div><dt>${esc(t.ptEndLabel)}</dt><dd>${e.EndingDate ? esc(dateText(e.EndingDate)) : esc(t.notKnown)}</dd></div></dl>`
      + `<p class="pt-next">${esc(t.ptShortageNext)}</p>${sourceLine()}</article>`;
  }
  return `<article class="pt-card pt-notlisted" aria-labelledby="${id}">${stateLine('info', t.ptNotListed)}${packageHead(e, id)}`
    + `<p class="pt-earlier">${esc(t.ptEarlier(dateText(e.last_seen)))} ${esc(t.pastNote)}</p><p class="pt-next">${esc(t.ptNotListedNote)}</p>${sourceLine()}</article>`;
}
// The name index loads on the first search, so a visit without a search does not pay for it. If it cannot load, the page shows the load error, never "not in the register".
let namesStarted = false;
function ensureNames() {
  if (namesStarted) return;
  namesStarted = true;
  loadNames().then(d => { registerNames = d; render(); }).catch(() => { namesStarted = false; showLoadError(); });
}
function render() {
  if (query) ensureNames();
  const box = $('pt-results'), ready = Boolean(currentRows && pastRows && registerNames);
  $('loading').hidden = !query || ready || !$('load-error').hidden;
  if (!query || !ready) { box.innerHTML = ''; $('pt-more-row').hidden = true; return; }
  const items = answerFor(query, currentRows, pastRows, registerNames);
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
