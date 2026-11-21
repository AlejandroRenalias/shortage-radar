let data, visible = 20;
const $ = id => document.getElementById(id);
const esc = value => String(value || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const copy = {
  en: {brand: 'SHORTAGE RADAR', languageLabel: 'Language', form_0:"Eye drops", form_1:"Ear drops", form_2:"Nasal spray", form_3:"Inhaled medicine", form_4:"Injection", form_5:"Infusion", form_6:"Cream", form_7:"Chewable tablet", form_8:"Tablet dissolved under the tongue", form_9:"Tablet", form_10:"Capsule", form_11:"Patch", form_12:"Oral solution", form_13:"Oral suspension", form_14:"Cream or ointment", form_15:"Gel", form_16:"Shampoo", form_17:"Suppository", form_18:"Enema", group_A:"Digestive and metabolic medicines", group_B:"Blood medicines", group_C:"Heart and blood pressure medicines", group_D:"Skin medicines", group_G:"Urinary and reproductive health medicines", group_H:"Hormone medicines", group_J:"Medicines for infections", group_L:"Cancer and immune system medicines", group_M:"Muscle and joint medicines", group_N:"Nervous system medicines", group_P:"Medicines for parasites", group_Q:"Veterinary medicines", group_R:"Breathing and allergy medicines", group_S:"Eye and ear medicines", group_V:"Other medicines", form_combined:"Medicine for injection or infusion", form_injectionPowder:"Powder for injection", form_infusionPowder:"Powder for infusion", form_oralSolutionPowder:"Powder for oral solution", form_oralSuspensionPowder:"Powder for oral suspension", group_eye:"Eye medicines", group_ear:"Ear medicines", chartAria:(a,b,n)=>`Saved snapshot counts from ${a} to ${b}, latest ${n}`, latest:d=>`LATEST SNAPSHOT ${d}`, country:"/ FINLAND", aboutLink:"About the data ↗", openData:"FIMEA OPEN DATA", heading:"Medicine shortages", headingPlace:"in Finland.", intro:"A clearer view of reported medicine shortages, updated from Fimea’s open data.", aboutTitle:"ABOUT THIS DATA", aboutText:"Includes current shortages and those expected to begin within two weeks. A listing does not tell you whether a medicine is available at your pharmacy.", overview:"Overview", statShortages:"LISTED SHORTAGES", statCurrent:"Current and upcoming", statCompanies:"COMPANIES", statHolders:"Marketing authorisation holders", statArchive:"ARCHIVE STARTED", statArchiveNote:"History begins on this date", listKicker:"01 / THE LIST", searchLabel:"Search shortages", packageLevel:"FIMEA · PACKAGE LEVEL", pictureKicker:"02 / THE PICTURE", pictureTitle:"Where shortages appear", pictureText:"Counts represent listed shortage records, not unique medicines.", byGroup:"By medicine group", byCompany:"By company", topTen:"top 10", historyKicker:"03 / OVER TIME", historyTitle:"A history, starting here.", historyText:"Snapshots are saved when the source changes. Gaps do not prove daily observations, and removal from the list is not proof of actual supply.", chartLabel:"Shortage counts by saved snapshot", delayKicker:"04 / DELAYS", delayTitle:"Estimated end vs. list removal", noticeTitle:"Not medical advice.", noticeText:"Ask a pharmacist or doctor about your medicines.", footerAgency:"Finnish Medicines Agency Fimea", footerTransform:"Data was selected, joined and transformed.", footerNote:"Source dates are HTTP Last-Modified times; publisher release times are not provided. Interchangeable groups are not substitution recommendations.", sourceLink:"Source and licence ↗", pageTitle:"Shortage Radar — Finland", description:"A clearer view of reported medicine shortages in Finland.", loading:"Loading shortages…", loadingData:"Loading data…", loadError:"Unable to load data", listError:"Data could not be loaded. Please try again later.", startUnknown:"Start date unknown", startUnknownSentence:"Start date not known.", chartEmpty:"A chart will appear when at least two snapshots are available.", unknownCompany:"Unknown", delayEmpty:"Needs more weeks of data.", firstEstimate:"first estimate", removedBy:"removed by", shortageFile:"Fimea shortage file", register:"Basic register", helpTitle:'What is a shortage?', help:'The company has told Fimea it cannot deliver this package for a while. Your pharmacy may still have some. Ask your pharmacy what is available. This site is not medical advice.', title:'Reported shortages', hint:'Search by medicine, active substance, ATC, company or VNR.', placeholder:'Search your medicine, e.g. Burana', count:n=>`${numberText(n)} ${n === 1 ? 'record' : 'records'}`, more:'Show more', empty:'No medicines match your search. Try another name or number.', out:'Out now', soon:'Starts soon', since:'Not available since', starts:'Expected to become unavailable on', expected:'Expected back around', estimate:"the company’s estimate", unknown:'Return date not known.', late:'Later than estimated', days:n=>`${numberText(n)} ${n === 1 ? 'day' : 'days'}`, details:'Details', strength:'Strength', substance:'Active substance', company:'Company', reported:'Report date', unavailable:'Name unavailable', group:'What is it for', noGroup:'Group not listed', form:'Original form', otherForm:'Other form'},
  fi: {brand: 'SAATAVUUSTUTKA', languageLabel: 'Kieli', form_0:"Silmätipat", form_1:"Korvatipat", form_2:"Nenäsumute", form_3:"Inhalaatiolääke", form_4:"Injektioneste", form_5:"Infuusioneste", form_6:"Emulsiovoide", form_7:"Purutabletti", form_8:"Kielen alle liukeneva tabletti", form_9:"Tabletti", form_10:"Kapseli", form_11:"Laastari", form_12:"Oraaliliuos", form_13:"Oraalisuspensio", form_14:"Voide", form_15:"Geeli", form_16:"Sampoo", form_17:"Peräpuikko", form_18:"Peräruiske", group_A:"Ruoansulatuksen ja aineenvaihdunnan lääkkeet", group_B:"Veren ja verenkierron lääkkeet", group_C:"Sydän- ja verenpainelääkkeet", group_D:"Iholääkkeet", group_G:"Virtsateiden ja lisääntymisterveyden lääkkeet", group_H:"Hormonilääkkeet", group_J:"Infektiolääkkeet", group_L:"Syöpä- ja immuunijärjestelmän lääkkeet", group_M:"Lihas- ja nivelsairauksien lääkkeet", group_N:"Hermoston lääkkeet", group_P:"Loislääkkeet", group_Q:"Eläinlääkkeet", group_R:"Hengitystie- ja allergialääkkeet", group_S:"Silmä- ja korvalääkkeet", group_V:"Muut lääkkeet", form_combined:"Injektio- tai infuusiolääke", form_injectionPowder:"Injektiokuiva-aine", form_infusionPowder:"Infuusiokuiva-aine", form_oralSolutionPowder:"Jauhe oraaliliuosta varten", form_oralSuspensionPowder:"Jauhe oraalisuspensiota varten", group_eye:"Silmälääkkeet", group_ear:"Korvalääkkeet", chartAria:(a,b,n)=>`Tallennettujen tilannekuvien ilmoitusmäärät ${a}–${b}, viimeisin ${n}`, latest:d=>`VIIMEISIN TILANNEKUVA ${d}`, country:"/ SUOMI", aboutLink:"Tietoa aineistosta ↗", openData:"FIMEAN AVOIN DATA", heading:"Lääkkeiden", headingPlace:"saatavuushäiriöt Suomessa.", intro:"Selkeä näkymä ilmoitettuihin lääkkeiden saatavuushäiriöihin Fimean avoimen datan perusteella.", aboutTitle:"TIETOA AINEISTOSTA", aboutText:"Mukana ovat nykyiset häiriöt ja kahden viikon kuluessa alkaviksi arvioidut häiriöt. Ilmoitus ei kerro, onko lääkettä saatavilla omassa apteekissasi.", overview:"Yhteenveto", statShortages:"ILMOITETUT HÄIRIÖT", statCurrent:"Nykyiset ja tulevat", statCompanies:"YRITYKSET", statHolders:"Myyntiluvan haltijat", statArchive:"ARKISTO ALKANUT", statArchiveNote:"Historia alkaa tästä päivästä", listKicker:"01 / LISTA", searchLabel:"Hae saatavuushäiriöitä", packageLevel:"FIMEA · PAKKAUSTASO", pictureKicker:"02 / YLEISKUVA", pictureTitle:"Missä häiriöitä esiintyy", pictureText:"Luvut kuvaavat ilmoituksia, eivät yksittäisten lääkkeiden määrää.", byGroup:"Lääkeryhmittäin", byCompany:"Yrityksittäin", topTen:"10 suurinta", historyKicker:"03 / AIKANA", historyTitle:"Historia alkaa tästä.", historyText:"Tilannekuva tallennetaan, kun lähdeaineisto muuttuu. Aukot eivät osoita päivittäisiä havaintoja, eikä listalta poistuminen todista, että lääkettä on saatavilla.", chartLabel:"Ilmoitusten määrä tallennetuissa tilannekuvissa", delayKicker:"04 / VIIVEET", delayTitle:"Arvioitu päättyminen ja listalta poistuminen", noticeTitle:"Tämä ei ole lääketieteellinen neuvo.", noticeText:"Kysy lääkkeistäsi apteekista tai lääkäriltä.", footerAgency:"Lääkealan turvallisuus- ja kehittämiskeskus Fimea", footerTransform:"Aineistoa on valikoitu, yhdistetty ja muokattu.", footerNote:"Lähteiden ajankohdat ovat HTTP Last-Modified -aikoja; julkaisija ei ilmoita julkaisuaikoja. Vaihtokelpoisten lääkkeiden ryhmät eivät ole suosituksia lääkkeen vaihtamisesta.", sourceLink:"Lähde ja lisenssi ↗", pageTitle:"Saatavuustutka — Suomi", description:"Selkeä näkymä Suomessa ilmoitettuihin lääkkeiden saatavuushäiriöihin.", loading:"Ladataan saatavuushäiriöitä…", loadingData:"Ladataan tietoja…", loadError:"Tietojen lataaminen epäonnistui", listError:"Tietoja ei voitu ladata. Yritä myöhemmin uudelleen.", startUnknown:"Alkamispäivä ei tiedossa", startUnknownSentence:"Alkamispäivä ei ole tiedossa.", chartEmpty:"Kaavio tulee näkyviin, kun vähintään kaksi tilannekuvaa on tallennettu.", unknownCompany:"Ei tiedossa", delayEmpty:"Tietoja tarvitaan useammalta viikolta.", firstEstimate:"ensimmäinen arvio", removedBy:"poistunut listalta", shortageFile:"Fimean saatavuushäiriötiedosto", register:"Perusrekisteri", helpTitle:'Mitä saatavuushäiriö tarkoittaa?', help:'Yritys on ilmoittanut Fimealle, ettei se voi toimittaa tätä pakkausta vähään aikaan. Apteekissa sitä voi silti olla. Kysy apteekista, mitä on saatavilla. Tämä sivusto ei anna lääketieteellisiä neuvoja.', title:'Ilmoitetut saatavuushäiriöt', hint:'Hae lääkkeen tai vaikuttavan aineen nimellä, ATC-koodilla, yrityksellä tai VNR-numerolla.', placeholder:'Hae lääkettä, esim. Burana', count:n=>`${numberText(n)} ${n === 1 ? 'ilmoitus' : 'ilmoitusta'}`, more:'Näytä lisää', empty:'Haulla ei löytynyt lääkkeitä. Kokeile toista nimeä tai numeroa.', out:'Saatavuushäiriö nyt', soon:'Alkaa pian', since:'Saatavuushäiriö alkanut', starts:'Saatavuushäiriön arvioidaan alkavan', expected:'Arvioidaan olevan taas saatavilla noin', estimate:'yrityksen arvio', unknown:'Saatavuuden palautumisen ajankohta ei ole tiedossa.', late:'Arvio on ylittynyt', days:n=>`${numberText(n)} ${n === 1 ? 'päivä' : 'päivää'}`, details:'Lisätiedot', strength:'Vahvuus', substance:'Vaikuttava aine', company:'Yritys', reported:'Ilmoituspäivä', unavailable:'Nimi ei tiedossa', group:'Lääkeryhmä', noGroup:'Lääkeryhmää ei ole ilmoitettu', form:'Alkuperäinen lääkemuoto', otherForm:'Muu lääkemuoto'}
};
Object.assign(copy.en, {
  archiveCredit: 'Earlier captures:',
  delayBias: ' Shortages still on the list are not counted, so the share past the estimate is likely higher.',
  activePast: (n,date,gap) => ` On ${date}, ${n} shortages were still listed past their first estimated end date and had first been seen within ${gap} days of the preceding capture.`,
  savedLegend: '● saved by this project', importedLegend: '○ imported from the Internet Archive',
  capturePoint: (date, count, source) => `${date}: ${count} records (${source})`, savedSource: 'saved by this project', importedSource: 'imported from the Internet Archive',
  noCaptures: n => `no captures · ${n} days`, gapBefore: (n, date) => `${n} days before ${date}`,
  chartSummary: (a,b,n,gaps) => `Capture counts from ${a} to ${b}; latest ${n}.${gaps ? ` Gaps without captures: ${gaps} days.` : ''}`,
  historySummary: (total,date,imported,own,gaps,first) => `${total} captures since ${date}: ${imported} imported from the Internet Archive and ${own} saved by this project.${gaps ? ` Longer gaps without captures: ${gaps}.` : ''} ${first} records were already listed at the first capture, so their start is unknown. The chart does not interpolate across gaps.`,
  rssSummary: items => `Earlier counts from archived copies of Fimea's RSS feed: ${items}. These items have no VNR and cannot be compared with package counts above.`, rssItem: (date,n) => `${date}: ${n} items`,
  delaySample: (n,gap) => `${n} ${n === '1' ? 'shortage' : 'shortages'} entered and left the list within the covered period, with captures at most ${gap} days apart at both ends. Left the list means the record was absent from a later capture; it does not prove the medicine is back.`,
  delayResult: (past,notPast,unknown,min,max) => ` Of these, ${past} were still listed after the first estimated end date, ${notPast} had left by then, and ${unknown} cannot be determined between captures. The share listed past the estimate is ${min}–${max}.`,
  delayMedian: range => ` For those still listed past the estimate, the median overrun was ${range} (lower and upper bounds).`, delaySmall: n => ` This is fewer than ${n}, too few for shares or medians.`,
  delayExcluded: (first,noEstimate,start,end,changed) => ` Excluded: ${first} already listed at the first capture, ${noEstimate} without an estimate, ${start} first seen after a long gap, ${end} removed across a long gap, and ${changed} whose package remained listed under a changed record.`,
  delayExamples: 'Longest observed overruns', lastListed: 'last listed', goneBy: 'gone by', dayRange: (a,b) => `${a === b ? a : `${a}–${b}`} days`
});
Object.assign(copy.fi, {
  archiveCredit: 'Aiemmat tallenteet:',
  delayBias: ' Edelleen listalla olevia saatavuushäiriöitä ei lasketa mukaan, joten arvion ylittäneiden todellinen osuus on todennäköisesti suurempi.',
  activePast: (n,date,gap) => ` Tilannekuvassa ${date} oli edelleen listalla ${n} saatavuushäiriötä ensimmäisen arvioidun päättymispäivän jälkeen. Ne oli havaittu ensimmäisen kerran enintään ${gap} päivää edellisen tilannekuvan jälkeen.`,
  savedLegend: '● tämän hankkeen tallentama', importedLegend: '○ Internet Archivesta tuotu',
  capturePoint: (date, count, source) => `${date}: ${count} ilmoitusta (${source})`, savedSource: 'tämän hankkeen tallentama', importedSource: 'Internet Archivesta tuotu',
  noCaptures: n => `ei tilannekuvia · ${n} päivää`, gapBefore: (n,date) => `${n} päivää ennen ${date}`,
  chartSummary: (a,b,n,gaps) => `Tilannekuvien ilmoitusmäärät ${a}–${b}, viimeisin ${n}.${gaps ? ` Aukot ilman tilannekuvia: ${gaps} päivää.` : ''}`,
  historySummary: (total,date,imported,own,gaps,first) => `${total} tilannekuvaa alkaen ${date}: ${imported} tuotu Internet Archivesta ja ${own} tämän hankkeen tallentamaa.${gaps ? ` Pidemmät aukot ilman tilannekuvia: ${gaps}.` : ''} Ensimmäisessä tilannekuvassa oli jo ${first} ilmoitusta, joiden alkamisajankohta ei ole tiedossa. Kaaviossa aukkoja ei täytetä arvioilla.`,
  rssSummary: items => `Fimean RSS-syötteen arkistoiduista kopioista poimittuja aiempia lukumääriä: ${items}. Ilmoituksissa ei ole VNR-numeroa, joten niitä ei voi verrata yllä oleviin pakkausmääriin.`, rssItem: (date,n) => `${date}: ${n} ilmoitusta`,
  delaySample: (n,gap) => `Tarkastelussa on ${n} saatavuushäiriötä, jotka tulivat listalle ja poistuivat siltä tarkastelujaksolla. Tilannekuvien väli oli sekä alussa että lopussa enintään ${gap} päivää. Listalta poistuminen tarkoittaa, ettei ilmoitus näkynyt myöhemmässä tilannekuvassa; se ei todista, että lääkettä on taas saatavilla.`,
  delayResult: (past,notPast,unknown,min,max) => ` Näistä ${past} oli listalla vielä ensimmäisen arvioidun päättymispäivän jälkeen ja ${notPast} oli poistunut siihen mennessä. ${unknown} ilmoituksen osalta asiaa ei voi päätellä tilannekuvista. Arvion jälkeen listalla olleiden osuus on ${min}–${max}.`,
  delayMedian: range => ` Arvion jälkeen listalla olleiden viiveen mediaani oli ${range} (ala- ja yläraja).`, delaySmall: n => ` Määrä on alle ${n}, joten osuuksia tai mediaaneja ei esitetä.`,
  delayExcluded: (first,noEstimate,start,end,changed) => ` Tarkastelusta jätettiin pois ${first} jo ensimmäisessä tilannekuvassa ollutta ilmoitusta, ${noEstimate} ilman arviota, ${start} pitkän aukon jälkeen havaittua, ${end} pitkän aukon aikana poistunutta ja ${changed}, joiden pakkaus jäi listalle muuttuneella ilmoituksella.`,
  delayExamples: 'Pisimmät havaitut viiveet', lastListed: 'viimeksi listalla', goneBy: 'poistunut viimeistään', dayRange: (a,b) => `${a === b ? a : `${a}–${b}`} päivää`
});
let language = 'en';
try { const saved = localStorage.getItem('language'); language = ['en','fi'].includes(saved) ? saved : ((navigator.language || '').toLowerCase().startsWith('fi') ? 'fi' : 'en'); } catch (_) { language = (typeof navigator !== 'undefined' && (navigator.language || '').toLowerCase().startsWith('fi')) ? 'fi' : 'en'; }
const numberText = n => new Intl.NumberFormat(language === 'fi' ? 'fi-FI' : 'en-GB').format(n);
// Ordered so specific forms are matched before general ingredients of their names.
const forms = ["silmätipat", "korvatipat", "nenäsumute", "inhalaatio", "injektio", "infuusio", "emulsiovoide", "purutabletti", "resoribletti", "tabletti", "kapseli", "laastari", "oraaliliuos", "oraalisuspensio", "voide", "geeli", "shampoo", "peräpuikko", "peräruisk"];
function parsedDate(s) { if (!/^\d{4}-\d{2}-\d{2}$/.test(s || '')) return null; const d = new Date(`${s}T00:00:00Z`); return Number.isNaN(d.valueOf()) ? null : d; }
const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
function formatDate(d) { return language === 'fi' ? `${d.getUTCDate()}.${d.getUTCMonth()+1}.${d.getUTCFullYear()}` : `${d.getUTCDate()} ${months[d.getUTCMonth()]} ${d.getUTCFullYear()}`; }
function dateText(s) { const d=parsedDate(s); return d ? formatDate(d) : '—'; }
function timestampText(s) { const d=new Date(s); if (Number.isNaN(d.valueOf())) return ''; const h=String(d.getUTCHours()).padStart(2,'0'), m=String(d.getUTCMinutes()).padStart(2,'0'); return language === 'fi' ? `${formatDate(d)} klo ${h}.${m} UTC` : `${formatDate(d)}, ${h}:${m} UTC`; }
function todayUTC() { const parts = new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Helsinki',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date()); const get = type => parts.find(p=>p.type===type).value; return Date.UTC(+get('year'),+get('month')-1,+get('day')); }
function formText(form) {
  if (!form) return '';
  const value = form.toLocaleLowerCase();
  if (value.includes('injektio') && value.includes('infuusio')) return copy[language].form_combined;
  if ((value.includes('jauhe') || value.includes('kuiva-aine')) && value.includes('injektio')) return copy[language].form_injectionPowder;
  if ((value.includes('jauhe') || value.includes('kuiva-aine')) && value.includes('infuusio')) return copy[language].form_infusionPowder;
  if (value.includes('jauhe') && value.includes('oraaliliuos')) return copy[language].form_oralSolutionPowder;
  if (value.includes('jauhe') && value.includes('oraalisuspensio')) return copy[language].form_oralSuspensionPowder;
  const found=forms.findIndex(part => value.includes(part)); return found >= 0 ? copy[language]['form_'+found] : copy[language].otherForm;
}
function groupName(atc, lang = language) {
  const key = atc?.startsWith('S01') ? 'eye' : atc?.startsWith('S02') ? 'ear' : (atc || '')[0];
  return copy[lang]['group_'+key] || copy[lang].noGroup;
}
function card(e, now) {
  const t=copy[language], start=parsedDate(e.UnavailableFrom), end=parsedDate(e.EndingDate), upcoming=start && start.valueOf()>now;
  const days=start ? Math.floor((now-start.valueOf())/86400000) : null;
  const status=!start ? t.startUnknown : upcoming ? t.soon : t.out;
  const sentence=start ? `${upcoming ? t.starts : t.since} ${dateText(e.UnavailableFrom)}${!upcoming ? ` (${t.days(days)})` : ''}.` : t.startUnknownSentence;
  const late=end && end.valueOf()<now;
  const expectation=end ? `${t.expected} ${dateText(e.EndingDate)} (${t.estimate}).` : t.unknown;
  const group=groupName(e.atc);
  const details=[[t.form,e.form],[t.strength,e.strength],[t.substance,e.substances],['ATC',e.atc],['VNR',e.NordicArticleNumber],[t.company,e.Company],[t.reported,e.DateOfTheNotification ? dateText(e.DateOfTheNotification) : '']];
  return `<article class="row"><div class="card-heading"><h3>${esc(e.name || t.unavailable)}</h3><span class="status ${upcoming ? 'upcoming' : ''}">${esc(status)}</span></div><p class="form">${esc([formText(e.form),e.pack].filter(Boolean).join(' · '))}</p><p class="group">${esc(t.group)}: ${esc(group)}</p><p class="status-sentence">${esc(sentence)}</p><p>${esc(expectation)} ${late ? `<strong class="late">${esc(t.late)}.</strong>` : ''}</p><details><summary>${esc(t.details)}</summary><dl>${details.map(([label,value])=>`<div><dt>${esc(label)}</dt><dd>${esc(value || '—')}</dd></div>`).join('')}</dl></details></article>`;
}
function drawList() {
  const t=copy[language], query=$('search').value.trim().toLocaleLowerCase();
  const rows=data.events.filter(e=>!e.removed_on && [e.name,e.substances,e.atc,e.Company,e.NordicArticleNumber].some(x=>(x || '').toLocaleLowerCase().includes(query)));
  $('result-count').textContent=t.count(rows.length);
  const now=todayUTC();
  $('list').innerHTML=rows.slice(0,visible).map(e=>card(e,now)).join('') || `<p class="list-state">${esc(t.empty)}</p>`;
  $('more').textContent=t.more; $('more').hidden=visible>=rows.length;
}
function setLanguage() {
  language=$('language').value; const t=copy[language];
  document.documentElement.lang=language; document.title=t.pageTitle;
  document.querySelector('meta[name="description"]').content=t.description;
  document.querySelectorAll('[data-i18n]').forEach(el => el.textContent=t[el.dataset.i18n]);
  document.querySelectorAll('[data-i18n-aria]').forEach(el => el.setAttribute('aria-label',t[el.dataset.i18nAria]));
  $('help-title').textContent=t.helpTitle; $('help-text').textContent=t.help; $('list-title').textContent=t.title; $('search-hint').textContent=t.hint; $('search').placeholder=t.placeholder; $('search').setAttribute('aria-label',t.searchLabel);
  try { localStorage.setItem('language',language); } catch (_) {}
  if(data) renderData(); else if (loadFailed) { $('updated').textContent=t.loadError; $('list').textContent=t.listError; } else { $('updated').textContent=t.loadingData; $('list').textContent=t.loading; $('delay-note').textContent=t.delayEmpty; }
}
let loadFailed=false;
$('language').value=language;
$('language').addEventListener('change',setLanguage);
setLanguage();
document.documentElement.classList.remove('i18n-pending');
function bars(id, counts, limit) {
  const entries = Object.entries(counts).sort((a,b) => b[1]-a[1]).slice(0,limit), max = entries[0]?.[1] || 1;
  $(id).innerHTML = entries.map(([name,n]) => `<div class="barrow"><span title="${esc(name)}">${esc(name)}</span><span class="track"><i style="width:${n/max*100}%"></i></span><strong>${numberText(n)}</strong></div>`).join('');
}
function drawChart(history, maxGap) {
  const t=copy[language];
  if (history.length < 2) { $('chart').textContent=t.chartEmpty; return; }
  const day=h=>Date.parse(h.date)/86400000, segments=[];
  history.forEach(h=>{const g=segments[segments.length-1]; if(g && day(h)-day(g[g.length-1])<=maxGap) g.push(h); else segments.push([h]);});
  const lo=0, hi=Math.max(50,Math.ceil(Math.max(...history.map(h=>h.count))/50)*50), y=n=>150-125*n/hi;
  const band=Math.min(26,150/Math.max(1,segments.length-1)), room=350-band*(segments.length-1), spans=segments.map(g=>Math.max(day(g[g.length-1])-day(g[0]),1)), sum=spans.reduce((a,b)=>a+b,0), minimum=Math.min(14,room/segments.length/2);
  const widths=spans.map(s=>minimum+(room-minimum*segments.length)*s/sum); let x0=40, svg='', gaps=[];
  segments.forEach((g,i)=>{
    const w=widths[i], x=h=>g.length===1 ? x0+w/2 : x0+w*(day(h)-day(g[0]))/(day(g[g.length-1])-day(g[0]));
    if(g.length>1) svg+=`<polyline points="${g.map(h=>`${x(h).toFixed(1)},${y(h.count).toFixed(1)}`).join(' ')}" fill="none" stroke="#16806d" stroke-width="1.5" vector-effect="non-scaling-stroke"/>`;
    svg+=g.map(h=>`<circle cx="${x(h).toFixed(1)}" cy="${y(h.count).toFixed(1)}" r="2.6" fill="${h.imported ? '#f7f8f3' : '#16806d'}" stroke="#16806d" stroke-width="1.2"><title>${esc(t.capturePoint(dateText(h.date),numberText(h.count),h.imported ? t.importedSource : t.savedSource))}</title></circle>`).join('');
    x0+=w;
    if(i<segments.length-1) {const days=Math.round(day(segments[i+1][0])-day(g[g.length-1])); gaps.push(numberText(days)); svg+=`<rect x="${x0}" y="10" width="${band}" height="140" fill="#e8f0e9"/>`; x0+=band;}
  });
  const grid=`<text x="36" y="${y(hi)+5}" font-size="14" fill="#536b5e" text-anchor="end">${numberText(hi)}</text><text x="36" y="155" font-size="14" fill="#536b5e" text-anchor="end">${numberText(lo)}</text>`, last=history[history.length-1];
  $('chart').innerHTML=`<svg viewBox="0 0 400 170" role="img" aria-label="${esc(t.chartSummary(dateText(history[0].date),dateText(last.date),numberText(last.count),gaps.join(', ')))}">${grid}${svg}</svg><div class="chart-labels"><span>${esc(dateText(history[0].date))}</span><span>${numberText(last.count)} · ${esc(dateText(last.date))}</span></div><div class="chart-labels"><span>${esc(t.savedLegend)}</span><span>${esc(t.importedLegend)}</span></div>${gaps.length ? `<div class="chart-labels"><span>${esc(gaps.map(g=>t.noCaptures(g)).join('; '))}</span></div>` : ''}`;
}
function drawDelays(d, snapshotDate) {
  const t=copy[language]; if(!d) { $('delay-note').textContent=t.delayEmpty; $('delay-list').innerHTML=''; return; }
  const n=numberText, ex=d.excluded, pct=s=>`${Math.round(s*100)}${language === 'fi' ? ' ' : ''}%`;
  let text=t.delaySample(n(d.sample_size),n(d.max_gap_days));
  if(d.meaningful) { text+=t.delayResult(n(d.past_estimate),n(d.not_past_estimate),n(d.undetermined),pct(d.share_past_min),pct(d.share_past_max)); if(d.past_estimate) text+=t.delayMedian(t.dayRange(n(d.median_overrun_min_days),n(d.median_overrun_max_days))); }
  else text+=t.delaySmall(n(d.min_sample));
  text+=t.delayBias+t.activePast(n(d.active_past_estimate),dateText(snapshotDate),n(d.max_gap_days));
  text+=t.delayExcluded(n(ex.listed_at_first_capture),n(ex.no_estimate),n(ex.wide_start_window),n(ex.wide_removal_window),n(ex.vnr_still_listed));
  $('delay-note').textContent=text;
  $('delay-list').innerHTML=d.meaningful && d.examples.length ? `<h3>${esc(t.delayExamples)}</h3>`+d.examples.map(e=>`<p>${esc(e.name || e.vnr)} · ${esc(t.firstEstimate)} ${esc(dateText(e.first_estimated_end))} · ${esc(t.lastListed)} ${esc(dateText(e.last_seen))} · ${esc(t.goneBy)} ${esc(dateText(e.removed_on))}</p>`).join('') : '';
}
function drawDates(d) {
  const meta = d.source_metadata || {}, sourceTimes = [];
  if (meta.shortages_last_modified && timestampText(meta.shortages_last_modified)) sourceTimes.push(`${copy[language].shortageFile}: ${timestampText(meta.shortages_last_modified)}`);
  if (meta.register_last_modified && timestampText(meta.register_last_modified)) sourceTimes.push(`${copy[language].register}: ${timestampText(meta.register_last_modified)}`);
  $('source-times').textContent = sourceTimes.join('; ');
  $('updated').textContent = copy[language].latest(dateText(d.snapshot_date)); $('start').textContent = dateText(d.archive_start);
  const t=copy[language], own=d.history.filter(h=>!h.imported).length, imported=d.history.length-own;
  const gaps=d.history.filter(h=>h.gap_days>d.max_gap_days).map(h=>t.gapBefore(numberText(h.gap_days),dateText(h.date)));
  $('history-note').textContent=t.historySummary(numberText(d.history.length),dateText(d.archive_start),numberText(imported),numberText(own),gaps.join('; '),numberText(d.events.filter(e=>e.listed_at_first_capture).length));
  const rss=(d.rss_counts || []).filter(c=>c.items);
  $('rss-note').textContent=rss.length ? t.rssSummary(rss.map(c=>t.rssItem(dateText(c.date),numberText(c.items))).join('; ')) : '';
  drawChart(d.history,d.max_gap_days); drawDelays(d.delays,d.snapshot_date);
}
function renderData() {
  const d=data, t=copy[language], current=d.events.filter(e => !e.removed_on), companies={}, atc={};
  current.forEach(e => {const company=e.Company || t.unknownCompany; companies[company]=(companies[company] || 0)+1; const group=e.atc && groupName(e.atc); if(group) atc[group]=(atc[group] || 0)+1;});
  drawDates(d); $('total').textContent=numberText(current.length); $('companies').textContent=numberText(Object.keys(companies).length);
  bars('atc',atc,30); bars('company',companies,10); drawList();
}
fetch('data.json').then(r => {if (!r.ok) throw Error(); return r.json()}).then(d => {data=d; renderData();}).catch(() => {loadFailed=true; setLanguage();});
$('search').addEventListener('input', () => {visible=20; if(data) drawList()}); $('more').addEventListener('click', () => {visible+=20; drawList()});
