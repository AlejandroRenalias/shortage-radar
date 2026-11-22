// Medicine: one package, from its VNR in the address (medicine.html?vnr=...).
function vnrFromSearch(search) { return (new URLSearchParams(search).get('vnr') || '').trim().slice(0, 12); }
function validVnr(v) { return /^\d{6}$/.test(v); }
// Finds the package for a number: on the current list first, then in the archive of events that left the list.
function lookup(vnr, current, archived, archiveFailed) {
  if (!validVnr(vnr)) return {state: 'missing', events: []};
  let events = current.events.filter(e => e.NordicArticleNumber === vnr && !e.removed_on).sort(defaultCompare(todayUTC()));
  if (events.length) return {state: statusOf(events[0]), events};
  if (!archived && !archiveFailed) return {state: 'pending', events: []};
  events = (archived ? archived.events : []).filter(e => e.NordicArticleNumber === vnr).sort((a, b) => (b.last_seen || '').localeCompare(a.last_seen || '')).slice(0, 1);
  return events.length ? {state: 'left', events} : {state: 'missing', events: []};
}
let vnr = '', current = null, archived = null, archiveFailed = false;
function timelineBar(model) {
  const x = pos => (12 + pos * 376).toFixed(1), mark = key => model.marks.find(m => m.key === key);
  const start = mark('start'), today = mark('today'), end = mark('end');
  const tone = model.late ? 'late' : model.status === 'soon' ? 'soon' : 'now';
  let svg = '<rect class="tl-rail" x="12" y="12" width="376" height="4" rx="2"/>';
  if (start && today && today.pos >= start.pos) svg += `<rect class="tl-fill tl-${tone}" x="${x(start.pos)}" y="11" width="${(Math.min(today.pos, end ? Math.max(end.pos, start.pos) : today.pos) * 376 - start.pos * 376).toFixed(1)}" height="6" rx="3"/>`;
  if (model.late && end) svg += `<rect class="tl-over" x="${x(end.pos)}" y="11" width="${((today.pos - end.pos) * 376).toFixed(1)}" height="6" rx="3"/>`;
  if (start && today && today.pos < start.pos) svg += `<rect class="tl-wait" x="${x(today.pos)}" y="13" width="${((start.pos - today.pos) * 376).toFixed(1)}" height="2"/>`;
  if (start) svg += `<circle class="tl-pt tl-pt-start" cx="${x(start.pos)}" cy="14" r="8"/>`;
  if (end) svg += `<rect class="tl-pt tl-pt-end" x="${(12 + end.pos * 376 - 2.5).toFixed(1)}" y="2" width="5" height="24" rx="2.500"/>`;
  svg += `<circle class="tl-pt tl-pt-today tl-${tone}" cx="${x(today.pos)}" cy="14" r="9"/>`;
  return `<svg class="tl-bar" viewBox="0 0 400 28" aria-hidden="true" focusable="false">${svg}</svg>`;
}
function timelineMarkup(e, archive) {
  const t = copy[language], now = archive ? parsedDate(e.last_seen).valueOf() : todayUTC(), model = timelineModel(e, now);
  const items = {
    start: ['start', t.tlStart, dateText(e.UnavailableFrom), model.daysSinceStart !== null ? t.tlDuration(model.daysSinceStart) : model.daysUntilStart !== null ? t.tlSoonNote(model.daysUntilStart) : ''],
    today: ['today', archive ? t.tlLastListed : t.tlToday, dateText(new Date(now).toISOString().slice(0, 10)), ''],
    end: ['end', t.tlEnd, dateText(e.EndingDate), model.late ? t.tlPast(model.daysPastEstimate) : model.daysToEstimate !== null ? t.tlRemaining(model.daysToEstimate) : '']
  };
  const list = model.order.map(key => {
    const [cls, label, date, note] = items[key];
    return `<li class="tl-item tl-${cls}${key === 'end' && model.late ? ' is-late' : ''}"><span class="tl-key" aria-hidden="true"></span><div><strong>${esc(label)}</strong><span class="tl-date">${esc(date)}</span>${note ? `<small>${esc(note)}</small>` : ''}${key === 'end' && model.late ? `<small class="late-flag">${esc(t.late)}</small>` : ''}</div></li>`;
  }).join('');
  const earlier = model.earlier.length ? `<div class="tl-earlier"><h3>${esc(t.tlEarlier)}</h3><p>${esc(t.tlEarlierNote)}</p><ul>${model.earlier.map(x => `<li><span class="tl-date">${esc(dateText(x.date))}</span><small>${esc(t.tlSeen(dateText(x.seen)))}</small></li>`).join('')}${model.hasEnd ? `<li class="is-now"><span class="tl-date">${esc(dateText(e.EndingDate))}</span><small>${esc(t.tlCurrent)}</small></li>` : ''}</ul></div>` : '';
  return `<section class="panel timeline" aria-labelledby="tl-title"><h2 id="tl-title">${esc(t.timelineTitle)}</h2>${timelineBar(model)}<ol class="tl-list">${list}</ol>${model.hasEnd ? '' : `<p class="note">${esc(t.tlNoEnd)}</p>`}${earlier}</section>`;
}
function detailsMarkup(e) {
  const t = copy[language];
  const rows = [[t.substance, e.substances], [t.strength, strengthText(e)], [t.pack, packText(e)], [t.form, formText(e.form)], [t.formRaw, e.form], [t.group, groupName(e.atc)], ['ATC', e.atc], [t.company, e.Company], [t.vnr, e.NordicArticleNumber], [t.reported, e.DateOfTheNotification ? dateText(e.DateOfTheNotification) : '']];
  return `<section class="panel" aria-labelledby="det-title"><h2 id="det-title">${esc(t.detailsTitle)}</h2><dl class="details">${rows.filter(([, v]) => v).map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join('')}</dl></section>`;
}
function labelMarkup(e, status) {
  const t = copy[language], spec = [strengthShown(e), packText(e)].filter(Boolean), kind = formKind(e.form);
  const tab = status === 'left' ? [t.medLeft, 'ended'] : [statusLabel(status), status === 'soon' ? 'soon' : status === 'unknown' ? 'unknown' : 'now'];
  const line = {now: t.medNow, soon: t.medSoon, unknown: t.medUnknown, left: t.medLeftText(dateText(e.last_seen))}[status];
  return `<article class="pkg pkg-${status === 'left' ? 'ended' : status} label"><p class="pkg-tab">${uiIcon(tab[1], 18)}<span>${esc(tab[0])}</span></p><div class="pkg-main"><span class="pkg-icon label-icon" title="${esc(kindLabel(kind))}">${formIcon(kind, 64)}</span><div class="pkg-id"><h1 class="pkg-name">${esc(e.name || t.unavailable)}</h1>`
    + (spec.length ? `<p class="form pkg-spec">${spec.map(s => `<span>${esc(s)}</span>`).join(' ')}</p>` : '')
    + `<p class="pkg-kind">${[formText(e.form), groupName(e.atc)].filter(Boolean).map(s => `<span>${esc(s)}</span>`).join(' ')}${(e.atc || '').startsWith('Q') ? `<span class="vet">${esc(t.veterinary)}</span>` : ''}</p></div></div>`
    + `<p class="status-line">${esc(line)}</p><p class="ask">${esc(status !== 'left' && e.other_packages_count > 0 ? t.otherPackages : t.askPharmacy)}</p></article>`;
}
function whatMarkup(e) {
  const t = copy[language];
  return `<section class="panel what" aria-labelledby="what-title"><h2 id="what-title">${esc(t.whatTitle)}</h2><p>${esc(t.whatText)}</p><p class="more-info">${esc(t.moreInfo(e.Company))} <a href="${esc(t.moreInfoUrl)}">${esc(t.moreInfoLink)}</a></p><p><a href="about.html#what-to-do">${esc(t.whatLink)}</a></p></section>`;
}
function notFound(root) {
  const t = copy[language];
  document.title = `${t.nfTitle} | ${t.brand}`;
  root.innerHTML = `<section class="not-found"><a class="back" href="shortages.html">${uiIcon('back', 18)}<span>${esc(t.medBack)}</span></a><h1>${esc(t.nfTitle)}</h1><p class="lead">${esc(vnr ? t.nfText(vnr) : t.nfNone)}</p>`
    + `<form class="bigsearch" action="shortages.html" method="get" role="search"><label for="q">${esc(t.homeSearchLabel)}</label><div class="searchrow">${uiIcon('search', 22)}<input id="q" name="q" type="search" autocomplete="off" maxlength="100" placeholder="${esc(t.placeholder)}"><button type="submit" class="btn">${esc(t.searchButton)}</button></div><p class="hint">${esc(t.hint)}</p></form>`
    + `<p><a href="shortages.html">${esc(t.nfSearch)}</a></p></section>`;
}
function render() {
  const t = copy[language], root = $('medicine'), data = current;
  if (!data) return;
  const found = lookup(vnr, data, archived, archiveFailed);
  if (found.state === 'pending') return;
  if (found.state === 'missing') return notFound(root);
  const events = found.events;
  const e = events[0], left = found.state === 'left', status = found.state, now = todayUTC();
  document.title = `${e.name || t.unavailable} | ${t.brand}`;
  const url = `${location.origin}${location.pathname}?vnr=${encodeURIComponent(vnr)}`;
  root.innerHTML = `<a class="back" href="shortages.html">${uiIcon('back', 18)}<span>${esc(t.medBack)}</span></a><div class="med-layout"><div class="med-main">${labelMarkup(e, status)}${timelineMarkup(e, left)}${whatMarkup(e)}`
    + (events.length > 1 ? `<section class="panel"><h2>${esc(t.otherNotice)}</h2><div class="pkg-list">${events.slice(1).map(x => pkgCard(x, now)).join('')}</div></section>` : '')
    + `</div><aside class="med-side">${detailsMarkup(e)}<section class="panel" aria-labelledby="share-title"><h2 id="share-title">${esc(t.shareTitle)}</h2><p class="share-url">${esc(url)}</p><button type="button" class="btn" id="copy-page">${uiIcon('copy', 18)}<span>${esc(t.copyPage)}</span></button> <span id="copy-status" role="status"></span></section>`
    + `<p class="source-note">${esc(t.sourceNote(dateText(data.snapshot_date)))} <a href="https://fimea.fi/en/about_us/open-data">${esc(t.sourceLink)}</a></p></aside></div>`;
  $('copy-page').addEventListener('click', () => {
    const done = () => { $('copy-status').textContent = copy[language].linkCopied; setTimeout(() => { $('copy-status').textContent = ''; }, 2500); };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).then(done, () => {});
  });
}
if (typeof document !== 'undefined' && document.documentElement.dataset && document.documentElement.dataset.page === 'medicine') {
  vnr = vnrFromSearch(location.search);
  start(render);
  loadCurrent().then(d => {
    current = d; renderChrome(d); render();
    if (lookup(vnr, d, null, false).state === 'pending') fetchJson('data.json').then(a => { archived = a; render(); }).catch(() => { archiveFailed = true; render(); });
  }).catch(showLoadError);
}
