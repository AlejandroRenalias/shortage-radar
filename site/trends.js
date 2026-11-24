// Trends: the count over time, this week, groups, the longest shortages and the end dates that changed.
let data, historyData, weekData, historyFailed = false, chartWidth = 0;
function bars(id, counts, limit) {
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, limit), max = entries[0]?.[1] || 1;
  $(id).innerHTML = entries.map(([name, n]) => `<div class="barrow"><span class="bar-label">${esc(name)}</span><strong>${numberText(n)}</strong><svg class="bar-svg" viewBox="0 0 100 3" preserveAspectRatio="none" aria-hidden="true"><rect width="100" height="3" fill="#e3ece7"/><rect width="${n / max * 100}" height="3" fill="#00704b"/></svg></div>`).join('');
}
function drawChart(history, maxGap, width = 400) {
  const t=copy[language];
  if (history.length < 2) { $('chart').textContent=t.chartEmpty; return; }
  const day=h=>Date.parse(h.date)/86400000, segments=[];
  history.forEach(h=>{const g=segments[segments.length-1]; if(g && day(h)-day(g[g.length-1])<=maxGap) g.push(h); else segments.push([h]);});
  const last=history[history.length-1], latest=numberText(last.count);
  // Leave a right gutter for the localized value, with space between it and the last point.
  const plotRight=width-16-9*latest.length;
  const counts=history.map(h=>h.count), lo=Math.max(0,Math.floor((Math.min(...counts)-20)/50)*50), hi=Math.ceil((Math.max(...counts)+20)/50)*50, y=n=>150-125*(n-lo)/(hi-lo);
  const band=Math.min(26,150/Math.max(1,segments.length-1)), room=plotRight-40-band*(segments.length-1), spans=segments.map(g=>Math.max(day(g[g.length-1])-day(g[0]),1)), sum=spans.reduce((a,b)=>a+b,0), minimum=Math.min(14,room/segments.length/2);
  const widths=spans.map(s=>minimum+(room-minimum*segments.length)*s/sum); let x0=40, svg='', gaps=[];
  segments.forEach((g,i)=>{
    const w=widths[i], x=h=>g.length===1 ? x0+w/2 : x0+w*(day(h)-day(g[0]))/(day(g[g.length-1])-day(g[0]));
    if(g.length>1) svg+=`<polyline points="${g.map(h=>`${x(h).toFixed(1)},${y(h.count).toFixed(1)}`).join(' ')}" fill="none" stroke="#00704b" stroke-width="1.5" vector-effect="non-scaling-stroke"/>`;
    svg+=g.map(h=>`<circle cx="${x(h).toFixed(1)}" cy="${y(h.count).toFixed(1)}" r="2.6" fill="${h.imported ? '#fbfdfc' : '#00704b'}" stroke="#00704b" stroke-width="1.2"><title>${esc(t.capturePoint(dateText(h.date),numberText(h.count),h.imported ? t.importedSource : t.savedSource))}</title></circle>`).join('');
    x0+=w;
    if(i<segments.length-1) {const days=Math.round(day(segments[i+1][0])-day(g[g.length-1])); gaps.push(numberText(days)); svg+=`<rect x="${x0}" y="10" width="${band}" height="140" fill="#e3ece7"/>`; x0+=band;}
  });
  const mid=(lo+hi)/2, tick=(n,dy)=>`<text x="36" y="${y(n)+dy}" font-size="14" fill="#5d6d68" text-anchor="end">${numberText(n)}</text>`;
  const grid=`<path d="M40 ${y(hi)}H${plotRight}M40 ${y(mid)}H${plotRight}M40 150H${plotRight}" stroke="#d3dede" fill="none"/>${tick(hi,5)}${tick(mid,5)}${tick(lo,5)}`;
  const label=`<text x="${plotRight+8}" y="${(y(last.count)+5).toFixed(1)}" font-size="14" font-weight="600" fill="#0f2a24">${latest}</text>`;
  $('chart').innerHTML=`<svg viewBox="0 0 ${width} 170" role="img" aria-label="${esc(t.chartSummary(dateText(history[0].date),dateText(last.date),numberText(last.count),gaps.join(', ')))}">${grid}${svg}${label}</svg><div class="chart-labels"><span>${esc(dateText(history[0].date))}</span><span>${numberText(last.count)}, ${esc(dateText(last.date))}</span></div><div class="chart-labels"><span>${esc(t.savedLegend)}</span><span>${esc(t.importedLegend)}</span></div>${lo>0 ? `<div class="chart-labels"><span>${esc(t.axisNote(numberText(lo)))}</span></div>` : ''}${gaps.length ? `<div class="chart-labels"><span>${esc(gaps.map(g=>t.noCaptures(g)).join('; '))}</span></div>` : ''}`;
}
function drawTable(history) {
  const t = copy[language];
  $('chart-table').innerHTML = `<table><thead><tr><th scope="col">${esc(t.thDate)}</th><th scope="col">${esc(t.thCount)}</th><th scope="col">${esc(t.thSource)}</th></tr></thead><tbody>${history.slice().reverse().map(h => `<tr><td>${esc(dateText(h.date))}</td><td>${numberText(h.count)}</td><td>${esc(h.imported ? t.importedSource : t.savedSource)}</td></tr>`).join('')}</tbody></table>`;
}
function drawWeek(w, total) {
  const t = copy[language], n = numberText; $('feed-link').href = language === 'fi' ? 'feed-fi.xml' : 'feed.xml';
  if (!w) { $('week').hidden = true; return; }
  const from = dateText(w.from); $('week').hidden = false;
  $('week-window').textContent = t.weekWindow(from, n(w.days));
  $('week-facts').innerHTML = [[t.weekNew, n(w.new), t.weekNewNote(from)], [t.weekLeft, n(w.left), t.weekLeftNote(from)], [t.weekTotal, n(total), t.weekTotalNote(n(total), n(w.count_from), from)]].map(([label, value, note]) => `<div class="fact"><dt>${esc(label)}</dt><dd class="fact-num">${esc(value)}</dd><dd class="fact-note">${esc(note)}</dd></div>`).join('');
}
// One dated fact: how many current notices changed their end date in our captures (build.py end_date_changes).
function drawEndChanges(c) {
  const t = copy[language], n = numberText;
  if (!c) { $('end-changes-text').textContent = ''; $('end-changes-note').textContent = ''; return; }
  $('end-changes-text').textContent = t.endChangesText(n(c.changed), n(c.current), dateText(c.from), dateText(c.to));
  $('end-changes-note').textContent = t.endChangesNote(n(c.max_gap_days));
}
// Groups that newly have no interchangeable product, and the counts recorded each day with that day's register.
function drawCritical(h) {
  const t = copy[language], list = h.newly_critical || [], gaps = h.history.filter(x => x.gap_days > h.max_gap_days);
  const from = (gaps.length ? gaps[gaps.length - 1] : h.history[0]).date;
  $('new-crit-list').innerHTML = list.slice(0, 12).map(c => {
    const names = [...new Set((c.packages || []).map(p => p.name).filter(Boolean))].join(', ');
    return `<li><div><strong><a href="medicine.html?vnr=${esc(c.vnrs[0])}">${esc([c.medicine || names, strengthText(c)].filter(Boolean).join(' '))}</a></strong>${names ? `<small>${esc(names)}</small>` : ''}</div><span class="crit-when">${esc(t.newCritItem(dateText(c.date), dateText(c.after)))}</span></li>`;
  }).join('') || `<li>${esc(t.newCritNone)}</li>`;
  $('new-crit-method').textContent = t.newCritMethod(numberText(list.length), dateText(from));
  const rec = h.triage_counts || [];
  $('triage-record').innerHTML = rec.length ? `<h3>${esc(t.triageRecTitle)}</h3><p class="note">${esc(t.triageRecNote(dateText(rec[0].date)))}</p><div class="data-table"><table><thead><tr><th scope="col">${esc(t.thDate)}</th>${IMPACT_LEVELS.map(k => `<th scope="col">${esc(t['impact_' + k])}</th>`).join('')}</tr></thead><tbody>${rec.slice().reverse().map(r => `<tr><td>${esc(dateText(r.date))}</td>${IMPACT_LEVELS.map(k => `<td>${numberText(r[k] || 0)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>` : '';
}
function drawDates(d) {
  $('data-date').textContent = copy[language].dataDate(dateText(d.snapshot_date));
  renderCitation(d);
  if (!historyData) { if (historyFailed) { $('history-note').textContent = copy[language].historyError; $('end-changes-note').textContent = copy[language].historyError; } return; }
  const h = historyData, t = copy[language], own = h.history.filter(x => !x.imported).length, imported = h.history.length - own;
  const gaps = h.history.filter(x => x.gap_days > h.max_gap_days).map(x => t.gapBefore(numberText(x.gap_days), dateText(x.date)));
  $('history-note').textContent = t.historySummary(numberText(h.history.length), dateText(d.archive_start), numberText(imported), numberText(own), gaps.join('; '), numberText(h.first_capture_count));
  const rss = (h.rss_counts || []).filter(c => c.items);
  $('rss-note').textContent = rss.length ? t.rssSummary(rss.map(c => t.rssItem(dateText(c.date), numberText(c.items))).join('; ')) : '';
  chartWidth = Math.round($('chart').clientWidth) || 400;
  drawChart(h.history, h.max_gap_days, Math.max(300, Math.min(chartWidth, 1200))); drawTable(h.history); drawEndChanges(h.end_changes); drawCritical(h);
}
function renderData() {
  if (!data) return;
  const d = data, t = copy[language], atc = {};
  for (const [prefix, n] of Object.entries(d.atc)) { const group = prefix && groupName(prefix); if (group) atc[group] = (atc[group] || 0) + n; }
  drawDates(d);
  const now = todayUTC(), longest = d.longest.filter(e => parsedDate(e.UnavailableFrom) && parsedDate(e.UnavailableFrom).valueOf() <= now).slice(0, 5);
  $('longest-list').innerHTML = longest.map(e => `<li><div><strong><a href="medicine.html?vnr=${esc(e.NordicArticleNumber)}">${esc(nameWithStrength(e) || t.unavailable)}</a></strong><small>${esc(packText(e))}</small><small>${esc(e.Company)}</small><small>${esc(t.since)} ${esc(dateText(e.UnavailableFrom))}</small></div><span class="duration">${esc(t.days(daysBetween(parsedDate(e.UnavailableFrom).valueOf(), now)).replace(/ /g, ' '))}</span></li>`).join('');
  drawWeek(weekData, d.total); bars('atc', atc, 30);
}
if (typeof document !== 'undefined' && document.documentElement.dataset && document.documentElement.dataset.page === 'trends') {
  start(renderData); wireCitation();
  loadSummary().then(d => { data = d; renderChrome(d); renderData(); requestAnimationFrame(() => {
    fetchJson('history.json').then(h => { historyData = h; renderData(); }).catch(() => { historyFailed = true; renderData(); });
    fetchJson('week.json').then(w => { weekData = w; renderData(); }).catch(() => {});
  }); }).catch(showLoadError);
  let resizeTimer; addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => { if (historyData && Math.abs(($('chart').clientWidth || 0) - chartWidth) > 40) renderData(); }, 200); });
}
