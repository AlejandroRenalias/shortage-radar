// Trends: the count over time, this week, groups, companies, the longest shortages and the delay result.
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
  const counts=history.map(h=>h.count), lo=Math.max(0,Math.floor((Math.min(...counts)-20)/50)*50), hi=Math.ceil((Math.max(...counts)+20)/50)*50, y=n=>150-125*(n-lo)/(hi-lo); let lastX=40;
  const band=Math.min(26,150/Math.max(1,segments.length-1)), room=(width-50)-band*(segments.length-1), spans=segments.map(g=>Math.max(day(g[g.length-1])-day(g[0]),1)), sum=spans.reduce((a,b)=>a+b,0), minimum=Math.min(14,room/segments.length/2);
  const widths=spans.map(s=>minimum+(room-minimum*segments.length)*s/sum); let x0=40, svg='', gaps=[];
  segments.forEach((g,i)=>{
    const w=widths[i], x=h=>g.length===1 ? x0+w/2 : x0+w*(day(h)-day(g[0]))/(day(g[g.length-1])-day(g[0]));
    if(i===segments.length-1) lastX=x(g[g.length-1]);
    if(g.length>1) svg+=`<polyline points="${g.map(h=>`${x(h).toFixed(1)},${y(h.count).toFixed(1)}`).join(' ')}" fill="none" stroke="#00704b" stroke-width="1.5" vector-effect="non-scaling-stroke"/>`;
    svg+=g.map(h=>`<circle cx="${x(h).toFixed(1)}" cy="${y(h.count).toFixed(1)}" r="2.6" fill="${h.imported ? '#fbfdfc' : '#00704b'}" stroke="#00704b" stroke-width="1.2"><title>${esc(t.capturePoint(dateText(h.date),numberText(h.count),h.imported ? t.importedSource : t.savedSource))}</title></circle>`).join('');
    x0+=w;
    if(i<segments.length-1) {const days=Math.round(day(segments[i+1][0])-day(g[g.length-1])); gaps.push(numberText(days)); svg+=`<rect x="${x0}" y="10" width="${band}" height="140" fill="#e3ece7"/>`; x0+=band;}
  });
  const mid=(lo+hi)/2, last=history[history.length-1], tick=(n,dy)=>`<text x="36" y="${y(n)+dy}" font-size="14" fill="#4a625c" text-anchor="end">${numberText(n)}</text>`;
  const grid=`<path d="M40 ${y(hi)}H${width-10}M40 ${y(mid)}H${width-10}M40 150H${width-10}" stroke="#d3dede" fill="none"/>${tick(hi,5)}${tick(mid,5)}${tick(lo,5)}`;
  const label=`<text x="${(lastX-8).toFixed(1)}" y="${(y(last.count)-9).toFixed(1)}" font-size="14" font-weight="700" fill="#0f2a24" text-anchor="end">${numberText(last.count)}</text>`;
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
function drawDelays(d, snapshotDate) {
  const t=copy[language]; if(!d) { $('delay-headline').textContent=''; $('delay-visual').innerHTML=''; $('delay-note').textContent=t.delayEmpty; $('delay-list').innerHTML=''; $('how-count').hidden=true; return; }
  const n=numberText, pct=s=>`${Math.round(s*100)}${language === 'fi' ? ' ' : ''}%`;
  $('delay-headline').textContent=d.meaningful ? t.delayHeadline(n(d.past_estimate),n(d.sample_size),n(d.undetermined),pct(d.share_past_min),pct(d.share_past_max)) : t.delaySample(n(d.sample_size),n(d.max_gap_days))+t.delaySmall(n(d.min_sample));
  const values=[[t.delayBy,d.not_past_estimate],[t.delayPast,d.past_estimate],[t.delayUncertain,d.undetermined]], max=Math.max(...values.map(([,v])=>v),1);
  $('delay-visual').innerHTML=(d.meaningful ? `<div class="delay-bars">${values.map(([label,value])=>`<div class="delay-row"><span>${esc(label)}</span><svg viewBox="0 0 100 1" preserveAspectRatio="none" aria-hidden="true"><rect width="100" height="1" fill="#e3ece7"/><rect width="${value/max*100}" height="1" fill="#00704b"/></svg><strong>${n(value)}</strong></div>`).join('')}</div>` : '')+`<p>${esc(t.activePast(n(d.active_past_estimate),dateText(snapshotDate),n(d.max_gap_days)))}</p>`;
  $('delay-note').textContent=t.delayMethod(n(d.sample_size),n(d.max_gap_days))+t.delayBias;
  const x=d.excluded || {}; $('how-count').hidden=false;
  const skipped=[['listed_at_first_capture',t.howFirst],['no_estimate',t.howNoEstimate],['wide_start_window',t.howStart],['wide_removal_window',t.howEnd],['vnr_still_listed',t.howChanged]].filter(([k])=>x[k]).map(([k,f])=>f(n(x[k]))).join(', ');
  $('how-count-text').textContent=t.howText(n(d.sample_size),n(d.removed_total),n(d.max_gap_days),skipped);
  $('delay-list').innerHTML=d.meaningful && d.examples.length ? `<h3>${esc(t.delayExamples)}</h3><ul class="examples">`+d.examples.map(e=>`<li><strong>${esc(nameWithStrength(e) || e.vnr)}</strong><span>${esc(t.firstEstimate)} ${esc(dateText(e.first_estimated_end))}, ${esc(t.lastListed)} ${esc(dateText(e.last_seen))}, ${esc(t.goneBy)} ${esc(dateText(e.removed_on))}</span></li>`).join('')+'</ul>' : '';
}
function drawDates(d) {
  $('data-date').textContent = copy[language].dataDate(dateText(d.snapshot_date));
  renderCitation(d);
  if (!historyData) { if (historyFailed) { $('history-note').textContent = copy[language].historyError; $('delay-note').textContent = copy[language].historyError; } return; }
  const h = historyData, t = copy[language], own = h.history.filter(x => !x.imported).length, imported = h.history.length - own;
  const gaps = h.history.filter(x => x.gap_days > h.max_gap_days).map(x => t.gapBefore(numberText(x.gap_days), dateText(x.date)));
  $('history-note').textContent = t.historySummary(numberText(h.history.length), dateText(d.archive_start), numberText(imported), numberText(own), gaps.join('; '), numberText(h.first_capture_count));
  const rss = (h.rss_counts || []).filter(c => c.items);
  $('rss-note').textContent = rss.length ? t.rssSummary(rss.map(c => t.rssItem(dateText(c.date), numberText(c.items))).join('; ')) : '';
  chartWidth = Math.round($('chart').clientWidth) || 400;
  drawChart(h.history, h.max_gap_days, Math.max(300, Math.min(chartWidth, 1200))); drawTable(h.history); drawDelays(h.delays, d.snapshot_date);
}
function renderData() {
  if (!data) return;
  const d = data, t = copy[language], companies = {}, atc = {};
  for (const [name, n] of Object.entries(d.companies)) companies[name || t.unknownCompany] = n;
  for (const [prefix, n] of Object.entries(d.atc)) { const group = prefix && groupName(prefix); if (group) atc[group] = (atc[group] || 0) + n; }
  drawDates(d);
  const now = todayUTC(), longest = d.longest.filter(e => parsedDate(e.UnavailableFrom) && parsedDate(e.UnavailableFrom).valueOf() <= now).slice(0, 5);
  $('longest-list').innerHTML = longest.map(e => `<li><div><strong><a href="medicine.html?vnr=${esc(e.NordicArticleNumber)}">${esc(nameWithStrength(e) || t.unavailable)}</a></strong><small>${esc(packText(e))}</small><small>${esc(e.Company)}</small><small>${esc(t.since)} ${esc(dateText(e.UnavailableFrom))}</small></div><span class="duration">${esc(t.days(daysBetween(parsedDate(e.UnavailableFrom).valueOf(), now)).replace(/ /g, ' '))}</span></li>`).join('');
  drawWeek(weekData, d.total); bars('atc', atc, 30); bars('company', companies, 10);
}
if (typeof document !== 'undefined' && document.documentElement.dataset && document.documentElement.dataset.page === 'trends') {
  start(renderData); wireCitation();
  loadSummary().then(d => { data = d; renderChrome(d); renderData(); requestAnimationFrame(() => {
    fetchJson('history.json').then(h => { historyData = h; renderData(); }).catch(() => { historyFailed = true; renderData(); });
    fetchJson('week.json').then(w => { weekData = w; renderData(); }).catch(() => {});
  }); }).catch(showLoadError);
  let resizeTimer; addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => { if (historyData && Math.abs(($('chart').clientWidth || 0) - chartWidth) > 40) renderData(); }, 200); });
}
