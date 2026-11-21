const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('site/app.js', 'utf8').split('function drawList(')[0];
const context = vm.createContext({Intl, Date, URLSearchParams});
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

test('pack sizes use the unit and do not repeat the form', () => {
  vm.runInContext("language='en'", context);
  const tablets = {name:'T', form:'tabletti, kalvopäällysteinen', pack:'98', pack_label:{en:'98 tablets', fi:'98 tablettia'}, atc:'N02'};
  assert.match(context.card(tablets, Date.UTC(2026,10,21)), /<p class="form">98 tablets<\/p>/);
  assert.match(context.card({...tablets, form:'injektioneste, liuos', pack:'5 ml', pack_label:{en:'5 ml', fi:'5 ml'}}, 0), /<p class="form">Injection · 5 ml<\/p>/);
  assert.match(context.card({...tablets, form:'purutabletti', pack_label:{en:'30 tablets', fi:'30 tablettia'}}, 0), /Chewable tablet · 30 tablets/);
  assert.match(context.card({...tablets, pack_label:undefined}, 0), /Tablet · 98</);
  vm.runInContext("language='fi'", context);
  assert.match(context.card(tablets, 0), /<p class="form">98 tablettia<\/p>/);
  vm.runInContext("language='en'", context);
});

test('Details give a neutral pointer instead of contact data', () => {
  const html = context.card({name:'T', atc:'N02', Company:'Example Oy', contact:'CONTACT-PLACEHOLDER'}, 0);
  assert.match(html, /For more information, ask your pharmacy or the company \(Example Oy\)\. <a href="https:\/\/fimea\.fi\/en\/databases_and_registers\/shortages">Fimea’s shortage search ↗<\/a>/);
  assert.doesNotMatch(html, /CONTACT-PLACEHOLDER/);
  vm.runInContext("language='fi'", context);
  assert.match(context.card({name:'T', atc:'N02', Company:'Example Oy'}, 0), /Lisätietoja saat apteekista tai yritykseltä \(Example Oy\)\. <a href="https:\/\/fimea\.fi\/laakehaut_ja_luettelot\/saatavuushairio-uusi">Fimean saatavuushäiriöhaku/);
  vm.runInContext("language='en'", context);
});

test('the q parameter fills the search from a feed link', () => {
  const queryFromUrl = search => vm.runInContext('queryFromUrl', context)(search);
  assert.equal(queryFromUrl('?q=599361'), '599361');
  assert.equal(queryFromUrl('?x=1'), '');
  assert.equal(queryFromUrl('?q=%20Burana%20'), 'Burana');
  assert.ok(context.searchMatches({NordicArticleNumber:'599361', name:'Other'}, queryFromUrl('?q=599361')));
});

test('this week summary and how-we-count note state their window and counts', () => {
  const elements = {};
  const get = id => elements[id] ||= {textContent:'', innerHTML:'', hidden:true, href:'', value:'en', addEventListener(){}, setAttribute(){}};
  const document = {getElementById:get, documentElement:{dataset:{},classList:{remove(){}}}, querySelector:()=>({}), querySelectorAll:()=>[]};
  const env = vm.createContext({Intl, Date, document, navigator:{language:'en'}, localStorage:{getItem:()=>null,setItem(){}}, fetch:()=>new Promise(()=>{})});
  vm.runInContext(fs.readFileSync('site/app.js','utf8'), env);
  const week = {from:'2026-11-13', to:'2026-11-21', days:8, new:77, left:70, count_from:751, count_to:758};
  env.drawWeek(week, 758);
  assert.equal(get('week').hidden, false);
  assert.equal(get('week-new').textContent, '77');
  assert.equal(get('week-left').textContent, '70');
  assert.equal(get('week-total').textContent, '758');
  assert.match(get('week-window').textContent, /capture of 13 Nov 2026, 8 days earlier/);
  assert.match(get('week-total-note').textContent, /751 records in the capture of 13 Nov 2026/);
  assert.equal(get('week-new-note').textContent, 'New records listed since 13 Nov 2026, including any that left again.');
  assert.match(get('week-left-note').textContent, /^Records that left the list since 13 Nov 2026, including any that arrived in the same period\./);
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
  assert.match(get('week-new-label').textContent, /UUDET LISTALLA/);
  assert.match(get('week-new-note').textContent, /myös ne, jotka ehtivät poistua uudelleen/);
  assert.match(get('how-count-text').textContent, /^Mukana on 156 listalta poistuneesta 1\s197 ilmoituksesta/);
  assert.match(get('how-count-text').textContent, /642 jo ensimmäisessä tilannekuvassa ollutta/);
});

test('strength is part of the main line, with a Finnish decimal comma', () => {
  const apixaban = {name:'Apixaban Sandoz', strength:'2.5 mg', form:'tabletti, kalvopäällysteinen', pack_label:{en:'60 tablets', fi:'60 tablettia'}, UnavailableFrom:'2026-11-06', atc:'B01'};
  vm.runInContext("language='en'", context);
  assert.deepEqual(Array.from(context.formAndPack(apixaban)), ['2.5 mg', '60 tablets']);
  assert.match(context.card(apixaban, Date.UTC(2026,10,21)), /<p class="form">2\.5 mg · 60 tablets<\/p>/);
  assert.deepEqual(Array.from(context.formAndPack({form:'injektioneste, liuos', strength:'10 mg/ml', pack:'5 ml'})), ['Injection', '10 mg/ml', '5 ml']);
  assert.deepEqual(Array.from(context.formAndPack({form:'injektioneste, liuos', pack:'5 ml'})).filter(Boolean), ['Injection', '5 ml']);
  vm.runInContext("language='fi'", context);
  assert.match(context.card(apixaban, Date.UTC(2026,10,21)), /<p class="form">2,5 mg · 60 tablettia<\/p>/);
  assert.match(context.card(apixaban, Date.UTC(2026,10,21)), /<dd>2\.5 mg<\/dd>/);
  assert.equal(context.nameWithStrength(apixaban), 'Apixaban Sandoz 2,5 mg');
  vm.runInContext("language='en'", context);
  assert.equal(context.nameWithStrength(apixaban), 'Apixaban Sandoz 2.5 mg');
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
  assert.deepEqual(hits('apixaban 2.5 mg'), ['2.5 mg']);
  assert.deepEqual(hits('apiksabaani 2,5 mg'), ['2.5 mg']);
  assert.deepEqual(hits('apixaban 2,'), ['2.5 mg']);
  assert.deepEqual(hits('2,5 mg'), ['2.5 mg']);
  assert.deepEqual(hits('apixaban sandoz'), ['2.5 mg', '5 mg']);
  assert.deepEqual(hits('apixaban 50 mg'), []);
  assert.deepEqual(hits('584836'), ['2.5 mg']);
});
