// Shared code for every page: search, dates, form pictograms, the package card, filters, the timeline model and page set-up.
// The copy lives in i18n.js, one script per page builds on this file.
const $ = id => document.getElementById(id);
const esc = value => String(value || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const queryFromUrl = search => { try { return (new URLSearchParams(search).get('q') || '').trim().slice(0,100); } catch (_) { return ''; } };
const aliases = {parasetamoli:'paracetamol', ibuprofeeni:'ibuprofen', insuliini:'insulin', asetyylisalisyylihappo:'acetylsalicylic acid', amoksisilliini:'amoxicillin', atsitromysiini:'azithromycin', doksisykliini:'doxycycline', metformiini:'metformin', atorvastatiini:'atorvastatin', simvastatiini:'simvastatin', rosuvastatiini:'rosuvastatin', amlodipiini:'amlodipine', bisoprololi:'bisoprolol', metoprololi:'metoprolol', propranololi:'propranolol', losartaani:'losartan', kandesartaani:'candesartan', enalapriili:'enalapril', ramipriili:'ramipril', furosemidi:'furosemide', spironolaktoni:'spironolactone', varfariini:'warfarin', apiksabaani:'apixaban', rivaroksabaani:'rivaroxaban', klopidogreeli:'clopidogrel', omepratsoli:'omeprazole', pantopratsoli:'pantoprazole', esomepratsoli:'esomeprazole', levotyroksiini:'levothyroxine', prednisoloni:'prednisolone', hydrokortisoni:'hydrocortisone', deksametasoni:'dexamethasone', salbutamoli:'salbutamol', budesonidi:'budesonide', formoteroli:'formoterol', setiritsiini:'cetirizine', loratadiini:'loratadine', desloratadiini:'desloratadine', sertraliini:'sertraline', sitalopraami:'citalopram', essitalopraami:'escitalopram', fluoksetiini:'fluoxetine', venlafaksiini:'venlafaxine', duloksetiini:'duloxetine', mirtatsapiini:'mirtazapine', amitriptyliini:'amitriptyline', diatsepaami:'diazepam', oksatsepaami:'oxazepam', tematsepaami:'temazepam', tsolpideemi:'zolpidem', melatoniini:'melatonin', tramadoli:'tramadol', kodeiini:'codeine', morfiini:'morphine', oksikodoni:'oxycodone', gabapentiini:'gabapentin', pregabaliini:'pregabalin', levetirasetaami:'levetiracetam', lamotrigiini:'lamotrigine', karbamatsepiini:'carbamazepine', metotreksaatti:'methotrexate', allopurinoli:'allopurinol', diklofenaakki:'diclofenac', naprokseeni:'naproxen', ketoprofeeni:'ketoprofen', finasteridi:'finasteride', tamsulosiini:'tamsulosin', metronidatsoli:'metronidazole', flukonatsoli:'fluconazole', nitrofurantoiini:'nitrofurantoin', siprofloksasiini:'ciprofloxacin', klindamysiini:'clindamycin', fenoksimetyylipenisilliini:'phenoxymethylpenicillin', asikloviiri:'aciclovir', valasikloviiri:'valaciclovir', ondansetroni:'ondansetron', metoklopramidi:'metoclopramide'};
const fold = s => String(s || '').toLocaleLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
// Page numbers for a long list: at most seven slots, "…" for a gap; the first and last page, the current page and its neighbours always show.
const pageCount = (total, size) => Math.max(1, Math.ceil(total / size));
const clampPage = (page, pages) => Math.min(Math.max(Math.trunc(page) || 1, 1), pages);
// The page number in the address (?page=3): read it, and write it back without touching other parameters. Page 1 leaves no parameter.
const pageFromUrl = (search, pages = Infinity) => { try { const v = new URLSearchParams(search).get('page'); return clampPage(/^\d{1,9}$/.test(v || '') ? Number(v) : 1, pages); } catch (_) { return 1; } };
function pageToUrl(search, page) {
  const params = new URLSearchParams(search);
  if (page > 1) params.set('page', String(page)); else params.delete('page');
  const text = params.toString();
  return text ? '?' + text : '';
}
function pageNumbers(current, pages) {
  if (pages <= 7) return Array.from({length: pages}, (_, i) => i + 1);
  if (current <= 4) return [1, 2, 3, 4, 5, '…', pages];
  if (current >= pages - 3) return [1, '…', pages - 4, pages - 3, pages - 2, pages - 1, pages];
  return [1, '…', current - 1, current, current + 1, '…', pages];
}
// Strengths are stored with decimal points; Finnish readers write and search "2,5".
// Strengths are raw register wording. Finnish readers get a decimal comma; English readers get common Finnish unit words translated. A number and its unit never break apart.
const strengthWords = {tuntia:'hours', tunti:'hour', annosta:'dose', annos:'dose', mikrog:'microg', 'yksikköä':'units', 'yksikkö':'unit', vuorokautta:'day', vuorokausi:'day'};
function strengthText(e) {
  let text=String(e.strength || '').replace(/\s+/g,' ').trim();
  text = language === 'fi' ? text.replace(/(\d)\.(?=\d)/g,'$1,') : text.replace(/(?<=\d )h(?![\p{L}])/gu,'hours').replace(/(?<![\p{L}])(tuntia|tunti|annosta|annos|mikrog|yksikköä|yksikkö|vuorokautta|vuorokausi)(?![\p{L}])/giu, w => strengthWords[w.toLocaleLowerCase()]);
  return text.replace(/(\d) (?=[\p{L}%µ])/gu,'$1\u00a0');
}
const plainText = s => String(s || '').replace(/\u00a0/g,' ').toLocaleLowerCase();
// The strength to show next to a name or pack: nothing when the pack label already starts with it ("10 mg + 2 ml").
function strengthShown(e) {
  const strength=strengthText(e), pack=plainText(packText(e)), own=plainText(strength);
  return !strength || (pack.startsWith(own) && !/^[\p{L}\d.,]/u.test(pack.slice(own.length))) ? '' : strength;
}
function nameWithStrength(e) { const name=e.name || '', strength=strengthShown(e); return !strength || plainText(name).includes(plainText(strength)) ? name : `${name} ${strength}`.trim(); }
const foldNumbers = s => s.replace(/(\d),(?=\d)/g,'$1.');
const NUMBER = /^\d+(?:\.\d*)?$/;
function searchMatches(e, query) {
  const q=foldNumbers(fold(query.trim()));
  const termsFor=word=>[word, ...Object.entries(aliases).filter(([fi])=>{const key=fold(fi); return word.length>=3 && !word.includes(' ') && (key.startsWith(word) || word.startsWith(key.slice(0,-1)));}).map(([,en])=>fold(en))];
  const fields=[e.name,e.strength,e.substances,e.atc,e.Company,e.NordicArticleNumber].map(x=>foldNumbers(fold(x)));
  if (fields.some(x=>termsFor(q).some(term=>x.includes(term)))) return true;
  // Several words match across fields, so "apixaban 5 mg" finds the 5 mg packs of Apixaban Sandoz.
  const words=q.replace(/(^|\s)(\d+(?:\.\d+)?)(mg|g|ml|mikrog|mcg|iu|%)(?=\s|$)/g,'$1$2 $3').split(/\s+/).filter(Boolean).map(word=>word.replace(/^(\d+),$/,'$1.'));
  if (words.length < 2) return false;
  const text=fields.join('\n');
  // A number matches whole numbers only, so "5" does not match "2.5" or "50"; a trailing point allows "2," while typing.
  return words.every(word=>NUMBER.test(word) ? new RegExp(String.raw`(?<![\d.])` + word.replace('.', String.raw`\.`) + (word.endsWith('.') ? '' : String.raw`(?!\d|\.\d)`)).test(text) : termsFor(word).some(term=>text.includes(term)));
}
let language = 'en';
try { const saved = localStorage.getItem('language'); language = ['en','fi'].includes(saved) ? saved : ((navigator.language || '').toLowerCase().startsWith('fi') ? 'fi' : 'en'); } catch (_) { language = (typeof navigator !== 'undefined' && (navigator.language || '').toLowerCase().startsWith('fi')) ? 'fi' : 'en'; }
const numberText = n => new Intl.NumberFormat(language === 'fi' ? 'fi-FI' : 'en-GB').format(n);
// Ordered so specific forms are matched before general ingredients of their names.
const forms = ["silmätipat", "korvatipat", "nenäsumute", "inhalaatio", "injektio", "infuusio", "emulsiovoide", "purutabletti", "resoribletti", "tabletti", "kapseli", "laastari", "oraaliliuos", "oraalisuspensio", "voide", "geeli", "shampoo", "peräpuikko", "peräruisk"];
function parsedDate(s) { if (!/^\d{4}-\d{2}-\d{2}$/.test(s || '')) return null; const d = new Date(`${s}T00:00:00Z`); return Number.isNaN(d.valueOf()) ? null : d; }
const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
function formatDate(d) { return language === 'fi' ? `${d.getUTCDate()}.${d.getUTCMonth()+1}.${d.getUTCFullYear()}` : `${d.getUTCDate()} ${months[d.getUTCMonth()]} ${d.getUTCFullYear()}`; }
function dateText(s) { const d=parsedDate(s); return d ? formatDate(d) : '—'; }
function timestampText(s) { const d=new Date(s); if (Number.isNaN(d.valueOf())) return ''; const parts=new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Helsinki',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(d); const get=k=>parts.find(p=>p.type===k).value; const local=new Date(Date.UTC(+get('year'),+get('month')-1,+get('day'))); return language==='fi' ? `${formatDate(local)} klo ${+get('hour')}.${get('minute')} Suomen aikaa` : `${formatDate(local)}, ${get('hour')}:${get('minute')} Helsinki time`; }
function todayUTC() { const parts = new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Helsinki',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date()); const get = type => parts.find(p=>p.type===type).value; return Date.UTC(+get('year'),+get('month')-1,+get('day')); }
function freshnessInfo(d, now = Date.now(), today = todayUTC()) {
  const t=copy[language], checked=parsedDate(d.last_checked);
  if (checked) return {text:t.checked(dateText(d.last_checked)), stale:today-checked.valueOf()>3*86400000, warning:t.stale};
  const built=d.generated_at && new Date(d.generated_at);
  if (built && !Number.isNaN(built.valueOf())) return {text:`${t.checked(timestampText(d.generated_at))}. ${t.buildOnly}`, stale:now-built.valueOf()>3*86400000, warning:t.staleBuild};
  return {text:'', stale:false, warning:''};
}
// Modified-release and similar forms are named exactly, because a pharmacy does not swap them for ordinary tablets or capsules.
// The form filter still groups them with their pictogram (formKind).
const MODIFIED_FORMS = [
  ['depotInjection', v => v.includes('depot') && v.includes('injekt')],
  ['depotTablet', v => v.includes('depottabletti')],
  ['depotCapsule', v => v.includes('depotkapseli')],
  ['mrTablet', v => v.includes('säädellysti vapauttava') && v.includes('tabletti')],
  ['mrCapsule', v => v.includes('säädellysti vapauttava') && v.includes('kapseli')],
  ['entericTablet', v => v.includes('enterotabletti')],
  ['entericCapsule', v => v.includes('enterokapseli')],
  ['odFilm', v => v.includes('suussa hajoava kalvo')],
  ['odTablet', v => v.includes('suussa hajoava') && v.includes('tabletti')],
  ['dispersibleTablet', v => v.includes('dispergoituva tabletti')],
  ['effervescentTablet', v => v.includes('poretabletti')],
  ['lozenge', v => v.includes('imeskelytabletti')],
  ['sublingualTablet', v => v.includes('kielenalustabletti')]
];
function formText(form) {
  if (!form) return '';
  const value = form.toLocaleLowerCase();
  const modified = MODIFIED_FORMS.find(([, test]) => test(value));
  if (modified) return copy[language]['form_' + modified[0]];
  if (value.includes('injektio') && value.includes('infuusio')) return copy[language].form_combined;
  if ((value.includes('jauhe') || value.includes('kuiva-aine')) && value.includes('injektio')) return copy[language].form_injectionPowder;
  if ((value.includes('jauhe') || value.includes('kuiva-aine')) && value.includes('infuusio')) return copy[language].form_infusionPowder;
  if (value.includes('jauhe') && value.includes('oraaliliuos')) return copy[language].form_oralSolutionPowder;
  if (value.includes('jauhe') && value.includes('oraalisuspensio')) return copy[language].form_oralSuspensionPowder;
  const found=forms.findIndex(part => value.includes(part)); return found >= 0 ? copy[language]['form_'+found] : copy[language].otherForm;
}
function packText(e) { return (e.pack_label && e.pack_label[language]) || e.pack || ''; }
function formAndPack(e) {
  const form=formText(e.form), pack=packText(e);
  // A pack such as "98 tablets" already names the form, so the form is not repeated.
  return form.length > 3 && pack.toLocaleLowerCase().includes(form.toLocaleLowerCase().slice(0,-1)) ? [strengthShown(e),pack] : [form,strengthShown(e),pack];
}
function groupName(atc, lang = language) {
  const key = atc?.startsWith('S01') ? 'eye' : atc?.startsWith('S02') ? 'ear' : (atc || '')[0];
  return copy[lang]['group_'+key] || copy[lang].noGroup;
}

// ---- Form pictograms: one drawing for each kind of medicine form. Drawn on a 48 px grid with a 2.5 px line.
const ICON_PATHS = {
  tablet: '<circle class="fill" cx="24" cy="24" r="16"/><path d="M8 24h32"/>',
  capsule: '<g transform="rotate(-40 24 24)"><path class="fill" d="M24 15h11a9 9 0 0 1 0 18H24z"/><rect x="4" y="15" width="40" height="18" rx="9"/><path d="M24 15v18"/></g>',
  drops: '<rect x="18" y="4" width="12" height="6" rx="1.500"/><path class="fill" d="M16 10h16v13l-4.500 6h-7L16 23z"/><path d="M22 29v4h4v-4"/><path class="fill" d="M24 37c2.500 3 3.500 4.500 3.500 6a3.500 3.500 0 0 1-7 0c0-1.500 1-3 3.500-6z"/>',
  liquid: '<path class="fill" d="M14 29h20v11a3 3 0 0 1-3 3H17a3 3 0 0 1-3-3z"/><rect x="18" y="5" width="12" height="7" rx="2"/><path d="M20 12v4l-6 6v18a3 3 0 0 0 3 3h14a3 3 0 0 0 3-3V22l-6-6v-4"/><path d="M14 29h20"/>',
  injection: '<g transform="rotate(-45 24 24)"><rect class="fill" x="12" y="19" width="20" height="10" rx="2"/><path d="M18 19v4M23 19v4M28 19v4M12 16v16M12 24H5M5 19v10M32 24h12"/></g>',
  tube: '<path class="fill" d="M13 6h22v6L32 37H16L13 12z"/><path d="M13 12h22"/><rect x="18" y="37" width="12" height="7" rx="1.500"/>',
  inhaler: '<rect x="17" y="4" width="14" height="19" rx="3"/><path class="fill" d="M14 23h20v13h8a2.500 2.500 0 0 1 0 5H18a4 4 0 0 1-4-4z"/>',
  spray: '<path class="fill" d="M17 25h16a3 3 0 0 1 3 3v12a3 3 0 0 1-3 3H17a3 3 0 0 1-3-3V28a3 3 0 0 1 3-3z"/><path d="M21 25v-5h8v5M19 20v-6h12v6zM19 17h-6"/><path d="M8 12h.01M6 17h.01M8 22h.01M3 14.500h.01M3 19.500h.01" stroke-width="3.500"/>',
  patch: '<g transform="rotate(-10 24 24)"><rect x="7" y="7" width="34" height="34" rx="10"/><rect class="fill" x="16" y="16" width="16" height="16" rx="1.500"/><path d="M13 36h.01M36 12h.01" stroke-width="3.500"/></g>',
  powder: '<path class="fill" d="M12 6h24v36H12z"/><path d="M12 13h24M12 35h24"/><circle cx="19" cy="22" r="1.500"/><circle cx="28" cy="24" r="1.500"/><circle cx="22" cy="29" r="1.500"/>',
  suppository: '<g transform="rotate(-35 24 24)"><path class="fill" d="M5 24c0-6 6-10 14-10h17a3 3 0 0 1 3 3v14a3 3 0 0 1-3 3H19c-8 0-14-4-14-10z"/></g>',
  other: '<path class="fill" d="M6 16 24 7l18 9v17L24 42 6 33z"/><path d="M6 16l18 9 18-9M24 25v17"/>'
};
const KINDS = Object.keys(ICON_PATHS);
function formKind(form) {
  const v = String(form || '').toLocaleLowerCase();
  if (!v || /kohdun|kohtuun|intrauter|implant/.test(v)) return 'other';
  if (/shampoo|sampoo/.test(v)) return 'liquid';
  if (/injektio|infuusio/.test(v)) return 'injection';
  if (/inhalaa|aerosol/.test(v)) return 'inhaler';
  if (/sumute|suihke|spray/.test(v)) return 'spray';
  if (/jauhe|rakeet|granula|kuiva-aine/.test(v)) return 'powder';
  if (/voide|geeli|pasta|ihotip/.test(v)) return 'tube';
  if (/silmätip|korvatip|silmä|korva/.test(v)) return 'drops';
  if (/laastari/.test(v)) return 'patch';
  if (/puikko|peräruisk|ovuli/.test(v)) return 'suppository';
  if (/kapseli/.test(v)) return 'capsule';
  if (/tabletti|resoribletti|kielenalus/.test(v)) return 'tablet';
  if (/oraali|liuos|suspensio|mikstuura|siirappi|tipat|emulsio/.test(v)) return 'liquid';
  return 'other';
}
function kindLabel(kind) { return copy[language]['kind_' + kind] || copy[language].kind_other; }
function formIcon(kind, size = 40) { return `<svg class="ficon" viewBox="0 0 48 48" width="${size}" height="${size}" aria-hidden="true" focusable="false">${ICON_PATHS[kind] || ICON_PATHS.other}</svg>`; }
// Small interface icons on a 24 px grid.
const UI_PATHS = {
  now: '<path d="M12 3.500 2.500 20h19z"/><path d="M12 10v4.500M12 17.500h.01"/>',
  soon: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  ended: '<circle cx="12" cy="12" r="9"/><path d="m8 12.500 3 3 5-6"/>',
  unknown: '<circle cx="12" cy="12" r="9"/><path d="M9.500 9.500a2.500 2.500 0 1 1 3.500 2.300c-.7.400-1 .9-1 1.700M12 17h.01"/>',
  home: '<path d="M3.500 11 12 4l8.500 7M6 9.500V20h12V9.500"/>',
  list: '<path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01"/>',
  chart: '<path d="M4 20V4M4 20h16M8 15l3-4 3 2 5-7"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.500h.01"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m16.500 16.500 4 4"/>',
  copy: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/>',
  back: '<path d="m15 5-7 7 7 7"/>',
  next: '<path d="m9 5 7 7-7 7"/>',
  filter: '<path d="M4 6h16M7 12h10M10 18h4"/>',
  pill: '<rect x="3" y="8" width="18" height="8" rx="4" transform="rotate(-35 12 12)"/><path d="m9.500 8.500 5 7"/>',
  trend: '<path d="M3 17l6-6 4 4 8-9M15 6h6v6"/>',
  pharmacy: '<path d="M12 4v16M4 12h16"/><rect x="3" y="3" width="18" height="18" rx="5"/>',
  substitute: '<path d="M4 8h14l-3.500-3.500M20 16H6l3.500 3.500"/>',
  critical: '<path d="M5 4.500h14a1.500 1.500 0 0 1 1.500 1.500v9a1.500 1.500 0 0 1-1.500 1.500h-7.500L7 20v-3.500H5A1.500 1.500 0 0 1 3.500 15V6A1.500 1.500 0 0 1 5 4.500z"/><path d="M8 9h8M8 12.500h5"/>',
  nogroup: '<rect x="4" y="4" width="16" height="16" rx="4"/><path d="M8.500 12h7"/>',
  vet: '<circle cx="6.500" cy="10.500" r="1.800"/><circle cx="10" cy="6" r="1.800"/><circle cx="14.500" cy="6" r="1.800"/><circle cx="18" cy="10.500" r="1.800"/><path d="M12 12c-2.500 0-4.500 2.800-4.500 5 0 1.500 1.200 2.500 2.500 2.500.8 0 1.300-.4 2-.4s1.200.4 2 .4c1.300 0 2.500-1 2.500-2.500 0-2.200-2-5-4.500-5z"/>',
  chevron: '<path d="m9 6 6 6-6 6"/>'
};
function uiIcon(name, size = 20) { return `<svg class="uicon" viewBox="0 0 24 24" width="${size}" height="${size}" aria-hidden="true" focusable="false">${UI_PATHS[name]}</svg>`; }

// ---- Status, sorting and filters
const DAY = 86400000;
function statusOf(e, now = todayUTC()) {
  const start = parsedDate(e.UnavailableFrom);
  return !start ? 'unknown' : start.valueOf() > now ? 'soon' : 'now';
}
function statusLabel(status) { return {now: copy[language].out, soon: copy[language].soon, unknown: copy[language].startUnknown}[status]; }
// Current shortages first (newest reported start first), then those starting soon (soonest first).
function defaultCompare(now) {
  const rank = e => ({now: 0, unknown: 0, soon: 1}[statusOf(e, now)]);
  return (a, b) => rank(a) - rank(b) || (rank(a) === 1 ? (a.UnavailableFrom || '').localeCompare(b.UnavailableFrom || '') : (b.UnavailableFrom || '').localeCompare(a.UnavailableFrom || '')) || (a.name || '').localeCompare(b.name || '');
}
function sortPackages(rows, sort, now = todayUTC(), lang = language) {
  const byName = (a, b) => (a.name || '').localeCompare(b.name || '', lang);
  const compare = {
    name: byName,
    longest: (a, b) => (a.UnavailableFrom || '9999').localeCompare(b.UnavailableFrom || '9999') || byName(a, b),
    end: (a, b) => (a.EndingDate || '9999').localeCompare(b.EndingDate || '9999') || byName(a, b)
  }[sort] || defaultCompare(now);
  return rows.slice().sort(compare);
}
function groupKey(atc) { return atc?.startsWith('S01') ? 'eye' : atc?.startsWith('S02') ? 'ear' : (atc || '')[0] || ''; }
function isVet(e) { return (e.atc || '').startsWith('Q'); }
// ---- Impact: can a pharmacy usually give a substitute? The level is set at build time (scripts/triage.py).
const IMPACT_LEVELS = ['substitute', 'critical', 'nogroup', 'vet'];
function impactOf(e) {
  if (IMPACT_LEVELS.includes(e.impact)) return e.impact;
  return isVet(e) ? 'vet' : !e.substitution_group ? 'nogroup' : e.other_packages_count > 0 ? 'substitute' : 'critical';
}
// The plain label with its reason, for a package card and the medicine page.
function impactLine(e) {
  const level = impactOf(e), t = copy[language];
  return level === 'substitute' ? t.impactCard_substitute(e.other_packages_count || 0) : t['impactCard_' + level];
}
function impactBadge(e, tag = 'p') {
  const level = impactOf(e);
  return `<${tag} class="impact impact-${level}">${uiIcon(level, 20)}<span>${esc(impactLine(e))}</span></${tag}>`;
}
// Strengths of one medicine side by side: "10/20/30 mg" when they share a unit, else listed in order.
function mergedStrengths(list) {
  const uniq = [...new Set(list.filter(Boolean))], value = s => parseFloat(s.replace(',', '.'));
  const parts = uniq.map(s => s.match(/^(\d+(?:[.,]\d+)?)\s*(\S.*)$/u));
  // Slashes only between numbers of two digits or more, so "1 g, 2 g" is not read as a half.
  if (parts.length > 1 && parts.every(p => p && value(p[1]) >= 10) && new Set(parts.map(p => p[2])).size === 1) return parts.sort((a, b) => value(a[1]) - value(b[1])).map(p => p[1]).join('/') + '\u00a0' + parts[0][2];
  return uniq.sort((a, b) => (value(a) || 0) - (value(b) || 0) || a.localeCompare(b)).join(', ');
}
// Critical rows grouped by medicine: one row for each active substance and form, with its strengths, product names and packages.
function groupByMedicine(rows, lang = language) {
  const groups = new Map();
  for (const e of rows) {
    const medicine = e.medicine || e.name || '', form = formText(e.form), key = `${fold(medicine)}|${form}`;
    if (!groups.has(key)) groups.set(key, {key, medicine, form, kind: formKind(e.form), packages: []});
    groups.get(key).packages.push(e);
  }
  return [...groups.values()].map(g => ({...g, strength: mergedStrengths(g.packages.map(strengthText)), names: [...new Set(g.packages.map(e => e.name).filter(Boolean))].sort((a, b) => a.localeCompare(b, lang))}))
    .sort((a, b) => a.medicine.localeCompare(b.medicine, lang) || a.form.localeCompare(b.form, lang));
}
const FILTER_KEYS = ['impact', 'status', 'group', 'form', 'company'];
function parseFilters(search) {
  const params = new URLSearchParams(search), pick = (key, max = 100) => (params.get(key) || '').trim().slice(0, max);
  const status = pick('status'), sort = pick('sort'), form = pick('form'), impact = pick('impact');
  return {q: pick('q'), impact: IMPACT_LEVELS.includes(impact) ? impact : '', status: ['now', 'soon'].includes(status) ? status : '', group: pick('group', 10), form: KINDS.includes(form) ? form : '', company: pick('company', 120), sort: ['name', 'longest', 'end'].includes(sort) ? sort : ''};
}
function filtersToQuery(f) {
  const params = new URLSearchParams();
  for (const key of ['q', ...FILTER_KEYS, 'sort']) if (f[key]) params.set(key, f[key]);
  return params.toString();
}
function filterPackages(rows, f, now = todayUTC()) {
  return rows.filter(e => (!f.q || searchMatches(e, f.q)) && (!f.impact || impactOf(e) === f.impact) && (!f.status || statusOf(e, now) === f.status || (f.status === 'now' && statusOf(e, now) === 'unknown')) && (!f.group || groupKey(e.atc) === f.group) && (!f.form || formKind(e.form) === f.form) && (!f.company || e.Company === f.company));
}
const relevant = rows => rows.filter(e => !e.removed_on);

// ---- Package card: the shelf label. Status tab, pictogram, name, strength and pack, form and group, dates.
const daysBetween = (from, to) => Math.floor((to - from) / DAY);
function pkgCard(e, now = todayUTC(), level = 3) {
  const t = copy[language], start = parsedDate(e.UnavailableFrom), end = parsedDate(e.EndingDate), status = statusOf(e, now);
  const late = status === 'now' && end && end.valueOf() < now;
  const spec = [strengthShown(e), packText(e)].filter(Boolean), kind = formKind(e.form), formName = formText(e.form), group = groupName(e.atc);
  const startNote = !start ? '' : status === 'soon' ? t.inDays(daysBetween(now, start.valueOf())) : t.daysAgo(daysBetween(start.valueOf(), now));
  const vnr = e.NordicArticleNumber || '';
  return `<article class="pkg pkg-${status}"><p class="pkg-tab">${uiIcon(status === 'soon' ? 'soon' : status === 'unknown' ? 'unknown' : 'now', 18)}<span>${esc(statusLabel(status))}</span></p>`
    + `<div class="pkg-main"><span class="pkg-icon" title="${esc(kindLabel(kind))}">${formIcon(kind, 40)}</span><div class="pkg-id"><h${level} class="pkg-name"><a href="medicine.html?vnr=${esc(vnr)}">${esc(e.name || t.unavailable)}</a></h${level}>`
    + (spec.length ? `<p class="form pkg-spec">${spec.map(x => `<span>${esc(x)}</span>`).join(' ')}</p>` : '')
    + `<p class="pkg-kind">${[formName, group].filter(Boolean).map(x => `<span>${esc(x)}</span>`).join('')}${isVet(e) ? `<span class="vet">${esc(t.veterinary)}</span>` : ''}</p></div></div>`
    + `<dl class="pkg-dates"><div><dt>${esc(status === 'soon' ? t.startsLabel : t.fromLabel)}</dt><dd>${esc(dateText(e.UnavailableFrom))}${startNote ? `<small>${esc(startNote)}</small>` : ''}</dd></div>`
    + `<div><dt>${esc(t.backLabel)}</dt><dd>${end ? esc(dateText(e.EndingDate)) : esc(t.notKnown)}${late ? `<small class="late">${esc(t.late)}</small>` : ''}</dd></div></dl>`
    + (e.removed_on ? '' : impactBadge(e)) + '</article>';
}

// ---- Timeline model for one package: where the reported start, today and the company's estimate fall.
function timelineModel(e, now = todayUTC()) {
  const start = parsedDate(e.UnavailableFrom), end = parsedDate(e.EndingDate), status = statusOf(e, now);
  const changes = (e.end_changes || []).filter(c => c.date), earlier = [];
  for (const c of changes) if (c.date !== e.EndingDate && !earlier.some(x => x.date === c.date)) earlier.push({date: c.date, seen: c.seen});
  const current = changes.filter(c => c.date === e.EndingDate).pop();
  const late = Boolean(status === 'now' && end && end.valueOf() < now);
  const points = [start && {key: 'start', at: start.valueOf()}, {key: 'today', at: now}, end && {key: 'end', at: end.valueOf()}].filter(Boolean);
  const lo = Math.min(...points.map(p => p.at)), hi = Math.max(...points.map(p => p.at)), span = Math.max(hi - lo, DAY);
  const pos = at => (at - lo) / span;
  return {status, late, hasEnd: Boolean(end), earlier, currentSeen: current ? current.seen : '',
    daysSinceStart: start && status === 'now' ? daysBetween(start.valueOf(), now) : null, daysUntilStart: start && status === 'soon' ? daysBetween(now, start.valueOf()) : null,
    daysPastEstimate: late ? daysBetween(end.valueOf(), now) : null, daysToEstimate: end && !late ? daysBetween(now, end.valueOf()) : null,
    marks: points.map(p => ({key: p.key, pos: pos(p.at)})), order: points.slice().sort((a, b) => a.at - b.at || (a.key === 'today' ? 1 : -1)).map(p => p.key)};
}

// ---- Page set-up: language, static text, shared links, stale warning and footer.
function applyStatic() {
  const t = copy[language], page = document.documentElement.dataset.page;
  document.documentElement.lang = language;
  if (t['title_' + page]) document.title = t['title_' + page];
  const description = document.querySelector('meta[name="description"]');
  if (description && t['desc_' + page]) description.content = t['desc_' + page];
  document.querySelectorAll('[data-i18n]').forEach(el => { const v = t[el.dataset.i18n]; if (typeof v === 'string') el.textContent = v; });
  document.querySelectorAll('[data-i18n-attr]').forEach(el => el.dataset.i18nAttr.split(';').forEach(pair => { const [name, key] = pair.split('='); if (typeof t[key] === 'string') el.setAttribute(name, t[key]); }));
  document.querySelectorAll('[data-feed]').forEach(el => { el.href = language === 'fi' ? 'feed-fi.xml' : 'feed.xml'; });
  document.querySelectorAll('[data-fimea]').forEach(el => { el.href = ({group: language === 'fi' ? 'https://fimea.fi/myyntiluvat/laakevaihto' : 'https://fimea.fi/en/marketing_authorisations/interchangeable_medicinal_products', search: t.moreInfoUrl, data: language === 'fi' ? 'https://fimea.fi/avoin_data' : 'https://fimea.fi/en/about_us/open-data'})[el.dataset.fimea]; });
  document.querySelectorAll('[data-lang-btn]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.langBtn === language)));
}
function renderChrome(d) {
  const t = copy[language], meta = d.source_metadata || {}, times = [];
  if (meta.shortages_last_modified && timestampText(meta.shortages_last_modified)) times.push(`${t.shortageFile}: ${timestampText(meta.shortages_last_modified)}`);
  if (meta.register_last_modified && timestampText(meta.register_last_modified)) times.push(`${t.register}: ${timestampText(meta.register_last_modified)}`);
  const checked = parsedDate(d.last_checked), snapshot = parsedDate(d.snapshot_date), newer = checked && snapshot && d.snapshot_date > d.last_checked;
  const freshness = freshnessInfo(d), show = !newer && freshness.text;
  if ($('source-times')) $('source-times').textContent = [t.latest(dateText(d.snapshot_date)), show ? freshness.text : '', ...times].filter(Boolean).map(x => x.replace(/\.$/, '')).join('. ') + '.';
  if ($('stale')) { const stale = !newer && freshness.stale; $('stale').hidden = !stale; $('stale-text').textContent = stale ? freshness.warning : ''; }
}
function setLanguage(next, render) {
  language = next;
  try { localStorage.setItem('language', language); } catch (_) {}
  applyStatic(); if (render) render();
}
function start(render) {
  document.querySelectorAll('[data-lang-btn]').forEach(b => b.addEventListener('click', () => setLanguage(b.dataset.langBtn, render)));
  applyStatic(); if (render) render();
  document.documentElement.classList.remove('i18n-pending');
  document.documentElement.dataset.appReady = 'true';
}
const fetchJson = url => fetch(url).then(r => { if (!r.ok) throw Error(url); return r.json(); });
let currentPromise;
const loadCurrent = () => currentPromise || (currentPromise = fetchJson('current.json'));
let summaryPromise;
const loadSummary = () => summaryPromise || (summaryPromise = fetchJson('summary.json'));
function showLoadError() {
  const error = $('load-error'), loading = $('loading');
  if (error) error.hidden = false;
  if (loading) loading.hidden = true;
}
function renderCitation(d) {
  if (!$('citation')) return;
  $('citation').textContent = copy[language].citation(dateText(d.snapshot_date), formatDate(new Date(todayUTC())));
  if ($('cite-box')) $('cite-box').hidden = false;
}
function wireCitation() {
  const button = $('copy-cite'); if (!button) return;
  button.addEventListener('click', () => {
    const select = () => { const range = document.createRange(); range.selectNodeContents($('citation')); const selection = getSelection(); selection.removeAllRanges(); selection.addRange(range); };
    const done = () => { $('copy-status').textContent = copy[language].copied; setTimeout(() => { $('copy-status').textContent = ''; }, 2500); };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText($('citation').textContent).then(done, select); else select();
  });
}
