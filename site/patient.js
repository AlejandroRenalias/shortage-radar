// Home for everyone: one question, one search box and one answer card for each matching package.
// A card has one of these states: Fimea lists a shortage, not on Fimea's list now, the name is not in the register, or (for a typing mistake) "Did you mean" with names only.
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
// A trade name is "Name|strength|strength" in the index; its entry has the name and its strengths. A substance is shown only when nothing else was found,
// because a substance that has packages on or near the list must not read as "not on the list".
const registerEntryCache = new WeakMap();
// The first letters of the words of a name: the entries of the index are grouped by them, so a search looks at the names that can start with the typed word and not at all of them.
function wordStarts(name) {
  const hay = fold(name), starts = new Set();
  for (let i = 0; i < hay.length; i++) if (i === 0 || !/[\p{L}\p{N}]/u.test(hay[i - 1])) starts.add(hay[i]);
  return starts;
}
function groupByStart(list) {
  const groups = new Map();
  for (const e of list) for (const c of wordStarts(e.name)) { if (!groups.has(c)) groups.set(c, []); groups.get(c).push(e); }
  return {all: list, groups};
}
function registerEntries(names) {
  let entries = registerEntryCache.get(names);
  if (!entries) registerEntryCache.set(names, entries = {
    trade: groupByStart((names.names || []).map(row => { const [name, ...strengths] = row.split('|'); return {name, strengths}; })),
    substances: groupByStart((names.substances || []).map(name => ({name, strengths: []})))
  });
  return entries;
}
// The entries of a group that can match the typed label: a name matches only if the first typed word (or one of its aliases) starts one of its words.
function candidates(group, parsed) {
  const found = new Set();
  for (const part of parsed.parts) {
    if (!part.words.length) continue;
    for (const term of termsFor(part.words[0])) for (const e of group.groups.get(term[0]) || []) found.add(e);
  }
  return [...found];
}
const SUGGESTED = 5;
// The label of a near entry: its name, with the typed strength when the entry has it.
const labelOf = (e, parsed) => parsed.strength && matchedStrength(e, parsed.strength) ? `${e.name} ${strengthText({strength: matchedStrength(e, parsed.strength)})}`.trim() : e.name;
// "Did you mean" labels for a typed label that is not an exact label, the nearest first. Only labels are offered, never a card: a typing mistake is never answered
// with a statement about a shortage or about the list. A typed strength that no near entry has is dropped from the comparison.
function suggestionsFor(parsed, rows, entries) {
  const all = [...rows, ...entries], out = new Map();
  const add = label => { if (!out.has(fold(label))) out.set(fold(label), label); };
  // The name is in the register but not with this strength ("Panadol 999 mg"): offer the strengths it has.
  if (parsed.strength) {
    const labels = [];
    for (const e of all.filter(e => labelMatches(e, {words: parsed.words, strength: ''}))) for (const strength of e.strengths && e.strengths.length ? e.strengths : [e.strength]) if (strength) labels.push(`${e.name} ${strengthText({strength})}`.trim());
    labels.sort((x, y) => x.localeCompare(y, language, {numeric: true})).forEach(add);
  }
  // A name that is on or was on the shortage list ranks before a register name that is as near, so a mistyped name never hides a package that is short.
  const near = p => all.map(e => [fuzzyScore(e, p), e]).filter(([score]) => score !== null).map(([score, e]) => [score - (e.NordicArticleNumber ? 0.1 : 0), e]).sort((x, y) => x[0] - y[0] || x[1].name.localeCompare(y[1].name, language));
  let found = near(parsed);
  if (!found.length && parsed.strength && !out.size) found = near({words: parsed.words, strength: ''});
  for (const [, e] of found) add(labelOf(e, parsed));
  return [...out.values()].slice(0, SUGGESTED);
}
// What to show for a typed name: the packages on the list now, then the packages that left it, then the register names that were never on the list.
// A typed label is exact when each word starts a word of a name or substance and the strength, if typed, is exactly one the entry has (normalizeStrength in lib.js).
// When it is not (a typing mistake, a word from the middle of another name, a strength that does not exist), the answer is "Did you mean" with near names, and no statement about the typed text.
// `names` is the name index ({names, substances}); without it (it could not load) a name that is not on the lists is neither "not on the list" nor "not in the register": the card says it could not be checked.
function answerFor(text, now, past, names) {
  const q = String(text || '').trim();
  if (!q) return [];
  const parsed = parseLabel(q), listed = new Set(now.map(e => e.NordicArticleNumber)), ended = latestPast(past, listed);
  // Cards come only from an exact label (see above), or from a typed package number (VNR). A word from the middle of a name ("asmin" in "Yasmin") or a typing mistake gets no card.
  const exact = /^\d{6}$/.test(q) ? e => e.NordicArticleNumber === q : e => labelMatches(e, parsed);
  const a = now.filter(exact).sort(byName), b = ended.filter(exact).sort(byName);
  const taken = new Set([...a, ...b].map(e => fold(e.name)));
  const entries = names ? registerEntries(names) : {trade: {all: [], groups: new Map()}, substances: {all: [], groups: new Map()}};
  const match = e => ({e, m: labelMatch(e, parsed)});
  const trade = candidates(entries.trade, parsed).filter(e => !taken.has(fold(e.name))).map(match).filter(x => x.m).sort((x, y) => x.e.name.localeCompare(y.e.name, language));
  // A substance is shown only when nothing else matched the label exactly.
  const substances = a.length || b.length || trade.length ? [] : candidates(entries.substances, parsed).map(match).filter(x => x.m);
  const registered = [...trade, ...substances].map(({e, m}) => ({state: 'registered', e: {name: m.strength ? `${e.name} ${strengthText({strength: m.strength})}`.trim() : e.name, base: e.name, matched: m.strength}}));
  const items = [...a.map(e => ({state: 'shortage', e})), ...b.map(e => ({state: 'notlisted', e})), ...registered];
  if (!items.length) {
    const labels = suggestionsFor(parsed, [...now, ...ended], [...entries.trade.all, ...entries.substances.all]);
    if (labels.length) items.push({state: 'suggest', labels});
  }
  return items.length ? items : [{state: names ? 'notfound' : 'unchecked'}];
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
  if (item.state === 'suggest') return `<article class="pt-card pt-suggest">${stateLine('unknown', t.ptDidYouMean)}<ul class="pt-suggest-list">${item.labels.map(label => `<li><button type="button" class="btn-quiet" data-pt-query="${esc(label)}">${esc(label)}</button></li>`).join('')}</ul>${sourceLine()}</article>`;
  if (item.state === 'unchecked') return `<article class="pt-card pt-notfound">${stateLine('unknown', t.ptUnchecked)}<p class="pt-next">${esc(t.ptNotFoundNext)}</p>${sourceLine()}</article>`;
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
// The name index loads on the first search, so a visit without a search does not pay for it. It is retried when the visitor searches again.
// Without it the cards of the shortage list still show, with a note that the name search is limited; the page never says "not in the register" without it.
let namesStarted = false, namesFailed = false;
function ensureNames() {
  if (namesStarted) return;
  namesStarted = true;
  loadNames().then(d => {
    registerNames = d; namesFailed = false;
    // The error of an earlier try is cleared once the index has loaded, unless the shortage list itself did not load.
    if (currentRows && $('load-error')) $('load-error').hidden = true;
    render();
  }).catch(() => { namesStarted = false; namesFailed = true; render(); });
}
function render() {
  const box = $('pt-results'), ready = Boolean(currentRows && pastRows && (registerNames || namesFailed));
  $('loading').hidden = !query || ready || !$('load-error').hidden;
  if (!query || !ready) { box.innerHTML = ''; $('pt-more-row').hidden = true; return; }
  const items = answerFor(query, currentRows, pastRows, registerNames);
  const note = namesFailed && !registerNames ? `<p class="pt-note">${esc(copy[language].ptNamesLimited)}</p>` : '';
  box.innerHTML = note + items.slice(0, shown).map(cardMarkup).join('');
  $('pt-more-row').hidden = shown >= items.length;
}
function readQuery(text, fromSubmit) {
  const next = String(text || '').trim().slice(0, 100);
  if (next !== query) shown = SHOWN;
  query = fromSubmit || next.length >= 2 ? next : '';
  try { const url = new URL(location.href); if (query) url.searchParams.set('q', query); else url.searchParams.delete('q'); history.replaceState(null, '', url); } catch (_) {}
  if (query) ensureNames();
  render();
}
if (typeof document !== 'undefined' && document.documentElement.dataset && document.documentElement.dataset.page === 'index') {
  const input = $('q');
  input.value = queryFromUrl(location.search);
  query = input.value.trim();
  $('pt-form').addEventListener('submit', e => { e.preventDefault(); clearTimeout(typing); readQuery(input.value, true); input.blur(); $('pt-results').scrollIntoView({block: 'nearest'}); });
  input.addEventListener('input', () => { clearTimeout(typing); typing = setTimeout(() => readQuery(input.value, false), 350); });
  $('pt-more').addEventListener('click', () => { shown += SHOWN; render(); });
  // A "Did you mean" name searches for that name.
  $('pt-results').addEventListener('click', e => {
    const button = e.target.closest && e.target.closest('[data-pt-query]');
    if (button) { input.value = button.dataset.ptQuery; clearTimeout(typing); readQuery(input.value, true); }
  });
  start(render);
  if (query) ensureNames();
  loadCurrent().then(d => { currentRows = relevant(d.events); snapshotDate = d.snapshot_date; renderChrome(d); render(); }).catch(showLoadError);
  loadRemoved().then(d => { pastRows = d.events || []; render(); }).catch(() => { pastRows = []; render(); });
}
