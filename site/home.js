// Home: one sentence on today's situation, a search, a shelf of forms, the newest packages, three facts and three paths.
let data, week = null;
function started(rows, now) { return rows.filter(e => parsedDate(e.UnavailableFrom) && parsedDate(e.UnavailableFrom).valueOf() <= now); }
// Counts for the form shelf, from the raw form text counted at build time.
function shelfCounts(forms) {
  const counts = Object.fromEntries(KINDS.map(k => [k, 0]));
  for (const [form, n] of Object.entries(forms || {})) counts[formKind(form)] += n;
  return counts;
}
function shelfMarkup(forms) {
  const t = copy[language], counts = shelfCounts(forms);
  return KINDS.filter(k => counts[k] > 0).map(k => `<li><a class="shelf-tile" href="shortages.html?form=${k}">${formIcon(k, 48)}<span class="shelf-name">${esc(t['shelf_' + k])}</span><span class="shelf-count">${numberText(counts[k])}</span></a></li>`).join('');
}
function factsMarkup() {
  const t = copy[language], now = todayUTC(), oldest = started(data.longest, now)[0];
  const facts = week
    ? [[t.factNew, numberText(week.new), t.factNewNote], [t.factLeft, numberText(week.left), t.factLeftNote]]
    : [[t.factTotal, numberText(data.total), t.factTotalNote], [t.factCompanies, numberText(data.company_count), t.factCompaniesNote]];
  if (oldest) facts.push([t.factLongest, t.days(daysBetween(parsedDate(oldest.UnavailableFrom).valueOf(), now)), t.factLongestNote(nameWithStrength(oldest), dateText(oldest.UnavailableFrom))]);
  return facts.map(([label, value, note]) => `<div class="fact"><dt>${esc(label)}</dt><dd class="fact-num">${esc(value)}</dd><dd class="fact-note">${esc(note)}</dd></div>`).join('');
}
function renderHome() {
  const t = copy[language], hero = $('hero-line'), now = todayUTC();
  const n = data ? data.total : Number(hero.dataset.count);
  if (Number.isFinite(n)) hero.textContent = t.heroLine(n);
  $('shelf').innerHTML = data ? shelfMarkup(data.forms) : '';
  $('newest').innerHTML = data ? sortPackages(data.newest, '', now).slice(0, 3).map(e => pkgCard(e, now)).join('') : '';
  $('facts').innerHTML = data ? factsMarkup() : '';
  $('facts-since').textContent = data && week ? t.factsSince(dateText(week.from)) : '';
  $('facts-title').textContent = week ? t.factsTitle : t.factsToday;
}
if (typeof document !== 'undefined' && document.documentElement.dataset && document.documentElement.dataset.page === 'index') {
  start(renderHome);
  loadSummary().then(d => { data = d; renderChrome(d); renderHome(); }).catch(showLoadError);
  fetchJson('week.json').then(w => { week = w; renderHome(); }).catch(() => {});
}
