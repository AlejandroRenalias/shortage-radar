// Home: one sentence on today's situation, a search, three facts and three paths.
let data, week = null;
function currentRows() { return data ? relevant(data.events) : []; }
function factsMarkup() {
  const t = copy[language], rows = currentRows(), now = todayUTC();
  const started = rows.filter(e => parsedDate(e.UnavailableFrom) && parsedDate(e.UnavailableFrom).valueOf() <= now).sort((a, b) => a.UnavailableFrom.localeCompare(b.UnavailableFrom));
  const oldest = started[0];
  const facts = week
    ? [[t.factNew, numberText(week.new), t.factNewNote], [t.factLeft, numberText(week.left), t.factLeftNote]]
    : [[t.factTotal, numberText(rows.length), t.factTotalNote], [t.factCompanies, numberText(new Set(rows.map(e => e.Company)).size), t.factCompaniesNote]];
  if (oldest) facts.push([t.factLongest, t.days(daysBetween(parsedDate(oldest.UnavailableFrom).valueOf(), now)), t.factLongestNote(nameWithStrength(oldest), dateText(oldest.UnavailableFrom))]);
  return facts.map(([label, value, note]) => `<div class="fact"><dt>${esc(label)}</dt><dd class="fact-num">${esc(value)}</dd><dd class="fact-note">${esc(note)}</dd></div>`).join('');
}
function renderHome() {
  const t = copy[language], hero = $('hero-line');
  const n = data ? currentRows().length : Number(hero.dataset.count);
  if (Number.isFinite(n)) hero.textContent = t.heroLine(n);
  $('facts').innerHTML = data ? factsMarkup() : '';
  $('facts-since').textContent = data && week ? t.factsSince(dateText(week.from)) : '';
  $('newest').innerHTML = data && matchMedia('(min-width: 900px)').matches ? sortPackages(currentRows(), '').slice(0, 2).map(e => pkgCard(e)).join('') : '';
  $('facts-title').textContent = week ? t.factsTitle : t.factsToday;
}
start(renderHome);
loadCurrent().then(d => { data = d; renderChrome(d); renderHome(); }).catch(showLoadError);
fetchJson('week.json').then(w => { week = w; renderHome(); }).catch(() => {});
