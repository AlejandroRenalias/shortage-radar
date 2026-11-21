let data, visible = 20;
const $ = id => document.getElementById(id);
const esc = value => String(value || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const copy = {
  en: {helpTitle:'What is a shortage?', help:'The company has told Fimea it cannot deliver this package for a while. Your pharmacy may still have some. Ask your pharmacy what is available. This site is not medical advice.', title:'Reported shortages', hint:'Search by medicine, active substance, ATC, company or VNR.', placeholder:'Search your medicine, e.g. Burana', count:'records', more:'Show more', empty:'No medicines match your search. Try another name or number.', out:'Out now', soon:'Starts soon', since:'Not available since', starts:'Expected to become unavailable on', expected:'Expected back around', estimate:"the company’s estimate", unknown:'Return date not known.', late:'Later than estimated', days:n=>`${n} ${n === 1 ? 'day' : 'days'}`, details:'Details', strength:'Strength', substance:'Active substance', company:'Company', reported:'Report date', unavailable:'Name unavailable', group:'What is it for', noGroup:'Group not listed', form:'Original form', otherForm:'Other form'},
  fi: {helpTitle:'Mitä saatavuushäiriö tarkoittaa?', help:'Yritys on ilmoittanut Fimealle, ettei se voi toimittaa tätä pakkausta vähään aikaan. Apteekissa sitä voi silti olla. Kysy apteekista, mitä on saatavilla. Tämä sivusto ei anna lääketieteellisiä neuvoja.', title:'Ilmoitetut saatavuushäiriöt', hint:'Hae lääkkeen tai vaikuttavan aineen nimellä, ATC-koodilla, yrityksellä tai VNR-numerolla.', placeholder:'Hae lääkettä, esim. Burana', count:'ilmoitusta', more:'Näytä lisää', empty:'Haulla ei löytynyt lääkkeitä. Kokeile toista nimeä tai numeroa.', out:'Saatavuushäiriö nyt', soon:'Alkaa pian', since:'Ei saatavilla alkaen', starts:'Saatavuushäiriön arvioidaan alkavan', expected:'Arvioitu saatavuus', estimate:'yrityksen arvio', unknown:'Saatavuuden palautumisen ajankohta ei ole tiedossa.', late:'Arvioitu päättymispäivä on ylittynyt', days:n=>`${n} ${n === 1 ? 'päivä' : 'päivää'}`, details:'Lisätiedot', strength:'Vahvuus', substance:'Vaikuttava aine', company:'Yritys', reported:'Ilmoituspäivä', unavailable:'Nimi ei tiedossa', group:'Mihin lääkeryhmään kuuluu', noGroup:'Lääkeryhmää ei ole ilmoitettu', form:'Alkuperäinen lääkemuoto', otherForm:'Muu lääkemuoto'}
};
let language = 'en';
// Ordered so specific forms are matched before general ingredients of their names.
const forms = [
  ['silmätipat','Eye drops','Silmätipat'], ['korvatipat','Ear drops','Korvatipat'], ['nenäsumute','Nasal spray','Nenäsumute'],
  ['inhalaatio','Inhaled medicine','Inhalaatiolääke'], ['injektio','Injection','Injektioneste'], ['infuusio','Infusion','Infuusioneste'],
  ['emulsiovoide','Cream','Emulsiovoide'], ['purutabletti','Chewable tablet','Purutabletti'], ['resoribletti','Tablet dissolved under the tongue','Resoribletti'],
  ['tabletti','Tablet','Tabletti'], ['kapseli','Capsule','Kapseli'], ['laastari','Patch','Laastari'],
  ['oraaliliuos','Oral solution','Oraaliliuos'], ['oraalisuspensio','Oral suspension','Oraalisuspensio'],
  ['voide','Cream or ointment','Voide'], ['geeli','Gel','Geeli'], ['shampoo','Shampoo','Sampoo'], ['peräpuikko','Suppository','Peräpuikko']
];
const groups = {A:['Digestive and metabolic medicines','Ruoansulatuksen ja aineenvaihdunnan lääkkeet'], B:['Blood medicines','Veren lääkkeet'], C:['Heart and blood pressure medicines','Sydän- ja verenpainelääkkeet'], D:['Skin medicines','Iholääkkeet'], G:['Urinary and reproductive health medicines','Virtsateiden ja lisääntymisterveyden lääkkeet'], H:['Hormone medicines','Hormonilääkkeet'], J:['Medicines for infections','Infektiolääkkeet'], L:['Cancer and immune system medicines','Syöpä- ja immuunijärjestelmän lääkkeet'], M:['Muscle and joint medicines','Lihas- ja nivelsairauksien lääkkeet'], N:['Nervous system medicines','Hermoston lääkkeet'], P:['Medicines for parasites','Loislääkkeet'], Q:['Veterinary medicines','Eläinlääkkeet'], R:['Breathing and allergy medicines','Hengitystie- ja allergialääkkeet'], S:['Eye and ear medicines','Silmä- ja korvalääkkeet'], V:['Other medicines','Muut lääkkeet']};
function parsedDate(s) { if (!/^\d{4}-\d{2}-\d{2}$/.test(s || '')) return null; const d = new Date(`${s}T00:00:00Z`); return Number.isNaN(d.valueOf()) ? null : d; }
const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
function formatDate(d) { return language === 'fi' ? `${d.getUTCDate()}.${d.getUTCMonth()+1}.${d.getUTCFullYear()}` : `${d.getUTCDate()} ${months[d.getUTCMonth()]} ${d.getUTCFullYear()}`; }
function dateText(s) { const d=parsedDate(s); return d ? formatDate(d) : '—'; }
function timestampText(s) { const d=new Date(s); return Number.isNaN(d.valueOf()) ? '' : `${formatDate(d)}, ${String(d.getUTCHours()).padStart(2,'0')}:${String(d.getUTCMinutes()).padStart(2,'0')} UTC`; }
function todayUTC() { const parts = new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Helsinki',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date()); const get = type => parts.find(p=>p.type===type).value; return Date.UTC(+get('year'),+get('month')-1,+get('day')); }
function formText(form) {
  if (!form) return '';
  const value = form.toLocaleLowerCase(), fi = language === 'fi';
  if (value.includes('injektio') && value.includes('infuusio')) return fi ? 'Injektio- tai infuusiolääke' : 'Medicine for injection or infusion';
  if ((value.includes('jauhe') || value.includes('kuiva-aine')) && value.includes('injektio')) return fi ? 'Injektiokuiva-aine' : 'Powder for injection';
  if ((value.includes('jauhe') || value.includes('kuiva-aine')) && value.includes('infuusio')) return fi ? 'Infuusiokuiva-aine' : 'Powder for infusion';
  if (value.includes('jauhe') && value.includes('oraaliliuos')) return fi ? 'Jauhe oraaliliuosta varten' : 'Powder for oral solution';
  if (value.includes('jauhe') && value.includes('oraalisuspensio')) return fi ? 'Jauhe oraalisuspensiota varten' : 'Powder for oral suspension';
  const found=forms.find(row => value.includes(row[0])); return found ? found[fi ? 2 : 1] : copy[language].otherForm;
}
function groupName(atc, lang = language) {
  const eyeEar = atc?.startsWith('S01') ? ['Eye medicines','Silmälääkkeet'] : atc?.startsWith('S02') ? ['Ear medicines','Korvalääkkeet'] : null;
  return (eyeEar || groups[(atc || '')[0]])?.[lang === 'fi' ? 1 : 0] || copy[lang].noGroup;
}
function card(e, now) {
  const t=copy[language], start=parsedDate(e.UnavailableFrom), end=parsedDate(e.EndingDate), upcoming=start && start.valueOf()>now;
  const days=start ? Math.floor((now-start.valueOf())/86400000) : null;
  const status=!start ? (language === 'fi' ? 'Alkamispäivä ei tiedossa' : 'Start date unknown') : upcoming ? t.soon : t.out;
  const sentence=start ? `${upcoming ? t.starts : t.since} ${dateText(e.UnavailableFrom)}${!upcoming ? ` (${t.days(days)})` : ''}.` : (language === 'fi' ? 'Alkamispäivä ei ole tiedossa.' : 'Start date not known.');
  const late=end && end.valueOf()<now;
  const expectation=end ? `${t.expected} ${dateText(e.EndingDate)} (${t.estimate}).` : t.unknown;
  const group=groupName(e.atc);
  const details=[[t.form,e.form],[t.strength,e.strength],[t.substance,e.substances],['ATC',e.atc],['VNR',e.NordicArticleNumber],[t.company,e.Company],[t.reported,e.DateOfTheNotification ? dateText(e.DateOfTheNotification) : '']];
  return `<article class="row"><div class="card-heading"><h3>${esc(e.name || t.unavailable)}</h3><span class="status ${upcoming ? 'upcoming' : ''}">${esc(status)}</span></div><p class="form">${esc([formText(e.form),e.pack].filter(Boolean).join(' · '))}</p><p class="group">${esc(t.group)}: ${esc(group)}</p><p class="status-sentence">${esc(sentence)}</p><p>${esc(expectation)} ${late ? `<strong class="late">${esc(t.late)}.</strong>` : ''}</p><details><summary>${esc(t.details)}</summary><dl>${details.map(([label,value])=>`<div><dt>${esc(label)}</dt><dd>${esc(value || '—')}</dd></div>`).join('')}</dl></details></article>`;
}
function drawList() {
  const t=copy[language], query=$('search').value.trim().toLocaleLowerCase();
  const rows=data.events.filter(e=>!e.removed_on && [e.name,e.substances,e.atc,e.Company,e.NordicArticleNumber].some(x=>(x || '').toLocaleLowerCase().includes(query)));
  $('result-count').textContent=`${rows.length} ${t.count}`;
  const now=todayUTC();
  $('list').innerHTML=rows.slice(0,visible).map(e=>card(e,now)).join('') || `<p class="list-state">${esc(t.empty)}</p>`;
  $('more').textContent=t.more; $('more').hidden=visible>=rows.length;
}
function setLanguage() {
  language=$('language').value; $('shortages').lang=language; $('help-title').parentElement.lang=language; const t=copy[language];
  $('help-title').textContent=t.helpTitle; $('help-text').textContent=t.help; $('list-title').textContent=t.title; $('search-hint').textContent=t.hint; $('search').placeholder=t.placeholder; $('search').setAttribute('aria-label',t.placeholder);
  if(data) { drawList(); drawDates(data); }
}
$('language').addEventListener('change',setLanguage);
function bars(id, counts, limit) {
  const entries = Object.entries(counts).sort((a,b) => b[1]-a[1]).slice(0,limit), max = entries[0]?.[1] || 1;
  $(id).innerHTML = entries.map(([name,n]) => `<div class="barrow"><span title="${esc(name)}">${esc(name)}</span><span class="track"><i style="width:${n/max*100}%"></i></span><strong>${n}</strong></div>`).join('');
}
function drawChart(history) {
  if (history.length < 2) { $('chart').textContent = 'A chart will appear when at least two snapshots are available.'; return; }
  const max = Math.max(...history.map(h => h.count),1), first = Date.parse(history[0].date), last = Date.parse(history[history.length-1].date), span = Math.max(last-first, 1);
  const points = history.map(h => `${10 + 380*(Date.parse(h.date)-first)/span},${155 - 140*h.count/max}`).join(' ');
  $('chart').innerHTML = `<svg viewBox="0 0 400 170" role="img" aria-label="Saved snapshot counts from ${esc(dateText(history[0].date))} to ${esc(dateText(history[history.length-1].date))}, latest ${history[history.length-1].count}"><polyline points="${points}" fill="none" stroke="#16806d" stroke-width="2" vector-effect="non-scaling-stroke"/><circle cx="${last === first ? 10 : 390}" cy="${155 - 140*history[history.length-1].count/max}" r="4" fill="#16806d"/></svg><div class="chart-labels"><span>${esc(dateText(history[0].date))}</span><span>${history[history.length-1].count} · ${esc(dateText(history[history.length-1].date))}</span></div>`;
}
function drawDates(d) {
  const meta = d.source_metadata || {}, sourceTimes = [];
  if (meta.shortages_last_modified && timestampText(meta.shortages_last_modified)) sourceTimes.push(`Fimea shortage file: ${timestampText(meta.shortages_last_modified)}`);
  if (meta.register_last_modified && timestampText(meta.register_last_modified)) sourceTimes.push(`Basic register: ${timestampText(meta.register_last_modified)}`);
  $('source-times').textContent = sourceTimes.join('; ');
  $('updated').textContent = `LATEST SNAPSHOT ${dateText(d.snapshot_date)}`; $('start').textContent = dateText(d.archive_start);
  $('history-note').textContent = `History starts on ${dateText(d.archive_start)}. Earlier shortages are not included.`;
  drawChart(d.history);
  const closed = d.events.filter(e => e.removed_on && e.first_estimated_end);
  if ((Date.parse(d.snapshot_date)-Date.parse(d.archive_start))/86400000 >= 28 && closed.length >= 10) $('delay-list').innerHTML = closed.slice(-20).map(e => `<p>${esc(e.name || e.NordicArticleNumber)} · first estimate ${esc(dateText(e.first_estimated_end))} · removed by ${esc(dateText(e.removed_on))}</p>`).join('');
}
fetch('data.json').then(r => {if (!r.ok) throw Error('Data unavailable'); return r.json()}).then(d => {
  data = d; const current = d.events.filter(e => !e.removed_on), companies = {}, atc = {};
  current.forEach(e => {companies[e.Company || 'Unknown'] = (companies[e.Company || 'Unknown'] || 0)+1; const group = e.atc && groupName(e.atc, 'en'); if (group) atc[group] = (atc[group] || 0)+1});
  drawDates(d); $('total').textContent = current.length; $('companies').textContent = Object.keys(companies).length;
  bars('atc', atc, 30); bars('company', companies, 10); drawList();
  const closed = d.events.filter(e => e.removed_on && e.first_estimated_end); const weeks = (Date.parse(d.snapshot_date)-Date.parse(d.archive_start))/86400000;
  if (weeks >= 28 && closed.length >= 10) { $('delay-note').textContent = `${closed.length} observed removals with an initial estimate. Removal dates are the first saved snapshot without the record, not confirmed end dates.`; }
}).catch(() => {$('updated').textContent='Unable to load data'; $('list').textContent='Data could not be loaded. Please try again later.'});
$('search').addEventListener('input', () => {visible=20; if(data) drawList()}); $('more').addEventListener('click', () => {visible+=20; drawList()});
