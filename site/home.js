// Home: one sentence on today's situation, a search, the impact triage, a list of forms, the newest packages, three facts and three paths.
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
// Counts by impact level: from summary.json once it is loaded, else from the numbers built into the page.
function impactCounts() {
  if (data && data.impact) return data.impact;
  const raw = ($('triage') && $('triage').dataset.impact) || '';
  return Object.fromEntries(raw.split(',').filter(Boolean).map(pair => { const [key, n] = pair.split(':'); return [key, Number(n) || 0]; }));
}
function triageMarkup(counts) {
  const t = copy[language], levels = ['substitute', 'critical', 'nogroup'], total = levels.reduce((sum, k) => sum + (counts[k] || 0), 0) || 1;
  return levels.map(k => `<li><a class="tri tri-${k}" href="shortages.html?impact=${k}">${uiIcon(k, 24)}<span class="tri-num">${numberText(counts[k] || 0)}</span><span class="tri-text"><strong>${esc(t['impact_' + k])}</strong><span>${esc(t['triageNote_' + k])}</span></span>${uiIcon('chevron', 20).replace('class="uicon"', 'class="uicon tri-go"')}<svg class="tri-bar" viewBox="0 0 100 6" preserveAspectRatio="none" aria-hidden="true" focusable="false"><rect class="track" width="100" height="6"/><rect class="part" width="${(100 * (counts[k] || 0) / total).toFixed(2)}" height="6"/></svg></a></li>`).join('');
}
function renderHome() {
  const t = copy[language], hero = $('hero-line'), now = todayUTC();
  const n = data ? data.total : Number(hero.dataset.count);
  if (Number.isFinite(n)) hero.textContent = t.heroLine(n);
  const counts = impactCounts();
  if (Number.isFinite(counts.substitute)) {
    $('hero-answer').textContent = t.heroAnswer(counts.substitute);
    $('triage-list').innerHTML = triageMarkup(counts);
    $('triage-vet').textContent = t.triageVet(counts.vet || 0);
    $('triage-vet').parentElement.hidden = !counts.vet;
  }
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
