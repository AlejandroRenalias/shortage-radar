const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {execFileSync} = require('node:child_process');
const read = name => fs.readFileSync('site/' + name, 'utf8');
const shared = read('i18n.js') + '\n' + read('lib.js');
const context = vm.createContext({Intl, Date, URLSearchParams});
vm.runInContext(shared, context);
const setLanguage = (ctx, lang) => vm.runInContext(`language='${lang}'`, ctx);
const NOW = Date.UTC(2026, 10, 21);
const plain = value => JSON.parse(JSON.stringify(value));
const nb = text => String(text).replace(/ /g, ' ');
const pages = JSON.parse(execFileSync('python', ['-c', "import json,sys;sys.path.insert(0,'scripts');from pages import render_pages;print(json.dumps(render_pages(749)))"], {encoding: 'utf8'}));
// A page environment with a fake document, for the scripts that draw into elements.
function pageEnv(scripts = ['trends.js']) {
  const elements = {};
  const get = id => elements[id] ||= {textContent:'', innerHTML:'', hidden:true, href:'', value:'en', clientWidth:400, dataset:{}, addEventListener(){}, setAttribute(){}};
  const document = {getElementById:get, documentElement:{dataset:{},classList:{remove(){}}}, querySelector:()=>({}), querySelectorAll:()=>[]};
  const env = vm.createContext({Intl, Date, URLSearchParams, matchMedia: () => ({matches: false}), document, navigator:{language:'en'}, localStorage:{getItem:()=>null,setItem(){}}, fetch:()=>new Promise(()=>{}), location:{search:''}});
  vm.runInContext(shared + '\n' + scripts.map(read).join('\n'), env);
  return [env, get];
}

test('initial language is selected without inline scripts', () => {
  const script = read('language.js');
  for (const html of Object.values(pages)) assert.doesNotMatch(html, /<script>/);
  for (const [browser, saved, expected] of [['fi-FI', null, 'fi'], ['en-US', 'fi', 'fi'], ['fi-FI', 'en', 'en']]) {
    const classes = new Set();
    const document = {documentElement: {lang:'en', dataset:{}, classList: {add: name => classes.add(name)}}};
    vm.runInNewContext(script, {document, window:{addEventListener(){}}, navigator:{language:browser}, localStorage:{getItem:() => saved}});
    assert.equal(document.documentElement.lang, expected);
    assert.equal(classes.has('i18n-pending'), expected === 'fi');
  }
});

test('the old address with ?q= on the home page is sent to the shortage list', () => {
  const calls = [];
  const document = {documentElement: {lang:'en', dataset:{page:'index'}, classList: {add(){}}}};
  vm.runInNewContext(read('language.js'), {document, window:{addEventListener(){}}, navigator:{language:'en'}, localStorage:{getItem:() => null}, URLSearchParams, location:{search:'?q=Burana', replace:url => calls.push(url)}});
  assert.deepEqual(calls, ['shortages.html?q=Burana']);
});

test('translations have matching keys and nonempty Finnish values', () => {
  const translations = vm.runInContext('copy', context);
  assert.deepEqual(Object.keys(translations.fi).sort(), Object.keys(translations.en).sort());
  for (const lang of ['en', 'fi']) for (const [key, value] of Object.entries(translations[lang])) {
    const rendered = typeof value === 'function' ? value(2, 'x', '3') : value;
    assert.ok(typeof rendered === 'string' && rendered.trim(), key);
    assert.doesNotMatch(rendered, /→/, key);
  }
});

