const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('site/app.js', 'utf8').split('function drawList(')[0];
const context = vm.createContext({Intl, Date});
vm.runInContext(source, context);

test('initial language is selected without inline scripts', () => {
  const html = fs.readFileSync('site/index.html', 'utf8');
  const script = fs.readFileSync('site/language.js', 'utf8');
  assert.doesNotMatch(html, /<script>/);
  for (const [browser, saved, expected] of [['fi-FI', null, 'fi'], ['en-US', 'fi', 'fi'], ['fi-FI', 'en', 'en']]) {
    const classes = new Set();
    const document = {documentElement: {lang:'en', classList: {add: name => classes.add(name)}}};
    vm.runInNewContext(script, {document, window:{addEventListener(){}}, navigator:{language:browser}, localStorage:{getItem:() => saved}});
    assert.equal(document.documentElement.lang, expected);
    assert.equal(classes.has('i18n-pending'), expected === 'fi');
  }
});

test('translations have matching keys and nonempty Finnish values', () => {
  const translations = vm.runInContext('copy', context);
  assert.deepEqual(Object.keys(translations.fi).sort(), Object.keys(translations.en).sort());
  for (const [key, value] of Object.entries(translations.fi)) {
    const rendered = typeof value === 'function' ? value(2, 'x', '3') : value;
    assert.ok(typeof rendered === 'string' && rendered.trim(), key);
  }
});

test('veterinary and missing medicine groups have clear labels', () => {
  assert.equal(context.groupName('QN02', 'en'), 'Veterinary medicines');
  assert.equal(context.groupName('QN02', 'fi'), 'Eläinlääkkeet');
  assert.equal(context.groupName('', 'en'), 'Group not listed');
});
test('common forms are understandable and unrecognised forms have a fallback', () => {
  for (const form of ['depottabletti', 'injektiokuiva-aine', 'infuusiokonsentraatti', 'depotkapseli', 'depotlaastari', 'jauhe oraaliliuosta varten', 'emulsiovoide', 'purutabletti']) {
    assert.notEqual(context.formText(form), 'Other form', form);
  }
  assert.equal(context.formText('unrecognised form'), 'Other form');
  assert.equal(context.formText(''), '');
});
test('dates use fixed abbreviations and Finnish numeric format', () => {
  assert.equal(context.dateText('2026-09-21'), '21 Sep 2026');
  vm.runInContext("language = 'fi'", context);
  assert.equal(context.dateText('2026-09-21'), '21.9.2026');
  assert.equal(context.timestampText('2026-11-21T00:30:00Z'), '21.11.2026 klo 2.30 Suomen aikaa');
  vm.runInContext("language='en'",context);
  assert.equal(context.timestampText('2026-07-21T00:30:00Z'), '21 Jul 2026, 03:30 Helsinki time');
});

test('Finnish counts, forms and shortage wording read naturally', () => {
  vm.runInContext("language = 'fi'", context);
  assert.equal(vm.runInContext('copy.fi.count(1)', context), '1 ilmoitus');
  assert.equal(vm.runInContext('copy.fi.count(2)', context), '2 ilmoitusta');
  assert.equal(context.formText('resoribletti'), 'Kielen alle liukeneva tabletti');
  assert.equal(context.formText('peräruiskeliuos'), 'Peräruiske');
  assert.equal(context.groupName('B01', 'fi'), 'Veren ja verenkierron lääkkeet');
  const html = context.card({name:'Test', UnavailableFrom:'2026-11-06', EndingDate:'2026-12-01', atc:'B01'}, Date.UTC(2026,10,21));
  assert.match(html, /Saatavuushäiriö ilmoitettu alkavaksi 6\.11\.2026 \(15 päivää\)/);
  assert.match(html, /Arvioidaan olevan taas saatavilla noin 1\.12\.2026 \(yrityksen arvio\)/);
  assert.match(html, /Lääkeryhmä: Veren ja verenkierron lääkkeet/);
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
  vm.runInContext("language='en'", context);
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

test('history and delay rendering uses translated dates and explains the sample', () => {
  const elements = {};
  const get = id => elements[id] ||= {textContent:'', innerHTML:'', value:'en', addEventListener(){}, setAttribute(){}};
  const document = {getElementById:get, documentElement:{dataset:{},classList:{remove(){}}}, querySelector:()=>({}), querySelectorAll:()=>[]};
  const env = vm.createContext({Intl, Date, document, navigator:{language:'en'}, localStorage:{getItem:()=>null,setItem(){}}, fetch:()=>new Promise(()=>{})});
  vm.runInContext(fs.readFileSync('site/app.js','utf8'), env);
  const history = [{date:'2024-11-18',count:670,imported:true},{date:'2026-11-21',count:751,imported:false}];
  const delays = {sample_size:1,active_past_estimate:24,max_gap_days:14,min_sample:30,meaningful:false,excluded:{listed_at_first_capture:0,no_estimate:0,wide_start_window:0,wide_removal_window:0,vnr_still_listed:0},examples:[]};
  env.drawChart(history,14); env.drawDelays(delays,'2026-11-21');
  assert.match(get('chart').innerHTML, /18 Nov 2024/);
  assert.doesNotMatch(get('chart').innerHTML, /2024-11-18/);
  assert.match(get('delay-headline').textContent, /1 shortage entered/);
  assert.match(get('delay-note').textContent, /does not prove supply returned/);
  assert.match(get('delay-visual').innerHTML, /24 shortages were still listed/);
  assert.match(get('delay-note').textContent, /likely higher/);
  assert.match(get('chart').innerHTML, /font-size="14"[^>]*>0<\/text>/);
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
  assert.match(get('updated').textContent, /Päivitetty 21\.11\.2026/);
  assert.equal(get('freshness').textContent, '');
});
