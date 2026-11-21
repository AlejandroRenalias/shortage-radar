let data, visible = 20;
const $ = id => document.getElementById(id);
const esc = value => String(value || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function drawList() {
  const query = $('search').value.toLocaleLowerCase();
  const rows = data.events.filter(e => !e.removed_on && [e.name,e.substances,e.atc,e.Company,e.NordicArticleNumber].some(x => (x || '').toLocaleLowerCase().includes(query)));
  $('result-count').textContent = `${rows.length} RECORDS`;
  $('list').innerHTML = rows.slice(0, visible).map(e => `<div class="row"><div><strong>${esc(e.name || 'Name unavailable')}</strong><small>${esc([e.strength,e.form,e.pack].filter(Boolean).join(' · '))} · VNR ${esc(e.NordicArticleNumber)}</small></div><div>${esc(e.substances || 'Substance unavailable')}<small>ATC ${esc(e.atc || '—')}</small></div><div>${esc(e.Company)}<small>Estimated end ${esc(e.EndingDate || 'unknown')}</small></div><div class="status ${e.Valid === 'K' ? '' : 'upcoming'}">${e.Valid === 'K' ? '● CURRENT' : '○ UPCOMING'}<small>From ${esc(e.UnavailableFrom)}</small></div></div>`).join('') || '<p>No matching records.</p>';
  $('more').hidden = visible >= rows.length;
}
function bars(id, counts, limit) {
  const entries = Object.entries(counts).sort((a,b) => b[1]-a[1]).slice(0,limit), max = entries[0]?.[1] || 1;
  $(id).innerHTML = entries.map(([name,n]) => `<div class="barrow"><span title="${esc(name)}">${esc(name)}</span><span class="track"><i style="width:${n/max*100}%"></i></span><strong>${n}</strong></div>`).join('');
}
fetch('data.json').then(r => {if (!r.ok) throw Error('Data unavailable'); return r.json()}).then(d => {
  data = d; const current = d.events.filter(e => !e.removed_on), companies = {}, atc = {};
  $('source-times').textContent = `Source last modified (UTC): shortages ${d.source_metadata.shortages_last_modified || 'unknown'}; basic register ${d.source_metadata.register_last_modified || 'unknown'}.`;
  current.forEach(e => {companies[e.Company || 'Unknown'] = (companies[e.Company || 'Unknown'] || 0)+1; const group = e.atc?.[0] || 'Unknown'; atc[group] = (atc[group] || 0)+1});
  $('updated').textContent = `LATEST SNAPSHOT ${d.snapshot_date}`; $('start').textContent = d.archive_start; $('total').textContent = current.length; $('companies').textContent = Object.keys(companies).length;
  bars('atc', atc, 30); bars('company', companies, 10); drawList();
  $('history-note').textContent = `History starts on ${d.archive_start}. Earlier shortages are not included.`;
  const max = Math.max(...d.history.map(h => h.count),1); $('chart').innerHTML = d.history.map(h => `<div title="${esc(h.date)}: ${h.count} records" style="height:${Math.max(3,h.count/max*145)}px"><span>${h.count}</span></div>`).join('');
  const closed = d.events.filter(e => e.removed_on && e.first_estimated_end); const weeks = (Date.parse(d.snapshot_date)-Date.parse(d.archive_start))/86400000;
  if (weeks >= 28 && closed.length >= 10) { $('delay-note').textContent = `${closed.length} observed removals with an initial estimate. Removal dates are the first saved snapshot without the record, not confirmed end dates.`; $('delay-list').innerHTML = closed.slice(-20).map(e => `<p>${esc(e.name || e.NordicArticleNumber)} · first estimate ${esc(e.first_estimated_end)} · removed by ${esc(e.removed_on)}</p>`).join(''); }
}).catch(() => {$('updated').textContent='Unable to load data'; $('list').textContent='Data could not be loaded. Please try again later.'});
$('search').addEventListener('input', () => {visible=20; if(data) drawList()}); $('more').addEventListener('click', () => {visible+=20; drawList()});