test('the built pages carry the same English text as the copy file, so a string is changed in one place', () => {
  const en = vm.runInContext('copy.en', context);
  const decode = s => s.replace(/&amp;/g, '&').replace(/&#x27;/g, "'").replace(/&quot;/g, '"');
  let checked = 0;
  for (const [file, html] of Object.entries(pages)) {
    for (const [, key, text] of html.matchAll(/data-i18n="(\w+)"[^>]*>([^<]*)</g)) {
      assert.equal(typeof en[key], 'string', `${file}: unknown key ${key}`);
      assert.equal(decode(text), en[key], `${file}: ${key}`);
      checked++;
    }
    for (const [, pairs] of html.matchAll(/data-i18n-attr="([^"]+)"/g)) for (const pair of pairs.split(';')) assert.equal(typeof en[pair.split('=')[1]], 'string', `${file}: ${pair}`);
  }
  assert.ok(checked > 80);
  assert.match(pages['index.html'], new RegExp(en.heroLine(749).replace('.', '\\.')));
});

test('no label is all capitals, no numbered markers, no middle-dot strings or arrows in the copy', () => {
  const copy = vm.runInContext('copy', context);
  for (const lang of ['en', 'fi']) for (const [key, value] of Object.entries(copy[lang])) {
    const text = typeof value === 'function' ? value(2, 'x', '3') : value;
    assert.doesNotMatch(text, /^[A-ZÄÖÅ0-9 /·]{6,}$/, key);
    assert.doesNotMatch(text, /\s·\s/, key);
  }
  for (const html of Object.values(pages)) { assert.doesNotMatch(html, /class="kicker"|class="eyebrow"/); assert.doesNotMatch(html, />\s*0\d\s*\/</); }
});

test('veterinary and missing medicine groups have clear labels', () => {
  assert.equal(context.groupName('QN02', 'en'), 'Veterinary medicines');
  assert.equal(context.groupName('QN02', 'fi'), 'Eläinlääkkeet');
  assert.equal(context.groupName('', 'en'), 'Group not listed');
});
test('common forms are understandable and unrecognised forms have a fallback', () => {
  setLanguage(context, 'en');
  for (const form of ['depottabletti', 'injektiokuiva-aine', 'infuusiokonsentraatti', 'depotkapseli', 'depotlaastari', 'jauhe oraaliliuosta varten', 'emulsiovoide', 'purutabletti']) {
    assert.notEqual(context.formText(form), 'Other form', form);
  }
  assert.equal(context.formText('unrecognised form'), 'Other form');
  assert.equal(context.formText(''), '');
});

test('every form falls into one of the twelve pictograms, and each pictogram is drawn', () => {
  const expected = {'tabletti':'tablet', 'purutabletti':'tablet', 'tabletti, kalvopäällysteinen':'tablet', 'depottabletti':'tablet', 'kapseli, kova':'capsule', 'depotkapseli, kova':'capsule', 'silmätipat, liuos':'drops', 'korvatipat, liuos':'drops', 'oraaliliuos':'liquid', 'oraalisuspensio':'liquid',
    'shampoo':'liquid', 'injektioneste, liuos':'injection', 'infuusiokonsentraatti, liuosta varten':'injection', 'injektiokuiva-aine ja liuotin, liuosta varten':'injection', 'emulsiovoide':'tube', 'geeli':'tube', 'depotlaastari':'patch', 'jauhe oraaliliuosta varten':'powder', 'rakeet':'powder',
    'inhalaatiojauhe, kapseli, kova':'inhaler', 'inhalaatiosumute, liuos':'inhaler', 'nenäsumute, liuos':'spray', 'transdermaalisumute, liuos':'spray', 'sumute iholle, liuos':'spray',
    'peräpuikko':'suppository', 'depotlääkevalmiste, kohtuun':'other', 'implantaatti silmän lasiaiseen, asetin':'other', 'implantaatti':'other', '':'other'};
  for (const [form, kind] of Object.entries(expected)) assert.equal(context.formKind(form), kind, form);
  const kinds = Array.from(vm.runInContext('KINDS', context));
  assert.equal(kinds.length, 12);
  for (const kind of kinds) { assert.match(context.formIcon(kind), /<svg class="ficon"[^>]*aria-hidden="true"/); assert.notEqual(context.kindLabel(kind), undefined); }
  assert.ok(vm.runInContext("KINDS.every(k => copy.fi['kind_' + k] && copy.en['kind_' + k] && copy.fi['shelf_' + k] && copy.en['shelf_' + k])", context));
});

test('dates use fixed abbreviations and Finnish numeric format', () => {
  assert.equal(context.dateText('2026-09-21'), '21 Sep 2026');
  setLanguage(context, 'fi');
  assert.equal(context.dateText('2026-09-21'), '21.9.2026');
  assert.equal(context.timestampText('2026-11-21T00:30:00Z'), '21.11.2026 klo 2.30 Suomen aikaa');
  setLanguage(context, 'en');
  assert.equal(context.timestampText('2026-07-21T00:30:00Z'), '21 Jul 2026, 03:30 Helsinki time');
});

test('cards link to the medicine page, with labelled dates and a structured name, strength, pack, form and group', () => {
  setLanguage(context, 'fi');
  assert.equal(vm.runInContext('copy.fi.count(1)', context), '1 pakkaus');
  assert.equal(vm.runInContext('copy.fi.count(2)', context), '2 pakkausta');
  assert.equal(context.formText('resoribletti'), 'Kielen alle liukeneva tabletti');
  assert.equal(context.formText('peräruiskeliuos'), 'Peräruiske');
  assert.equal(context.groupName('B01', 'fi'), 'Veren ja verenkierron lääkkeet');
  const html = context.pkgCard({name:'Test', NordicArticleNumber:'123456', UnavailableFrom:'2026-11-06', EndingDate:'2026-12-01', atc:'B01', form:'tabletti', strength:'5 mg', pack_label:{en:'30 tablets', fi:'30 tablettia'}}, NOW);
  assert.match(html, /<a href="medicine\.html\?vnr=123456">Test<\/a>/);
  assert.match(html, /Saatavuushäiriö nyt/);
  assert.match(html, /<dt>Ilmoitettu alkamispäivä<\/dt><dd>6\.11\.2026<small>15 päivää sitten<\/small>/);
  assert.match(html, /<dt>Arvioitu paluu<\/dt><dd>1\.12\.2026<\/dd>/);
  assert.match(nb(html), /<p class="form pkg-spec"><span>5 mg<\/span> <span>30 tablettia<\/span><\/p>/);
  assert.match(html, /<span>Tabletti<\/span><span>Veren ja verenkierron lääkkeet<\/span>/);
  assert.doesNotMatch(html, / · /);
  setLanguage(context, 'en');
  assert.match(context.pkgCard({name:'Test', UnavailableFrom:'2026-12-01', atc:'B01'}, NOW), /Starting soon[\s\S]*<dt>Starts<\/dt><dd>1 Dec 2026<small>in 10 days<\/small>/);
  assert.match(context.pkgCard({name:'Test', UnavailableFrom:'2026-10-01', EndingDate:'2026-11-01', atc:'B01'}, NOW), /<small class="late">Later than estimated<\/small>/);
  assert.match(context.pkgCard({name:'T', atc:'Q02'}, NOW), /<span class="vet">Veterinary<\/span>/);
});

test('Finnish substance aliases and diacritics match English records', () => {
  for (const [query, substance] of [['parasetamoli','paracetamol'], ['ibuprofeeni','ibuprofen'], ['insuliini','insulin']]) {
    assert.ok(context.searchMatches({substances: substance}, query));
  }
  assert.ok(context.searchMatches({name:'Äänekoski'}, 'aanekoski'));
  for (const query of ['parasetam', 'parasetamolia', 'parasetamolit']) assert.ok(context.searchMatches({substances:'paracetamol'},query));
  assert.equal(context.searchMatches({substances:'acetylsalicylic acid'},'as'),false);
  assert.ok(vm.runInContext('Object.keys(aliases).length >= 60', context));
});

test('freshness uses the successful check date and distinguishes a build-only fallback', () => {
  setLanguage(context, 'en');
  const today = Date.UTC(2026, 10, 21);
  const recent = context.freshnessInfo({last_checked:'2026-11-18', generated_at:'2026-11-21T12:00:00Z'}, today, today);
  assert.equal(recent.text, 'Checked 18 Nov 2026');
  assert.equal(recent.stale, false);
  assert.equal(context.freshnessInfo({last_checked:'2026-11-17'}, today, today).stale, true);
  const fallback = context.freshnessInfo({last_checked:null, generated_at:'2026-11-17T00:00:00Z'}, today, today);
  assert.match(fallback.text, /Build time; the last source check is unknown/);
  assert.equal(fallback.stale, true);
  assert.equal(context.freshnessInfo({}, today, today).text, '');
});

test('the stale-data warning is shown on every page that loads data', () => {
  const [env, get] = pageEnv(['home.js']);
  get('stale'); get('stale-text'); get('source-times');
  env.renderChrome({snapshot_date:'2026-11-01', last_checked:'2026-11-01', generated_at:'2026-11-01T00:00:00Z', source_metadata:{}});
  assert.equal(get('stale').hidden, false);
  assert.match(get('stale-text').textContent, /more than 3 days ago/);
  assert.doesNotMatch(get('source-times').textContent, /\.\./);
  const today = new Date().toISOString().slice(0, 10);
  env.renderChrome({snapshot_date:today, last_checked:today, source_metadata:{}});
  assert.equal(get('stale').hidden, true);
  for (const html of Object.entries(pages).filter(([f]) => f !== '404.html')) assert.match(html[1], /id="stale"/);
});

test('history and delay rendering uses translated dates and explains the sample', () => {
  const [env, get] = pageEnv();
  const history = [{date:'2024-11-18',count:670,imported:true},{date:'2026-11-21',count:751,imported:false}];
  const delays = {sample_size:1,active_past_estimate:24,max_gap_days:14,min_sample:30,meaningful:false,excluded:{listed_at_first_capture:0,no_estimate:0,wide_start_window:0,wide_removal_window:0,vnr_still_listed:0},examples:[]};
  env.drawChart(history,14); env.drawDelays(delays,'2026-11-21');
  assert.match(get('chart').innerHTML, /18 Nov 2024/);
  assert.doesNotMatch(get('chart').innerHTML, /2024-11-18/);
  assert.match(get('chart').innerHTML, /no captures, 733 days/);
  assert.match(get('delay-headline').textContent, /1 shortage entered/);
  assert.match(get('delay-note').textContent, /does not prove supply returned/);
  assert.match(get('delay-visual').innerHTML, /24 shortages were still listed/);
  assert.match(get('chart').innerHTML, /font-size="14"[^>]*>650<\/text>/);
  assert.match(get('chart').innerHTML, /font-weight="600"[^>]*>751<\/text>/);
  assert.match(get('chart').innerHTML, /The vertical axis starts at 650\./);
  env.drawTable(history);
  assert.match(get('chart-table').innerHTML, /<td>21 Nov 2026<\/td><td>751<\/td><td>saved by this project<\/td>/);
  vm.runInContext("language='fi'",env);
  env.drawChart(history,14); env.drawDelays(delays,'2026-11-21');
  assert.match(get('chart').innerHTML, /18\.11\.2024/);
  assert.match(get('chart').innerHTML, /ei tilannekuvia/);
  assert.match(get('delay-note').textContent, /ei todista saatavuuden palautumista/);
  delays.meaningful=true; delays.past_estimate=1; delays.not_past_estimate=0; delays.undetermined=0; delays.share_past_min=.1; delays.share_past_max=.6; delays.median_overrun_min_days=1; delays.median_overrun_max_days=2;
  env.drawDelays(delays,'2026-11-21');
  assert.match(get('delay-headline').textContent, /10 %–60 %/);
  assert.match(get('delay-visual').innerHTML, /Listalla arvion jälkeen/);
  env.drawDates({snapshot_date:'2026-11-21',last_checked:'2026-11-20',archive_start:'2024-11-18'});
  assert.equal(get('data-date').textContent, 'Aineisto 21.11.2026');
});

test('pack sizes use the unit and the form is named on its own line', () => {
  setLanguage(context, 'en');
  const tablets = {name:'T', form:'tabletti, kalvopäällysteinen', pack:'98', pack_label:{en:'98 tablets', fi:'98 tablettia'}, atc:'N02'};
  assert.match(context.pkgCard(tablets, NOW), /<p class="form pkg-spec"><span>98 tablets<\/span><\/p>/);
  assert.match(context.pkgCard({...tablets, form:'injektioneste, liuos', pack:'5 ml', pack_label:{en:'5 ml', fi:'5 ml'}}, 0), /<p class="form pkg-spec"><span>5 ml<\/span><\/p><p class="pkg-kind"><span>Injection<\/span>/);
  assert.match(context.pkgCard({...tablets, form:'purutabletti', pack_label:{en:'30 tablets', fi:'30 tablettia'}}, 0), /<span>Chewable tablet<\/span>/);
  assert.match(context.pkgCard({...tablets, pack_label:undefined}, 0), /<span>98<\/span>/);
  setLanguage(context, 'fi');
  assert.match(context.pkgCard(tablets, 0), /<span>98 tablettia<\/span>/);
  setLanguage(context, 'en');
});

test('what to do names the pharmacy and points to Fimea without contact data', () => {
  const copy = vm.runInContext('copy', context);
  assert.match(copy.en.whatText, /^Ask your pharmacy\./);
  assert.match(copy.fi.whatText, /^Kysy apteekista\./);
  assert.equal(copy.en.moreInfo('Example Oy'), 'For more about this package, contact the company (Example Oy).');
  assert.equal(copy.en.moreInfoUrl, 'https://fimea.fi/en/databases_and_registers/shortages');
  assert.equal(copy.fi.moreInfoUrl, 'https://fimea.fi/laakehaut_ja_luettelot/saatavuushairio-uusi');
  assert.doesNotMatch(context.pkgCard({name:'T', atc:'N02', Company:'Example Oy', contact:'CONTACT-PLACEHOLDER'}, 0), /CONTACT-PLACEHOLDER/);
});

test('the q parameter and filters are read from the address and written back', () => {
  const queryFromUrl = search => vm.runInContext('queryFromUrl', context)(search);
  assert.equal(queryFromUrl('?q=599361'), '599361');
  assert.equal(queryFromUrl('?x=1'), '');
  assert.equal(queryFromUrl('?q=%20Burana%20'), 'Burana');
  assert.ok(context.searchMatches({NordicArticleNumber:'599361', name:'Other'}, queryFromUrl('?q=599361')));
  const f = context.parseFilters('?q=burana&status=soon&group=N&form=tablet&company=Orion%20Corporation&sort=name');
  assert.deepEqual({...f}, {q:'burana', impact:'', status:'soon', group:'N', form:'tablet', company:'Orion Corporation', sort:'name'});
  assert.equal(context.filtersToQuery(f), 'q=burana&status=soon&group=N&form=tablet&company=Orion+Corporation&sort=name');
  assert.deepEqual({...context.parseFilters('?status=bogus&form=bogus&sort=bogus&impact=bogus')}, {q:'', impact:'', status:'', group:'', form:'', company:'', sort:''});
  assert.equal(context.filtersToQuery(context.parseFilters('')), '');
});

test('the default order lists current shortages newest first, then those starting soon, soonest first', () => {
  const rows = [
    {name:'Old', UnavailableFrom:'2025-01-01'}, {name:'Soon later', UnavailableFrom:'2026-12-05'}, {name:'New', UnavailableFrom:'2026-11-20'},
    {name:'Soon first', UnavailableFrom:'2026-11-25'}, {name:'Mid', UnavailableFrom:'2026-06-01'}];
  const order = (sort) => Array.from(context.sortPackages(rows, sort, NOW, 'en')).map(e => e.name);
  assert.deepEqual(order(''), ['New', 'Mid', 'Old', 'Soon first', 'Soon later']);
  assert.deepEqual(order('longest'), ['Old', 'Mid', 'New', 'Soon first', 'Soon later']);
  assert.deepEqual(order('name'), ['Mid', 'New', 'Old', 'Soon first', 'Soon later']);
  assert.deepEqual(order('end'), order('end').slice().sort(), 'a missing end date sorts last without throwing');
});

test('filters combine status, group, form and company with the search', () => {
  const rows = [
    {name:'Burana', UnavailableFrom:'2026-10-01', atc:'M01AE01', form:'tabletti, kalvopäällysteinen', Company:'Orion'},
    {name:'Burana gel', UnavailableFrom:'2026-12-01', atc:'M02AA13', form:'geeli', Company:'Orion'},
    {name:'Eye', UnavailableFrom:'2026-10-02', atc:'S01XA', form:'silmätipat, liuos', Company:'Santen'}];
  const run = f => Array.from(context.filterPackages(rows, {q:'', status:'', group:'', form:'', company:'', ...f}, NOW)).map(e => e.name);
  assert.deepEqual(run({}), ['Burana', 'Burana gel', 'Eye']);
  assert.deepEqual(run({status:'soon'}), ['Burana gel']);
  assert.deepEqual(run({status:'now'}), ['Burana', 'Eye']);
  assert.deepEqual(run({group:'M'}), ['Burana', 'Burana gel']);
  assert.deepEqual(run({group:'eye'}), ['Eye']);
  assert.deepEqual(run({form:'tube'}), ['Burana gel']);
  assert.deepEqual(run({company:'Santen'}), ['Eye']);
  assert.deepEqual(run({q:'burana', company:'Orion', status:'now'}), ['Burana']);
});

test('the timeline model places the start, today and the estimate, and reports a late estimate', () => {
  const e = {UnavailableFrom:'2026-11-01', EndingDate:'2026-12-01', end_changes:[{seen:'2026-11-05', date:'2026-11-15'}, {seen:'2026-11-14', date:'2026-12-01'}]};
  const model = context.timelineModel(e, NOW);
  assert.equal(model.status, 'now');
  assert.equal(model.late, false);
  assert.deepEqual(Array.from(model.order), ['start', 'today', 'end']);
  assert.equal(model.daysSinceStart, 20);
  assert.equal(model.daysToEstimate, 10);
  assert.deepEqual(plain(model.earlier.map(x => [x.date, x.seen])), [['2026-11-15', '2026-11-05']]);
  assert.equal(model.currentSeen, '2026-11-14');
  const pos = Object.fromEntries(model.marks.map(m => [m.key, m.pos]));
  assert.equal(pos.start, 0); assert.equal(pos.end, 1); assert.ok(pos.today > 0 && pos.today < 1);
  const late = context.timelineModel({UnavailableFrom:'2026-10-01', EndingDate:'2026-11-11'}, NOW);
  assert.equal(late.late, true); assert.equal(late.daysPastEstimate, 10); assert.equal(late.daysToEstimate, null);
  assert.deepEqual(Array.from(late.order), ['start', 'end', 'today']);
  const soon = context.timelineModel({UnavailableFrom:'2026-11-25', EndingDate:'2026-12-25'}, NOW);
  assert.equal(soon.status, 'soon'); assert.equal(soon.daysUntilStart, 4); assert.deepEqual(Array.from(soon.order), ['today', 'start', 'end']);
  const open = context.timelineModel({UnavailableFrom:'2026-11-01'}, NOW);
  assert.equal(open.hasEnd, false); assert.deepEqual(Array.from(open.order), ['start', 'today']);
});

test('this week summary and how-we-count note state their window and counts', () => {
  const [env, get] = pageEnv();
  const week = {from:'2026-11-13', to:'2026-11-21', days:8, new:77, left:70, count_from:751, count_to:758};
  env.drawWeek(week, 758);
  assert.equal(get('week').hidden, false);
  const facts = get('week-facts').innerHTML;
  assert.match(facts, /<dt>New on the list<\/dt><dd class="fact-num">77<\/dd>/);
  assert.match(facts, /<dt>Left the list<\/dt><dd class="fact-num">70<\/dd>/);
  assert.match(facts, /<dd class="fact-num">758<\/dd><dd class="fact-note">758 now, 751 on 13 Nov 2026<\/dd>/);
  assert.match(facts, /New records listed since 13 Nov 2026, including any that left again\./);
  assert.match(get('week-window').textContent, /capture of 13 Nov 2026, 8 days earlier/);
  assert.equal(get('feed-link').href, 'feed.xml');
  env.drawWeek(null, 758);
  assert.equal(get('week').hidden, true);
  const delays = {sample_size:156,removed_total:1197,max_gap_days:14,min_sample:30,meaningful:false,active_past_estimate:0,excluded:{listed_at_first_capture:642,no_estimate:0,wide_start_window:332,wide_removal_window:0,vnr_still_listed:67},examples:[]};
  env.drawDelays(delays, '2026-11-21');
  assert.equal(get('how-count').hidden, false);
  assert.equal(get('how-count-text').textContent, 'Counted: 156 of the 1,197 records that have left the list. These were first seen and last seen within 14 days of a neighbouring capture and had an estimated end date. Not counted: 642 already listed at the first capture, 332 first seen after a long gap, 67 whose package stayed listed under a changed record.');
  vm.runInContext("language='fi'", env);
  env.drawWeek(week, 758); env.drawDelays(delays, '2026-11-21');
  assert.equal(get('feed-link').href, 'feed-fi.xml');
  assert.match(get('week-facts').innerHTML, /Uudet listalla/);
  assert.match(get('week-facts').innerHTML, /myös ne, jotka ehtivät poistua uudelleen/);
  assert.match(get('how-count-text').textContent, /^Mukana on 156 listalta poistuneesta 1\s197 ilmoituksesta/);
});

test('strength is part of the label, with a Finnish decimal comma', () => {
  const apixaban = {name:'Apixaban Sandoz', strength:'2.5 mg', form:'tabletti, kalvopäällysteinen', pack_label:{en:'60 tablets', fi:'60 tablettia'}, UnavailableFrom:'2026-11-06', atc:'B01'};
  setLanguage(context, 'en');
  assert.deepEqual(plain(context.formAndPack(apixaban)).map(nb), ['2.5 mg', '60 tablets']);
  assert.match(nb(context.pkgCard(apixaban, NOW)), /<span>2\.5 mg<\/span> <span>60 tablets<\/span>/);
  assert.deepEqual(plain(context.formAndPack({form:'injektioneste, liuos', strength:'10 mg/ml', pack:'5 ml'})).map(nb), ['Injection', '10 mg/ml', '5 ml']);
  setLanguage(context, 'fi');
  assert.match(nb(context.pkgCard(apixaban, NOW)), /<span>2,5 mg<\/span> <span>60 tablettia<\/span>/);
  assert.equal(nb(context.nameWithStrength(apixaban)), 'Apixaban Sandoz 2,5 mg');
  setLanguage(context, 'en');
  assert.equal(nb(context.nameWithStrength(apixaban)), 'Apixaban Sandoz 2.5 mg');
  assert.equal(context.nameWithStrength({name:'Burana 400 mg', strength:'400 mg'}), 'Burana 400 mg');
  assert.equal(context.nameWithStrength({name:'Burana'}), 'Burana');
});

test('search finds a package by strength with comma and point folded', () => {
  const two = {name:'Apixaban Sandoz', strength:'2.5 mg', substances:'apixaban', Company:'Sandoz', NordicArticleNumber:'584836'};
  const five = {name:'Apixaban Sandoz', strength:'5 mg', substances:'apixaban', Company:'Sandoz', NordicArticleNumber:'572154'};
  const hits = query => [two, five].filter(e => context.searchMatches(e, query)).map(e => e.strength);
  assert.deepEqual(hits('apixaban 5 mg'), ['5 mg']);
  assert.deepEqual(hits('apixaban 5mg'), ['5 mg']);
  assert.deepEqual(hits('apixaban 2,5'), ['2.5 mg']);
  assert.deepEqual(hits('apiksabaani 2,5 mg'), ['2.5 mg']);
  assert.deepEqual(hits('apixaban 2,'), ['2.5 mg']);
  assert.deepEqual(hits('apixaban sandoz'), ['2.5 mg', '5 mg']);
  assert.deepEqual(hits('apixaban 50 mg'), []);
  assert.deepEqual(hits('584836'), ['2.5 mg']);
});

test('strength is not repeated, never breaks between number and unit, and translates unit words in English only', () => {
  const octreotide = {name:'Octreotide ratiopharm', strength:'10 mg', form:'injektiokuiva-aine', pack:'10 mg + 2 ml', pack_label:{en:'10 mg + 2 ml', fi:'10 mg + 2 ml'}, UnavailableFrom:'2026-11-06', atc:'H01'};
  for (const lang of ['en', 'fi']) {
    setLanguage(context, lang);
    assert.deepEqual(plain(context.formAndPack(octreotide)).filter(Boolean).map(nb), [context.formText(octreotide.form), '10 mg + 2 ml']);
    assert.equal(context.nameWithStrength(octreotide), 'Octreotide ratiopharm');
  }
  setLanguage(context, 'en');
  for (const [raw, en] of [['20 mikrog / 24 tuntia', '20 microg / 24 hours'], ['5 mikrog/tunti', '5 microg/hour'], ['24 h', '24 hours'], ['200 Speywood-yksikköä/ml', '200 Speywood-units/ml'], ['3 mg / vuorokausi', '3 mg / day']]) {
    setLanguage(context, 'en');
    assert.equal(nb(context.strengthText({strength:raw})), en, raw);
    setLanguage(context, 'fi');
    assert.equal(nb(context.strengthText({strength:raw})), raw, raw);
  }
  setLanguage(context, 'en');
});

test('the empty result does not read as "no problem", and the placeholder finds results', () => {
  const copy = vm.runInContext('copy', context);
  assert.equal(copy.en.empty, 'Not on the list. That does not guarantee your pharmacy has it. Try the active substance (for example paracetamol) or ask your pharmacy.');
  assert.match(copy.fi.empty, /parasetamoli/);
  assert.match(copy.en.placeholder, /Burana or ibuprofen/);
  assert.match(copy.fi.placeholder, /Burana tai ibuprofeeni/);
  assert.ok(context.searchMatches({name:'Buranagel', substances:'Ibuprofen'}, 'burana'));
  assert.ok(context.searchMatches({name:'Buranagel', substances:'Ibuprofen'}, 'ibuprofeeni'));
});

test('the citation names the data date and the access date', () => {
  const copy = vm.runInContext('copy', context);
  for (const lang of ['en', 'fi']) {
    const text = copy[lang].citation('21 Nov 2026', '22 Nov 2026');
    assert.match(text, /alejandrorenalias\.github\.io\/shortage-radar\//);
    assert.match(text, /21 Nov 2026/);
    assert.match(text, /22 Nov 2026/);
  }
  assert.match(copy.en.citation('a', 'b'), /accessed b/);
});

test('the pages keep the head tags, the one search, the report link and the citation box', () => {
  const home = pages['index.html'], list = pages['shortages.html'], trends = pages['trends.html'], about = pages['about.html'];
  for (const html of Object.values(pages)) assert.doesNotMatch(html, /hreflang/);
  assert.match(home, /<html lang="en"/);
  assert.match(home, /og:locale" content="en_GB"/);
  assert.match(home, /og:image:alt/);
  assert.equal((list.match(/id="search"/g) || []).length, 1);
  assert.match(list, /id="result-count" aria-live="polite" aria-atomic="true"/);
  assert.match(about, /issues\/new\?template=data-problem\.yml/);
  assert.match(about, /id="citation"/); assert.match(trends, /id="cite-box"/);
  assert.match(trends, /id="chart-table"/);
  assert.ok(fs.existsSync('.github/ISSUE_TEMPLATE/data-problem.yml'));
  assert.ok(fs.existsSync('site/sitemap.xml'));
  assert.match(about, /id="what-to-do"/); assert.match(about, /id="privacy"/); assert.match(about, /id="licence"/);
  assert.doesNotMatch(Object.values(pages).join(''), /https?:\/\/(?!alejandrorenalias|fimea|creativecommons|web\.archive|github)/);
});

test('every current card carries one impact label with its reason, in both languages', () => {
  const record = {name:'Test', UnavailableFrom:'2026-11-06', EndingDate:'2026-12-01', atc:'N02'};
  const cases = [
    [{substitution_group:'0042', other_packages_count:5}, 'substitute', {en:'Pharmacy can usually give a substitute: 5 other packages on the market', fi:'Apteekki voi yleensä vaihtaa valmisteen: kaupan on 5 muuta pakkausta'}],
    [{substitution_group:'0042', other_packages_count:1}, 'substitute', {en:'Pharmacy can usually give a substitute: 1 other package on the market', fi:'Apteekki voi yleensä vaihtaa valmisteen: kaupan on 1 muu pakkaus'}],
    [{substitution_group:'0042', other_packages_count:0}, 'critical', {en:'No interchangeable product on the market. Talk to your pharmacist or doctor early.', fi:'Ei vaihtokelpoista valmistetta kaupan. Kysy apteekista tai lääkäriltä hyvissä ajoin.'}],
    [{other_packages_count:0}, 'nogroup', {en:'No substitution group. Ask your pharmacist.', fi:'Ei vaihtokelpoisuusryhmää. Kysy apteekista.'}],
    [{atc:'QN02', substitution_group:'0042', other_packages_count:3}, 'vet', {en:'Veterinary medicine. Ask your veterinarian or pharmacy.', fi:'Eläinlääke. Kysy eläinlääkäriltä tai apteekista.'}],
  ];
  for (const lang of ['en', 'fi']) {
    setLanguage(context, lang);
    for (const [extra, level, text] of cases) {
      const html = context.pkgCard({...record, ...extra}, NOW);
      assert.equal(context.impactOf({...record, ...extra}), level);
      assert.equal((html.match(/class="impact /g) || []).length, 1);
      assert.ok(html.includes(`<p class="impact impact-${level}">`) && html.includes(`<span>${text[lang]}</span>`), `${lang} ${level}`);
    }
    // The level built into the data wins; a package that left the list has no label.
    assert.equal(context.impactOf({...record, impact:'critical', other_packages_count:4, substitution_group:'1'}), 'critical');
    assert.doesNotMatch(context.pkgCard({...record, removed_on:'2026-11-10'}, NOW), /class="impact /);
  }
  setLanguage(context, 'en');
});

test('the critical wording never says that no medicine or treatment exists, and uses no alarm words', () => {
  const copy = vm.runInContext('copy', context);
  const keys = Object.keys(copy.en).filter(k => /impact|crit|triage|altShort|newCrit/i.test(k));
  for (const lang of ['en', 'fi']) for (const key of keys) {
    const value = copy[lang][key], text = typeof value === 'function' ? value(2, 'x') : value;
    assert.doesNotMatch(text, /no (medicine|treatment) (is )?available|no treatment exists|urgent|danger|warning|alarm|critical/i, `${lang} ${key}`);
    assert.doesNotMatch(text, /ei (ole )?(lääkettä|hoitoa) saatavilla|kiireellinen|vaara|hälytys|kriittinen/i, `${lang} ${key}`);
  }
  // The About text says plainly that the label is not about treatment existing.
  assert.match(copy.en.aboutImpact_critical, /does not mean that there is no treatment/); assert.match(copy.fi.aboutImpact_critical, /ei tarkoita, ettei hoitoa olisi/);
});

test('critical rows group by medicine and form, with strengths side by side', () => {
  setLanguage(context, 'en');
  const p = (vnr, name, strength, medicine, form = 'injektiokuiva-aine ja liuotin, depotsuspensiota varten') => ({NordicArticleNumber:vnr, name, strength, medicine, form, impact:'critical'});
  const rows = [p('1', 'Octreotide ratiopharm', '20 mg', 'Octreotide'), p('2', 'Octreotide ratiopharm', '10 mg', 'Octreotide'), p('3', 'Octreotide ratiopharm', '30 mg', 'Octreotide'),
    p('4', 'Biquetan', '200 mg', 'Quetiapine', 'depottabletti'), p('5', 'Ketipinor', '400 mg', 'Quetiapine', 'depottabletti'), p('6', 'Seroquel Prolong', '200 mg', 'Quetiapine', 'depottabletti'),
    p('7', 'Moviprep', '', '', 'jauhe oraaliliuosta varten')];
  const groups = Array.from(context.groupByMedicine(rows, 'en')).map(plain);
  assert.deepEqual(groups.map(g => [g.medicine, nb(g.strength), g.packages.length]), [['Moviprep', '', 1], ['Octreotide', '10/20/30 mg', 3], ['Quetiapine', '200/400 mg', 3]]);
  assert.deepEqual(groups[2].names, ['Biquetan', 'Ketipinor', 'Seroquel Prolong']);
  // The same substance in another form is another row, and prolonged-release tablets are not ordinary tablets.
  assert.equal(groups[2].form, 'Prolonged-release tablet');
  assert.equal(context.groupByMedicine([...rows, p('8', 'Quetiapin tablet', '25 mg', 'Quetiapine', 'tabletti, kalvopäällysteinen')], 'en').length, 4);
  assert.equal(context.groupByMedicine([...rows, p('8', 'Ketipinor', '50 mg', 'Quetiapine', 'depottabletti')], 'en').length, 3);
  assert.equal(context.groupByMedicine([...rows, p('8', 'Quetiapin solution', '25 mg/ml', 'Quetiapine', 'oraaliliuos')], 'en').length, 4);
  assert.equal(nb(context.mergedStrengths(['25 mg/ml', '200 mg'])), '25 mg/ml, 200 mg');
  setLanguage(context, 'fi');
  assert.equal(nb(context.mergedStrengths(['2,5 mg', '10 mg'])), '2,5 mg, 10 mg');
  assert.equal(nb(context.mergedStrengths(['2 g', '1 g'])), '1 g, 2 g', 'never "1/2 g", which reads as a half');
  setLanguage(context, 'en');
});

test('modified-release and similar forms are named exactly in both languages, and the form filter still groups them', () => {
  const cases = [
    ['depottabletti', 'Prolonged-release tablet', 'Depottabletti', 'tablet'],
    ['depotkapseli, kova', 'Prolonged-release capsule', 'Depotkapseli', 'capsule'],
    ['säädellysti vapauttava tabletti', 'Modified-release tablet', 'Säädellysti vapauttava tabletti', 'tablet'],
    ['säädellysti vapauttava kapseli, kova', 'Modified-release capsule', 'Säädellysti vapauttava kapseli', 'capsule'],
    ['enterotabletti', 'Gastro-resistant tablet', 'Enterotabletti', 'tablet'],
    ['enterokapseli, kova', 'Gastro-resistant capsule', 'Enterokapseli', 'capsule'],
    ['tabletti, suussa hajoava', 'Orally disintegrating tablet', 'Suussa hajoava tabletti', 'tablet'],
    ['dispergoituva tabletti', 'Dispersible tablet', 'Dispergoituva tabletti', 'tablet'],
    ['poretabletti', 'Effervescent tablet', 'Poretabletti', 'tablet'],
    ['imeskelytabletti, puristettu', 'Lozenge', 'Imeskelytabletti', 'tablet'],
    ['injektiokuiva-aine ja liuotin, depotsuspensiota varten', 'Prolonged-release injection', 'Depotinjektio', 'injection'],
    ['Injektioneste, depotsuspensio, esitäytetty ruisku', 'Prolonged-release injection', 'Depotinjektio', 'injection'],
    ['tabletti, kalvopäällysteinen', 'Tablet', 'Tabletti', 'tablet'],
    ['purutabletti', 'Chewable tablet', 'Purutabletti', 'tablet'],
  ];
  for (const [form, en, fi, kind] of cases) {
    setLanguage(context, 'en'); assert.equal(context.formText(form), en, form);
    setLanguage(context, 'fi'); assert.equal(context.formText(form), fi, form);
    assert.equal(context.formKind(form), kind, form);
  }
  setLanguage(context, 'en');
  assert.match(context.pkgCard({name:'Quetiapin Hexal', strength:'200 mg', form:'depottabletti', atc:'N05AH04', UnavailableFrom:'2026-11-01'}, NOW), /<p class="pkg-kind"><span>Prolonged-release tablet<\/span>/);
});

test('the impact filter is kept in the address and narrows the list', () => {
  const f = context.parseFilters('?impact=critical&q=quetiapine');
  assert.equal(f.impact, 'critical');
  assert.equal(context.filtersToQuery(f), 'q=quetiapine&impact=critical');
  for (const level of ['substitute', 'critical', 'nogroup', 'vet']) assert.equal(context.parseFilters('?impact=' + level).impact, level);
  const rows = [{name:'A', impact:'substitute'}, {name:'B', impact:'critical'}, {name:'C', impact:'nogroup'}, {name:'D', atc:'QA01'}];
  const run = impact => Array.from(context.filterPackages(rows, {q:'', impact, status:'', group:'', form:'', company:''}, NOW)).map(e => e.name);
  assert.deepEqual(run('critical'), ['B']); assert.deepEqual(run('vet'), ['D']); assert.deepEqual(run(''), ['A', 'B', 'C', 'D']);
  const list = pages['shortages.html'];
  for (const level of ['', 'critical', 'substitute', 'nogroup', 'vet']) assert.match(list, new RegExp(`name="impact" value="${level}"`));
  assert.ok(list.indexOf('name="impact"') < list.indexOf('name="status"'), 'impact is the first filter');
  assert.match(list, /href="shortages\.html\?impact=critical" id="crit-show"/);
});

test('home leads with the triage: words and numbers, each part one tap from the filtered list', () => {
  const html = JSON.parse(execFileSync('python', ['-c', "import json,sys;sys.path.insert(0,'scripts');from pages import render_pages;print(json.dumps(render_pages(749, {'substitute':531,'critical':60,'nogroup':119,'vet':39})['index.html']))"], {encoding: 'utf8'}));
  assert.ok(html.indexOf('id="q"') < html.indexOf('id="triage"'), 'the search is on the first screen of a phone, ahead of the triage');
  for (const [level, n] of [['substitute', '531'], ['critical', '60'], ['nogroup', '119']]) assert.match(html, new RegExp(`href="shortages\\.html\\?impact=${level}"[^>]*>.*?<span class="tri-num">${n}</span>`));
  assert.match(html, /For 531 of them, the pharmacy can usually give a substitute\./);
  assert.match(html, /href="shortages\.html\?impact=vet" id="triage-vet">Also on the list: 39 veterinary medicines/);
  // Each row carries its share of the human packages as a bar; the widths follow the human counts only.
  assert.match(html, /<svg class="tri-bar"[^>]*aria-hidden="true"/);
  assert.match(html, /class="part" width="8\.45"/);
});

test('"Ask your pharmacy" is said once: by the impact label for a current package, and in What to do for one that left', () => {
  const copy = vm.runInContext('copy', context);
  for (const lang of ['en', 'fi']) {
    assert.match(copy[lang].impactCard_nogroup, lang === 'en' ? /Ask your pharmacist\.$/ : /Kysy apteekista\.$/);
    // The explanation under the label does not repeat the label's own advice.
    for (const level of ['substitute', 'critical', 'nogroup', 'vet']) assert.doesNotMatch(copy[lang]['impactText_' + level], /^(Ask your|Talk to your|Kysy )/);
  }
  // Without the label the advice opens with the ask; with it, the advice does not repeat it.
  assert.doesNotMatch(copy.en.whatTextRest, /Ask your pharmacy/); assert.doesNotMatch(copy.fi.whatTextRest, /Kysy apteekista/);
  assert.match(copy.en.whatText, /^Ask your pharmacy\./); assert.match(copy.fi.whatText, /^Kysy apteekista\./);
  setLanguage(context, 'en');
  assert.match(copy.en.delayHeadline('15', '156', '78', '10%', '60%'), /^15 of 156 observed shortages stayed listed past the estimate; for 78 we cannot tell yet\. .*10%–60%/);
});

test('veterinary packages are told to ask the veterinarian or pharmacy, not given human advice', () => {
  const copy = vm.runInContext('copy', context);
  assert.match(copy.en.whatTextVet, /^Ask your veterinarian or pharmacy\./);
  assert.match(copy.fi.whatTextVet, /^Kysy eläinlääkäriltä tai apteekista\./);
  for (const text of [copy.en.whatTextVet, copy.fi.whatTextVet]) assert.doesNotMatch(text, /pharmacist or doctor|farmaseutilta tai lääkäriltä/);
  const [env] = pageEnv(['medicine.js']);
  vm.runInContext("language='en'", env);
  assert.equal(env.isVet({atc:'QN02'}), true); assert.equal(env.isVet({atc:'N02'}), false);
  const vet = env.whatMarkup({atc:'QN02BA', Company:'Vet Oy', other_packages_count:3}, 'now');
  assert.match(vet, /Ask your veterinarian or pharmacy/); assert.doesNotMatch(vet, /pharmacist or doctor|substitution group/);
  const human = env.whatMarkup({atc:'N02BA', Company:'Oy', other_packages_count:3}, 'now');
  assert.doesNotMatch(human, /<p>Ask your pharmacy/);
  assert.match(env.whatMarkup({atc:'N02BA', Company:'Oy', other_packages_count:0}, 'left'), /<p>Ask your pharmacy\./);
  const vetImpact = env.impactMarkup({atc:'QN02BA', NordicArticleNumber:'123456'}, {});
  assert.match(vetImpact, /Ask your veterinarian or pharmacy/); assert.doesNotMatch(vetImpact, /Substitution group /);
});

test('the medicine page shows the impact label with the other packages of the group, so it can be checked', () => {
  const [env] = pageEnv(['medicine.js']);
  vm.runInContext("language='en'", env);
  const groups = {'1299': {available: [], short: [
    {vnr:'147881', name:'Quetiapin Hexal', strength:'200 mg', pack_label:{en:'120 tablets', fi:'120 tablettia'}, company:'Hexal A/S', listed:true},
    {vnr:'386574', name:'Ketipinor', strength:'200 mg', pack_label:{en:'100 tablets', fi:'100 tablettia'}, company:'Orion Corporation', listed:true}]},
    '0381': {available: [{vnr:'567362', name:'Seronil', strength:'20 mg', pack_label:{en:'30 capsules', fi:'30 kapselia'}, company:'Orion Corporation'}, {vnr:'138828', name:'Self', strength:'20 mg', pack_label:{en:'30', fi:'30'}, company:'X'}], short: []}};
  const critical = env.impactMarkup({NordicArticleNumber:'147881', atc:'N05AH04', substitution_group:'1299', other_packages_count:0, impact:'critical'}, groups);
  assert.match(critical, /No interchangeable product on the market\. Talk to your pharmacist or doctor early\./);
  assert.match(critical, /The other packages in its substitution group are short too\./);
  assert.match(critical, /<strong>Ketipinor 200&nbsp;mg|<strong>Ketipinor 200\u00a0mg/); assert.match(critical, /Orion Corporation/); assert.doesNotMatch(critical, /class="alt-flag"/, 'packages under "Short too" need no flag of their own');
  assert.doesNotMatch(critical, /Quetiapin Hexal/, 'the package itself is not its own alternative');
  assert.match(critical, /Substitution group 1299\./); assert.match(critical, /href="about\.html#impact"/);
  const substitute = env.impactMarkup({NordicArticleNumber:'138828', atc:'N06AB03', substitution_group:'0381', other_packages_count:1, impact:'substitute'}, groups);
  assert.match(substitute, /Pharmacy can usually give a substitute: 1 other package on the market/);
  assert.match(substitute, /<h3>Other packages on the market<\/h3>/); assert.match(substitute, /Seronil 20.mg<\/strong><span>30 capsules<\/span><span>Orion Corporation<\/span>/);
  assert.doesNotMatch(substitute, /<strong>Self/);
  const alone = env.impactMarkup({NordicArticleNumber:'111111', atc:'N01', substitution_group:'9999', other_packages_count:0, impact:'critical'}, groups);
  assert.match(alone, /It is the only package in its substitution group on the market\./);
  const nogroup = env.impactMarkup({NordicArticleNumber:'111111', atc:'L01', impact:'nogroup'}, groups);
  assert.match(nogroup, /No substitution group\. Ask your pharmacist\./); assert.doesNotMatch(nogroup, /Substitution group \d/);
});

test('the medicine page opens the right package from a feed link and shows a helpful state for an unknown number', () => {
  const [env] = pageEnv(['medicine.js']);
  const shard = {snapshot_date:'2026-11-22', events:[{NordicArticleNumber:'599361', name:'Rivastor', UnavailableFrom:'2026-11-01'}, {NordicArticleNumber:'111111', name:'Gone', removed_on:'2026-11-10', last_seen:'2026-11-09'}, {NordicArticleNumber:'111111', name:'Gone earlier', removed_on:'2026-05-10', last_seen:'2026-05-09'}]};
  assert.equal(env.vnrFromSearch('?vnr=599361'), '599361');
  assert.equal(env.vnrFromSearch('?vnr=%20599361%20'), '599361');
  assert.equal(env.vnrFromSearch(''), '');
  const found = env.lookup('599361', shard);
  assert.equal(found.state, 'now'); assert.equal(found.events[0].name, 'Rivastor');
  assert.equal(env.lookup('abc', shard).state, 'missing');
  assert.equal(env.lookup('', shard).state, 'missing');
  const left = env.lookup('111111', shard);
  assert.equal(left.state, 'left'); assert.equal(left.events[0].name, 'Gone');
  assert.equal(env.lookup('222222', shard).state, 'missing');
  for (const lang of ['en', 'fi']) { const copy = vm.runInContext(`copy.${lang}`, env); assert.match(copy.nfText('222222'), /222222/); assert.ok(copy.nfNone && copy.nfSearch); }
  // Feed entries link to the medicine page by VNR, and the page reads that number.
  assert.match(fs.readFileSync('scripts/changes.py', 'utf8'), /medicine\.html\?vnr=\{e\['NordicArticleNumber'\]\}/);
});

test('a package that left the list shows when it was listed, not days until the estimate', () => {
  const [env] = pageEnv(['medicine.js']);
  vm.runInContext("language='en'", env);
  const gone = {NordicArticleNumber:'111111', name:'Regiocit', UnavailableFrom:'2026-11-01', EndingDate:'2026-12-20', first_seen:'2026-11-03', last_seen:'2026-11-18', removed_on:'2026-11-19', listed_at_first_capture:false, end_changes:[{seen:'2026-11-03', date:'2026-12-20'}]};
  const html = env.timelineMarkup(gone, true);
  assert.match(html, /Last listed/); assert.match(html, /Not on the list on 19 Nov 2026/);
  assert.match(html, /On the list in our captures from 3 Nov 2026 to 18 Nov 2026\./);
  assert.doesNotMatch(html, /until the estimate|so far|Today/);
  assert.match(env.timelineMarkup({...gone, listed_at_first_capture:true}, true), /Already on the list in our first capture on 3 Nov 2026; last listed 18 Nov 2026\./);
  const label = env.labelMarkup(gone, 'left');
  assert.match(label, /No longer on the list/); assert.match(label, /last listed on 18 Nov 2026/);
  vm.runInContext("language='fi'", env);
  assert.match(env.timelineMarkup(gone, true), /Listalla tilannekuvissamme 3\.11\.2026–18\.11\.2026\./);
});

test('the timeline is one track in time order with evenly spaced markers and the right connectors', () => {
  const [env] = pageEnv(['medicine.js']);
  vm.runInContext("language='en'", env);
  const now = env.todayUTC(), day = n => new Date(now + n * 86400000).toISOString().slice(0, 10);
  const order = html => Array.from(html.matchAll(/class="tl-item tl-(\w+)/g)).map(m => m[1]);
  const late = env.timelineMarkup({UnavailableFrom:day(-40), EndingDate:day(-5)}, false);
  assert.deepEqual(order(late), ['start', 'end', 'today']);
  assert.match(late, /tl-end seg-done seg-late is-late/); assert.match(late, /tl-today seg-over/); assert.match(late, /Later than estimated/); assert.doesNotMatch(late, /<svg/);
  const ongoing = env.timelineMarkup({UnavailableFrom:day(-10), EndingDate:day(20)}, false);
  assert.deepEqual(order(ongoing), ['start', 'today', 'end']); assert.match(ongoing, /tl-end seg-ahead/);
  const soon = env.timelineMarkup({UnavailableFrom:day(5), EndingDate:day(30)}, false);
  assert.deepEqual(order(soon), ['today', 'start', 'end']); assert.equal((soon.match(/seg-ahead/g) || []).length, 2);
  assert.match(env.timelineMarkup({UnavailableFrom:day(-10)}, false), /tl-count-2/);
});

test('the form shelf counts packages by form and links to the list filtered by that form', () => {
  const [env] = pageEnv(['home.js']);
  vm.runInContext("language='en'", env);
  // Long tile words carry soft hyphens, so they break only at a hyphen in a narrow tile.
  const raw = env.shelfMarkup({'tabletti, kalvopäällysteinen':5, 'tabletti':3, 'silmätipat, liuos':2, 'nenäsumute, liuos':4, 'inhalaatiojauhe':1});
  assert.match(raw, /In\u00adhal\u00aders/);
  const html = raw.replace(/\u00ad/g, '');
  assert.match(html, /href="shortages\.html\?form=tablet">[\s\S]*?<span class="shelf-name">Tablets<\/span><span class="shelf-count">8<\/span>/);
  assert.match(html, /form=spray[\s\S]*?Sprays[\s\S]*?4/); assert.match(html, /form=inhaler[\s\S]*?Inhalers/); assert.match(html, /form=drops/);
  assert.doesNotMatch(html, /form=capsule/);
  assert.equal((html.match(/<li>/g) || []).length, 4);
  const copy = vm.runInContext('copy', env);
  for (const lang of ['en', 'fi']) for (const kind of ['injection', 'inhaler', 'suppository']) assert.match(copy[lang]['shelf_' + kind], /\u00ad/, `${lang} ${kind}`);
  assert.match(fs.readFileSync('site/style.css', 'utf8'), /\.shelf-name\{[^}]*overflow-wrap:normal[^}]*hyphens:auto/);
});
