// Medicine: one package, from its VNR in the address (medicine.html?vnr=...).
// The data comes from one small file for the VNR's last two digits (p/NN.json), not from the whole archive.
function vnrFromSearch(search) { return (new URLSearchParams(search).get('vnr') || '').trim().slice(0, 12); }
function validVnr(v) { return /^\d{6}$/.test(v); }
// Finds the package for a number in its data file: the current notice first, else the most recent one that left the list.
function lookup(vnr, shard) {
  if (!validVnr(vnr)) return {state: 'missing', events: []};
  const mine = shard.events.filter(e => e.NordicArticleNumber === vnr);
  const current = mine.filter(e => !e.removed_on).sort(defaultCompare(todayUTC()));
  if (current.length) return {state: statusOf(current[0]), events: current};
  const gone = mine.sort((a, b) => (b.last_seen || '').localeCompare(a.last_seen || '')).slice(0, 1);
  return gone.length ? {state: 'left', events: gone} : {state: 'missing', events: []};
}
let vnr = '', shard = null;
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
    + (spec.length ? `<p class="form pkg-spec">${spec.map(x => `<span>${esc(x)}</span>`).join(' ')}</p>` : '')
    + `<p class="pkg-kind">${[formText(e.form), groupName(e.atc)].filter(Boolean).map(x => `<span>${esc(x)}</span>`).join('')}${isVet(e) ? `<span class="vet">${esc(t.veterinary)}</span>` : ''}</p></div></div>`
    + `<p class="status-line">${esc(line)}</p></article>`;
}
// The other packages of the group, from the register: name and strength, pack and company.
function altList(items, limit) {
  const t = copy[language], li = p => `<li><strong>${esc(nameWithStrength(p) || p.name)}</strong>${packText(p) ? `<span>${esc(packText(p))}</span>` : ''}${p.company ? `<span>${esc(p.company)}</span>` : ''}${p.listed === false ? `<span class="alt-flag">${esc(t.altRegister)}</span>` : ''}</li>`;
  const shown = items.slice(0, limit), rest = items.slice(limit);
  return `<ul class="alts">${shown.map(li).join('')}</ul>` + (rest.length ? `<details class="alts-more"><summary>${esc(t.altAll(items.length))}</summary><ul class="alts">${rest.map(li).join('')}</ul></details>` : '');
}
// Can the pharmacy give a substitute? The label, its reason and the packages that make it checkable.
function impactMarkup(e, groups) {
  const t = copy[language], level = impactOf(e), code = e.substitution_group, group = (code && groups && groups[code]) || {available: [], short: []};
  const others = list => (list || []).filter(p => p.vnr !== e.NordicArticleNumber && p.vnr !== e.current_vnr);
  const available = others(group.available), short = others(group.short);
  const text = t['impactText_' + level];
  const reason = level === 'no_alternative' ? `<p>${esc(short.length ? t.impactCriticalShort : t.impactCriticalAlone)}</p>` : '';
  const lists = (level === 'substitute' && available.length ? `<h3>${esc(t.altTitle)}</h3>${altList(available, 6)}` : '') + (short.length && level !== 'vet' ? `<h3>${esc(t.altShort)}</h3>${altList(short, 6)}` : '');
  const groupLink = code && level !== 'vet' ? `<p class="group-link"><a href="group.html?g=${encodeURIComponent(code)}">${esc(t.grpPackages)}</a></p>` : '';
  return `<section class="panel impact-panel" aria-labelledby="impact-title"><h2 id="impact-title">${esc(t.impactQuestion)}</h2>${impactBadge(e)}<p>${esc(text)}</p>${reason}${lists}${groupLink}`
    + `<p class="note">${code && level !== 'vet' ? `${esc(t.groupCode(code))}. ` : ''}${esc(t.altNote)} <a href="about.html#impact">${esc(t.impactLink)}</a></p></section>`;
}
// "Ask your pharmacy" is said once: by the impact panel for a current package, else by the opening sentence of the advice.
function whatMarkup(e, status) {
  const t = copy[language], asked = status !== 'left';
  const advice = isVet(e) ? t.whatTextVet : asked ? t.whatTextRest : t.whatText;
  return `<section class="panel what" aria-labelledby="what-title"><h2 id="what-title">${esc(t.whatTitle)}</h2><p>${esc(advice)}</p>${isVet(e) ? '' : `<p>${esc(t.whatUrgent)}</p>`}<p class="more-info">${esc(t.moreInfo(e.Company))} <a href="${esc(t.moreInfoUrl)}">${esc(t.moreInfoLink)}</a></p><p><a href="about.html#what-to-do">${esc(t.whatLink)}</a></p></section>`;
}
// An ended record names the captures that bound it, not the date of today's file.
function sourceLine(e, left, snapshotDate) {
  const t = copy[language];
  return left && e.removed_on ? t.sourceNoteEnded(dateText(e.last_seen), dateText(e.removed_on)) : t.sourceNote(dateText(snapshotDate));
}
function notFound(root) {
  const t = copy[language];
  document.title = `${t.nfTitle} | ${t.brand}`;
  root.innerHTML = `<section class="not-found"><a class="back" href="shortages.html">${uiIcon('back', 18)}<span>${esc(t.medBack)}</span></a><h1>${esc(t.nfTitle)}</h1><p class="lead">${esc(vnr ? t.nfText(vnr) : t.nfNone)}</p>`
    + `<form class="bigsearch" action="shortages.html" method="get" role="search"><label for="q">${esc(t.homeSearchLabel)}</label><div class="searchrow">${uiIcon('search', 22)}<input id="q" name="q" type="search" autocomplete="off" maxlength="100" placeholder="${esc(t.placeholder)}"><button type="submit" class="btn">${esc(t.searchButton)}</button></div><p class="hint">${esc(t.hint)}</p></form>`
    + `<p><a href="shortages.html">${esc(t.nfSearch)}</a></p></section>`;
}
function render() {
  const t = copy[language], root = $('medicine');
  if (!shard) return;
  const found = lookup(vnr, shard);
  if (found.state === 'missing') return notFound(root);
  const events = found.events, e = events[0], left = found.state === 'left', status = found.state, now = todayUTC();
  document.title = `${e.name || t.unavailable} | ${t.brand}`;
  root.innerHTML = `<a class="back" href="shortages.html">${uiIcon('back', 18)}<span>${esc(t.medBack)}</span></a><div class="med-layout"><div class="med-main">${labelMarkup(e, status)}${left ? '' : impactMarkup(e, shard.groups)}${timelineMarkup(e, left)}${whatMarkup(e, status)}`
    + (events.length > 1 ? `<section class="panel"><h2>${esc(t.otherNotice)}</h2><div class="pkg-list">${events.slice(1).map(x => pkgCard(x, now)).join('')}</div></section>` : '')
    + `</div><aside class="med-side">${detailsMarkup(e)}<section class="panel share" aria-labelledby="share-title"><h2 id="share-title">${esc(t.shareTitle)}</h2><button type="button" class="btn" id="copy-page">${uiIcon('copy', 18)}<span>${esc(t.copyPage)}</span></button> <span id="copy-status" role="status"></span></section>`
    + `<p class="source-note">${esc(sourceLine(e, left, shard.snapshot_date))} <a href="https://fimea.fi/en/about_us/open-data">${esc(t.sourceLink)}</a></p></aside></div>`;
  $('copy-page').addEventListener('click', () => {
    const done = () => { $('copy-status').textContent = copy[language].linkCopied; setTimeout(() => { $('copy-status').textContent = ''; }, 2500); };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(`${location.origin}${location.pathname}?vnr=${encodeURIComponent(vnr)}`).then(done, () => {});
  });
}
if (typeof document !== 'undefined' && document.documentElement.dataset && document.documentElement.dataset.page === 'medicine') {
  vnr = vnrFromSearch(location.search);
  start(render);
  fetchJson(validVnr(vnr) ? `p/${vnr.slice(-2)}.json` : 'summary.json').then(d => { shard = validVnr(vnr) ? d : {events: [], snapshot_date: d.snapshot_date}; renderChrome(d); render(); }).catch(showLoadError);
}
