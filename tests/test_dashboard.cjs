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
const copy_fi = () => vm.runInContext('copy.fi', context);
const NOW = Date.UTC(2026, 10, 21);
const plain = value => JSON.parse(JSON.stringify(value));
const dict = (a, b) => Object.assign({}, a, b);
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
  assert.match(pages['index.html'], new RegExp(en.heroLine(749, 0).replace('.', '\\.')));
  assert.equal(en.heroLine(714, 43), 'Fimea: 714 short now, 43 more expected within 2 weeks.');
  assert.equal(copy_fi().heroLine(714, 43), 'Fimea: 714 saatavuushäiriötä nyt, 43 lisää odotettavissa 2 viikon sisällä.');
  assert.equal(en.sourceNoteEnded('1 Nov 2026', '2 Nov 2026'), 'Source: Fimea shortage file. From our captures: last seen in the capture of 1 Nov 2026, absent on 2 Nov 2026. From the company: the start and end dates.');
  assert.doesNotMatch(copy_fi().listIntro + copy_fi().trendsIntro, /puutteelli|listaa/);
  assert.match(copy_fi().impactCaveat1, /kaupan/);
  for (const lang of ['en', 'fi']) assert.doesNotMatch(vm.runInContext(`copy.${lang}`, context).heroAnswer(537), /pharmacy can usually|apteekki voi yleensä/);
  assert.match(en.heroAnswer(537), /^For 537 of them, the register lists an interchangeable package that is on the market and not flagged short\.$/);
  assert.match(pages['index.html'], /hero-answer[^>]*><\/p>|not flagged short/);
  assert.doesNotMatch(copy_fi().impactCaveat1, /markkinoilla/);
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
  assert.equal(recent.text, 'Checked by Shortage Radar: 18 Nov 2026');
  assert.equal(recent.stale, false);
  assert.equal(context.freshnessInfo({last_checked:'2026-11-17'}, today, today).stale, true);
  const fallback = context.freshnessInfo({last_checked:null, generated_at:'2026-11-17T00:00:00Z'}, today, today);
  assert.match(fallback.text, /^Checked by Shortage Radar: unknown\. Page built: 17 Nov 2026/);
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

const DAY = 86400000;
const httpDate = daysAgo => new Date(Date.now() - daysAgo * DAY).toUTCString();

test('a source file is stale only when its date is more than 2 days old, counted in Helsinki days', () => {
  const today = Date.UTC(2026, 10, 23);
  const stale = (meta) => plain(context.staleSources(meta, today));
  // Fimea changed the file on a Saturday: on Monday it is exactly two days old, so no banner.
  assert.deepEqual(stale({shortages_last_modified:'Sat, 21 Nov 2026 10:00:00 GMT', register_date:'2026-11-21'}), []);
  assert.deepEqual(stale({shortages_last_modified:'Fri, 20 Nov 2026 10:00:00 GMT'}), [{file:'shortages', date:'2026-11-20'}]);
  // 22:30 GMT on the 20th is already the 21st in Helsinki.
  assert.deepEqual(stale({shortages_last_modified:'Fri, 20 Nov 2026 22:30:00 GMT'}), []);
  assert.deepEqual(stale({register_date:'2026-11-20'}), [{file:'register', date:'2026-11-20'}]);
  assert.deepEqual(stale({shortages_last_modified:'Fri, 20 Nov 2026 10:00:00 GMT', register_date:'2026-11-10'}).map(x => x.file), ['shortages', 'register']);
  // An unknown date is not stale.
  assert.deepEqual(stale({}), []);
  assert.deepEqual(stale({shortages_last_modified:'garbage', register_date:'x'}), []);
  assert.equal(vm.runInContext('STALE_DAYS', context), 2);
});

test('the stale-file banner names the file and its date, in English and Finnish', () => {
  const [env, get] = pageEnv(['home.js']);
  get('stale'); get('stale-text'); get('source-times');
  const today = new Date().toISOString().slice(0, 10);
  const fresh = {snapshot_date:today, last_checked:today, generated_at:new Date().toISOString()};
  env.renderChrome(dict(fresh, {source_metadata:{shortages_last_modified:httpDate(0), register_date:today}}));
  assert.equal(get('stale').hidden, true);
  const old = {shortages_last_modified:'Fri, 06 Nov 2026 10:00:00 GMT', register_date:today};
  env.renderChrome(dict(fresh, {source_metadata:old}));
  assert.equal(get('stale').hidden, false);
  assert.equal(get('stale-text').textContent, 'Fimea’s shortage file has not changed since 6 Nov 2026, more than 2 days ago. The list may be out of date.');
  env.renderChrome(dict(fresh, {source_metadata:{shortages_last_modified:httpDate(0), register_date:'2026-11-05'}}));
  assert.equal(get('stale-text').textContent, 'Fimea’s basic register is dated 5 Nov 2026, more than 2 days ago. Information on interchangeable packages may be out of date.');
  env.renderChrome(dict(fresh, {source_metadata:{shortages_last_modified:'Fri, 06 Nov 2026 10:00:00 GMT', register_date:'2026-11-05'}}));
  assert.match(get('stale-text').textContent, /shortage file.*register/);
  // Switching the language redraws the banner and the footer line without a new load.
  vm.runInContext("setLanguage('fi', null)", env);
  assert.equal(get('stale-text').textContent, 'Fimean saatavuushäiriötiedosto on muuttunut viimeksi 6.11.2026, yli 2 päivää sitten. Lista voi olla vanhentunut. Fimean perusrekisterin päiväys on 5.11.2026, yli 2 päivää sitten. Tiedot vaihtokelpoisista valmisteista voivat olla vanhentuneita.');
});

// A direct link to an EU list page: the page's own script runs against a fake document, and source.json is what the build wrote next to it.
async function directLink(script, meta) {
  const elements = {};
  const get = id => elements[id] ||= {textContent:'', innerHTML:'', hidden:true, href:'', value:'', options:[], children:[], clientWidth:400, dataset:{}, open:false, addEventListener(){}, setAttribute(){}, append(){}, replaceChildren(){}, focus(){}, scrollIntoView(){}, classList:{toggle(){}, add(){}, remove(){}}};
  const requested = [];
  const document = {getElementById:get, documentElement:{dataset:{page:'critical'},classList:{remove(){}}}, querySelector:()=>({}), querySelectorAll:()=>[], createElement:()=>get('x' + Math.random()), addEventListener(){}};
  const env = vm.createContext({Intl, Date, URLSearchParams, matchMedia:() => ({matches:false}), document, navigator:{language:'en'}, localStorage:{getItem:()=>null,setItem(){}},
    fetch:url => { requested.push(url); return Promise.resolve({ok:true, json:() => Promise.resolve(meta)}); }, location:{search:''}});
  vm.runInContext(shared + '\n' + read(script), env);
  await new Promise(resolve => setTimeout(resolve, 20));
  return [get, requested];
}

test('the stale warning also shows on the EU list page, a code page and the methods page, from the same build’s source.json', async () => {
  const meta = {snapshot_date:'2026-11-23', last_checked:'2026-11-23', generated_at:new Date().toISOString(), source_metadata:{shortages_last_modified:'Fri, 20 Nov 2026 09:00:00 GMT', register_date:'2026-11-19'}};
  // critical.html loads critical.js; critical-<code>.html and critical-methods.html load common.js.
  for (const script of ['critical.js', 'common.js']) {
    const [get, requested] = await directLink(script, meta);
    assert.deepEqual(requested, ['source.json'], script);
    assert.equal(get('stale').hidden, false, script);
    assert.match(get('stale-text').textContent, /shortage file has not changed since 20 Nov 2026.*register is dated 19 Nov 2026/, script);
  }
  const fresh = JSON.parse(JSON.stringify(meta)); fresh.source_metadata = {shortages_last_modified:new Date().toUTCString(), register_date:new Date().toISOString().slice(0, 10)}; fresh.last_checked = fresh.snapshot_date = new Date().toISOString().slice(0, 10);
  const [get] = await directLink('common.js', fresh);
  assert.equal(get('stale').hidden, true);
  // The built EU pages carry the banner element, and load one of the two scripts.
  const out = JSON.parse(execFileSync('python', ['-c', "import json,sys;sys.path.insert(0,'scripts');sys.path.insert(0,'tests');import test_critical as t;from critical_pages import render_critical;e,p,d=t.fixture();m=t.matches_of(e,p,d);import critical as C;r=C.current_rows(e,m);print(json.dumps(render_critical({'eu':t.EU,'rows':r,'counts':C.counts(r),'history':C.history(e,m,[]),'archive_start':'2026-09-15','snapshot_date':'2026-11-23','source_metadata':t.SOURCES})))"], {encoding:'utf8', maxBuffer:256*1024*1024}));
  const names = Object.keys(out);
  assert.ok(names.includes('critical.html') && names.includes('critical-methods.html') && names.some(n => /^critical-[A-Z0-9]+\.html$/.test(n)));
  for (const name of names) {
    assert.match(out[name], /id="stale"/, name);
    assert.match(out[name], name === 'critical.html' ? /src="critical\.js"/ : /src="common\.js"/, name);
  }
});

test('the home page shows when Fimea’s file changed and when Shortage Radar checked, next to the headline', () => {
  const [env, get] = pageEnv(['home.js']);
  get('hero-fresh'); get('hero-file'); get('hero-checked'); get('source-times'); get('stale'); get('stale-text');
  const meta = {snapshot_date:'2026-11-23', last_checked:'2026-11-23', generated_at:'2026-11-23T05:00:00Z', source_metadata:{shortages_last_modified:'Sun, 22 Nov 2026 23:20:01 GMT', register_date:'2026-11-23', register_last_modified:'Mon, 23 Nov 2026 00:31:00 GMT'}};
  env.renderChrome(meta);
  assert.equal(get('hero-fresh').hidden, false);
  assert.equal(get('hero-file').textContent, 'Fimea file changed: 23 Nov 2026');
  assert.equal(get('hero-checked').textContent, 'Checked by Shortage Radar: 23 Nov 2026');
  assert.match(get('source-times').textContent, /Fimea file changed: 23 Nov 2026, 01:20 Helsinki time/);
  vm.runInContext("setLanguage('fi', null)", env);
  assert.equal(get('hero-file').textContent, 'Fimean tiedosto muuttui: 23.11.2026');
  assert.equal(get('hero-checked').textContent, 'Saatavuustutka tarkisti: 23.11.2026');
  // No file time: the line says so instead of showing nothing, and a failed check date is never replaced by the build time.
  env.renderChrome({snapshot_date:'2026-11-23', last_checked:null, generated_at:'2026-11-23T05:00:00Z', source_metadata:{}});
  assert.equal(get('hero-file').textContent, 'Fimean tiedosto muuttui: ei tiedossa');
  assert.match(get('hero-checked').textContent, /^Saatavuustutka tarkisti: ei tiedossa\. Sivu koostettu: /);
  assert.match(pages['index.html'], /id="hero-fresh"[^>]* hidden/);
  assert.ok(pages['index.html'].indexOf('id="hero-line"') < pages['index.html'].indexOf('id="hero-fresh"') && pages['index.html'].indexOf('id="hero-fresh"') < pages['index.html'].indexOf('id="hero-label"'));
});

test('history and end-date rendering uses translated dates and states one dated fact', () => {
  const [env, get] = pageEnv();
  const history = [{date:'2024-11-18',count:670,imported:true},{date:'2026-11-21',count:751,imported:false}];
  const changes = {current:700,changed:37,from:'2026-09-15',to:'2026-11-21',max_gap_days:14};
  env.drawChart(history,14); env.drawEndChanges(changes);
  assert.match(get('chart').innerHTML, /18 Nov 2024/);
  assert.doesNotMatch(get('chart').innerHTML, /2024-11-18/);
  assert.match(get('chart').innerHTML, /no captures, 733 days/);
  assert.equal(get('end-changes-text').textContent, '37 of the 700 notices on the list changed the estimated end date in our captures from 15 Sep 2026 to 21 Nov 2026.');
  assert.match(get('end-changes-note').textContent, /at most 14 days after the capture before it\. A change across a longer gap is not counted/);
  assert.doesNotMatch(get('end-changes-text').textContent + get('end-changes-note').textContent, /%|share|past the estimate|delay/i);
  assert.match(get('chart').innerHTML, /font-size="14"[^>]*>650<\/text>/);
  assert.match(get('chart').innerHTML, /font-weight="600"[^>]*>751<\/text>/);
  assert.match(get('chart').innerHTML, /The vertical axis starts at 650\./);
  env.drawTable(history);
  assert.match(get('chart-table').innerHTML, /<td>21 Nov 2026<\/td><td>751<\/td><td>saved by this project<\/td>/);
  vm.runInContext("language='fi'",env);
  env.drawChart(history,14); env.drawEndChanges(changes);
  assert.match(get('chart').innerHTML, /18\.11\.2024/);
  assert.match(get('chart').innerHTML, /ei tilannekuvia/);
  assert.equal(get('end-changes-text').textContent, 'Listalla olevista 700 ilmoituksesta 37 muutti arvioitua päättymispäivää tilannekuvissamme 15.9.2026–21.11.2026.');
  assert.match(get('end-changes-note').textContent, /enintään 14 päivää aiemmin\. Pidemmän aukon yli tapahtunutta muutosta ei lasketa/);
  env.drawEndChanges(null);
  assert.equal(get('end-changes-text').textContent, '');
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
  vm.runInContext("language='fi'", env);
  env.drawWeek(week, 758);
  assert.equal(get('feed-link').href, 'feed-fi.xml');
  assert.match(get('week-facts').innerHTML, /Uudet listalla/);
  assert.match(get('week-facts').innerHTML, /myös ne, jotka ehtivät poistua uudelleen/);
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
  assert.doesNotMatch(Object.values(pages).join(''), /https?:\/\/(?!alejandrorenalias|fimea|(?:www\.)?ema\.europa|creativecommons|web\.archive|github)/);
});

test('every current card carries one impact label with its reason, in both languages', () => {
  const record = {name:'Test', UnavailableFrom:'2026-11-06', EndingDate:'2026-12-01', atc:'N02'};
  const cases = [
    [{substitution_group:'0042', other_packages_count:5}, 'substitute', {en:'Pharmacy can usually give a substitute: 5 other packages on the market', fi:'Apteekki voi yleensä vaihtaa valmisteen: kaupan on 5 muuta pakkausta'}],
    [{substitution_group:'0042', other_packages_count:1}, 'substitute', {en:'Pharmacy can usually give a substitute: 1 other package on the market', fi:'Apteekki voi yleensä vaihtaa valmisteen: kaupan on 1 muu pakkaus'}],
    [{substitution_group:'0042', other_packages_count:0}, 'no_alternative', {en:'No interchangeable product on the market. Talk to your pharmacist or doctor early.', fi:'Ei vaihtokelpoista valmistetta kaupan. Kysy apteekista tai lääkäriltä hyvissä ajoin.'}],
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
    assert.equal(context.impactOf({...record, impact:'no_alternative', other_packages_count:4, substitution_group:'1'}), 'no_alternative');
    // A file saved before the rename still reads: the old name is the new level.
    assert.equal(context.impactOf({...record, impact:'critical', other_packages_count:4, substitution_group:'1'}), 'no_alternative');
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
  const p = (vnr, name, strength, medicine, form = 'injektiokuiva-aine ja liuotin, depotsuspensiota varten') => ({NordicArticleNumber:vnr, name, strength, medicine, form, impact:'no_alternative'});
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
  assert.equal(f.impact, 'no_alternative');  // an old link with ?impact=critical keeps working
  assert.equal(context.parseFilters('?impact=no_alternative').impact, 'no_alternative');
  assert.equal(context.filtersToQuery(f), 'q=quetiapine&impact=no_alternative');
  for (const level of ['substitute', 'no_alternative', 'nogroup', 'vet']) assert.equal(context.parseFilters('?impact=' + level).impact, level);
  const rows = [{name:'A', impact:'substitute'}, {name:'B', impact:'no_alternative'}, {name:'C', impact:'nogroup'}, {name:'D', atc:'QA01'}];
  const run = impact => Array.from(context.filterPackages(rows, {q:'', impact, status:'', group:'', form:'', company:''}, NOW)).map(e => e.name);
  assert.deepEqual(run('no_alternative'), ['B']); assert.deepEqual(run('vet'), ['D']); assert.deepEqual(run(''), ['A', 'B', 'C', 'D']);
  const list = pages['shortages.html'];
  for (const level of ['', 'no_alternative', 'substitute', 'nogroup', 'vet']) assert.match(list, new RegExp(`name="impact" value="${level}"`));
  assert.ok(list.indexOf('name="impact"') < list.indexOf('name="status"'), 'impact is the first filter');
  assert.match(list, /href="shortages\.html\?impact=no_alternative" id="crit-show"/);
});

test('home leads with the triage: words and numbers, each part one tap from the filtered list', () => {
  const html = JSON.parse(execFileSync('python', ['-c', "import json,sys;sys.path.insert(0,'scripts');from pages import render_pages;print(json.dumps(render_pages(749, {'substitute':531,'no_alternative':60,'nogroup':119,'vet':39})['index.html']))"], {encoding: 'utf8'}));
  assert.ok(html.indexOf('id="q"') < html.indexOf('id="triage"'), 'the search is on the first screen of a phone, ahead of the triage');
  for (const [level, n] of [['substitute', '531'], ['no_alternative', '60'], ['nogroup', '119']]) assert.match(html, new RegExp(`href="shortages\\.html\\?impact=${level}"[^>]*>.*?<span class="tri-num">${n}</span>`));
  assert.match(html, /For 531 of them, the register lists an interchangeable package that is on the market and not flagged short\./);
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
    for (const level of ['substitute', 'no_alternative', 'nogroup', 'vet']) assert.doesNotMatch(copy[lang]['impactText_' + level], /^(Ask your|Talk to your|Kysy )/);
  }
  // Without the label the advice opens with the ask; with it, the advice does not repeat it.
  assert.doesNotMatch(copy.en.whatTextRest, /Ask your pharmacy/); assert.doesNotMatch(copy.fi.whatTextRest, /Kysy apteekista/);
  assert.match(copy.en.whatText, /^Ask your pharmacy\./); assert.match(copy.fi.whatText, /^Kysy apteekista\./);
  setLanguage(context, 'en');
  for (const lang of ['en', 'fi']) for (const key of Object.keys(copy[lang])) assert.doesNotMatch(key, /^(delay|how(Text|First|NoEstimate|Start|End|Changed|Gap)|byCompany)/, `${lang} ${key} was removed with the delay share and the company ranking`);
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

test('an ended record names the capture it was last seen in and the capture it was absent in, not the file date', () => {
  const [env] = pageEnv(['medicine.js']);
  vm.runInContext("language='en'", env);
  const ended = {last_seen: '2026-11-10', removed_on: '2026-11-12'};
  assert.match(env.sourceLine(ended, true, '2026-11-23'), /From our captures: last seen in the capture of 10 Nov 2026, absent on 12 Nov 2026\./);
  assert.doesNotMatch(env.sourceLine(ended, true, '2026-11-23'), /23 Nov/);
  assert.match(env.sourceLine({last_seen: '2026-11-23', removed_on: null}, false, '2026-11-23'), /data of 23 Nov 2026/);
});

test('the medicine page shows the impact label with the other packages of the group, so it can be checked', () => {
  const [env] = pageEnv(['medicine.js']);
  vm.runInContext("language='en'", env);
  const groups = {'1299': {available: [], short: [
    {vnr:'147881', name:'Quetiapin Hexal', strength:'200 mg', pack_label:{en:'120 tablets', fi:'120 tablettia'}, company:'Hexal A/S', listed:true},
    {vnr:'386574', name:'Ketipinor', strength:'200 mg', pack_label:{en:'100 tablets', fi:'100 tablettia'}, company:'Orion Corporation', listed:true}]},
    '0381': {available: [{vnr:'567362', name:'Seronil', strength:'20 mg', pack_label:{en:'30 capsules', fi:'30 kapselia'}, company:'Orion Corporation'}, {vnr:'138828', name:'Self', strength:'20 mg', pack_label:{en:'30', fi:'30'}, company:'X'}], short: []}};
  const critical = env.impactMarkup({NordicArticleNumber:'147881', atc:'N05AH04', substitution_group:'1299', other_packages_count:0, impact:'no_alternative'}, groups);
  assert.match(critical, /No interchangeable product on the market\. Talk to your pharmacist or doctor early\./);
  assert.match(critical, /The other packages in its substitution group are short too\./);
  assert.match(critical, /<strong>Ketipinor 200&nbsp;mg|<strong>Ketipinor 200\u00a0mg/); assert.match(critical, /Orion Corporation/); assert.doesNotMatch(critical, /class="alt-flag"/, 'packages under "Short too" need no flag of their own');
  assert.doesNotMatch(critical, /Quetiapin Hexal/, 'the package itself is not its own alternative');
  assert.match(critical, /Substitution group 1299\./); assert.match(critical, /href="about\.html#impact"/);
  const substitute = env.impactMarkup({NordicArticleNumber:'138828', atc:'N06AB03', substitution_group:'0381', other_packages_count:1, impact:'substitute'}, groups);
  assert.match(substitute, /Pharmacy can usually give a substitute: 1 other package on the market/);
  assert.match(substitute, /<h3>Other packages on the market<\/h3>/); assert.match(substitute, /Seronil 20.mg<\/strong><span>30 capsules<\/span><span>Orion Corporation<\/span>/);
  assert.doesNotMatch(substitute, /<strong>Self/);
  const alone = env.impactMarkup({NordicArticleNumber:'111111', atc:'N01', substitution_group:'9999', other_packages_count:0, impact:'no_alternative'}, groups);
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

test('a notice seen on both sides of a long gap says it was not observed in between', () => {
  const [env] = pageEnv(['medicine.js']);
  vm.runInContext("language='en'", env);
  const now = env.todayUTC(), day = n => new Date(now + n * 86400000).toISOString().slice(0, 10);
  const spans = [{first_seen:'2024-11-18', last_seen:'2024-11-18'}, {first_seen:'2026-09-15', last_seen:'2026-11-23'}];
  const e = {NordicArticleNumber:'114636', UnavailableFrom:day(-100), EndingDate:day(100), first_seen:'2024-11-18', last_seen:'2026-11-23', removed_on:null, listed_at_first_capture:true, spans, gaps:[{from:'2024-11-18', to:'2026-09-15', days:666}]};
  for (const archive of [false, true]) {
    const html = env.timelineMarkup(e, archive);
    assert.match(html, /Not observed between 18 Nov 2024 and 15 Sep 2026\./);
    assert.match(html, /On the list in our capture of 15 Sep 2026|On the list in our captures from 15 Sep 2026 to 23 Nov 2026\./);
    assert.doesNotMatch(html, /from 18 Nov 2024 to 23 Nov 2026/);
  }
  assert.doesNotMatch(env.timelineMarkup({...e, gaps:[], spans:[spans[1]], listed_at_first_capture:false}, false), /Not observed/);
  vm.runInContext("language='fi'", env);
  assert.match(env.timelineMarkup(e, false), /Ei havaintoja välillä 18\.11\.2024–15\.9\.2026\./);
  const gone = {...e, removed_on:'2026-12-01', last_seen:'2024-11-18', spans:[spans[0]], gaps:[], removed_after_gap:true};
  vm.runInContext("language='en'", env);
  assert.match(env.timelineMarkup({...gone, removed_on:'2026-09-15'}, true), /Not observed between 18 Nov 2024 and 15 Sep 2026\./);
});

test('the line from the reported start to today is hatched when a gap lies inside it, and the count says what it counts', () => {
  const [env] = pageEnv(['medicine.js']);
  vm.runInContext("language='en'", env);
  const now = env.todayUTC(), day = n => new Date(now + n * 86400000).toISOString().slice(0, 10);
  const base = {NordicArticleNumber:'114636', UnavailableFrom:day(-1028), EndingDate:day(100), first_seen:'2024-11-18', last_seen:day(0), removed_on:null};
  const gap = {from:'2024-11-18', to:'2026-09-15', days:666};
  const hatched = env.timelineMarkup({...base, gaps:[gap]}, false);
  assert.match(hatched, /tl-today seg-unknown/); assert.doesNotMatch(hatched, /seg-done|seg-now/);
  assert.match(hatched, /Days since the reported start: 1,028/); assert.doesNotMatch(hatched, /so far/);
  const solid = env.timelineMarkup({...base, gaps:[]}, false);
  assert.match(solid, /seg-done seg-now/); assert.doesNotMatch(solid, /seg-unknown/);
  // A gap that ended before the reported start does not touch the stretch.
  assert.match(env.timelineMarkup({...base, UnavailableFrom:'2026-10-01', gaps:[gap]}, false), /seg-done/);
  vm.runInContext("language='fi'", env);
  assert.match(env.timelineMarkup({...base, gaps:[gap]}, false), /Päiviä ilmoitetusta alkamispäivästä: 1\s?028/);
  assert.match(fs.readFileSync(require('node:path').join(__dirname, '../site/style.css'), 'utf8'), /\.seg-unknown\)::before\{background:repeating-linear-gradient/);
});

test('every stretch of the timeline line is hatched when a gap overlaps it, including an estimated end inside a gap', () => {
  const [env] = pageEnv(['medicine.js']);
  vm.runInContext("language='en'", env);
  const now = env.todayUTC(), day = n => new Date(now + n * 86400000).toISOString().slice(0, 10);
  // Reported start before the gap, estimated end inside it, today after it: start -> end -> today. Both stretches touch the gap.
  const e = {NordicArticleNumber:'1', UnavailableFrom:day(-300), EndingDate:day(-150), first_seen:day(-300), last_seen:day(0), removed_on:null, gaps:[{from:day(-200), to:day(-100), days:100}]};
  const html = env.timelineMarkup(e, false);
  assert.match(html, /tl-end seg-unknown/); assert.match(html, /tl-today seg-unknown/); assert.doesNotMatch(html, /seg-over|seg-done/);
  // The gap lies between the reported start and the estimate only: the stretch after the estimate is known and stays solid.
  const early = env.timelineMarkup({...e, gaps:[{from:day(-290), to:day(-200), days:90}]}, false);
  assert.match(early, /tl-end seg-unknown/); assert.match(early, /tl-today seg-over/);
  // The gap lies after the estimate only: the first stretch is solid, the overrun is hatched.
  const late = env.timelineMarkup({...e, gaps:[{from:day(-100), to:day(-50), days:50}]}, false);
  assert.match(late, /tl-end seg-done/); assert.match(late, /tl-today seg-unknown/);
  // A gap that ends before the reported start touches no stretch.
  assert.doesNotMatch(env.timelineMarkup({...e, gaps:[{from:day(-500), to:day(-400), days:100}]}, false), /seg-unknown/);
  // The future stretch stays dashed, not hatched.
  const ahead = env.timelineMarkup({UnavailableFrom:day(-100), EndingDate:day(50), gaps:[{from:day(-60), to:day(-30), days:30}]}, false);
  assert.match(ahead, /tl-today seg-unknown/); assert.match(ahead, /tl-end seg-ahead/);
});

test('no text calls a reported start a "longest running" or "so far" listing', () => {
  const copy = vm.runInContext('copy', context);
  for (const lang of ['en', 'fi']) {
    const t = copy[lang];
    assert.equal(t.longestTitle, lang === 'en' ? 'Earliest reported starts' : 'Varhaisimmat ilmoitetut alkamispäivät');
    for (const key of ['longestTitle', 'longestNote', 'sortLongest', 'factLongest', 'tlDuration']) {
      const text = typeof t[key] === 'function' ? t[key](3, '1 Jan 2026') : t[key];
      assert.doesNotMatch(text, /longest running|so far|pisimpään|tähän mennessä/i, key);
    }
  }
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

test('page numbers for a long list: seven slots at most, the current page and the ends always show', () => {
  const nums = (current, pages) => plain(context.pageNumbers(current, pages));
  assert.deepEqual(nums(1, 1), [1]);
  assert.deepEqual(nums(2, 5), [1, 2, 3, 4, 5]);
  assert.deepEqual(nums(4, 7), [1, 2, 3, 4, 5, 6, 7]);
  assert.deepEqual(nums(1, 11), [1, 2, 3, 4, 5, '…', 11]);
  assert.deepEqual(nums(4, 11), [1, 2, 3, 4, 5, '…', 11]);
  assert.deepEqual(nums(6, 11), [1, '…', 5, 6, 7, '…', 11]);
  assert.deepEqual(nums(8, 11), [1, '…', 7, 8, 9, 10, 11]);
  assert.deepEqual(nums(11, 11), [1, '…', 7, 8, 9, 10, 11]);
  for (let pages = 1; pages <= 30; pages++) for (let current = 1; current <= pages; current++) {
    const list = nums(current, pages);
    assert.ok(list.length <= 7 && list.includes(current) && list.includes(1) && list.includes(pages), `${current}/${pages}`);
  }
  assert.equal(vm.runInContext("pageCount", context)(0, 12), 1); assert.equal(vm.runInContext("pageCount", context)(12, 12), 1); assert.equal(vm.runInContext("pageCount", context)(13, 12), 2); assert.equal(vm.runInContext("pageCount", context)(123, 12), 11);
  assert.equal(vm.runInContext("clampPage", context)(0, 5), 1); assert.equal(vm.runInContext("clampPage", context)(9, 5), 5); assert.equal(vm.runInContext("clampPage", context)(NaN, 5), 1); assert.equal(vm.runInContext("clampPage", context)(3, 5), 3);
});

test('the list page number in the address: parse, clamp and build', () => {
  const from = (search, pages) => vm.runInContext('pageFromUrl', context)(search, pages);
  const to = (search, page) => vm.runInContext('pageToUrl', context)(search, page);
  assert.equal(from('?page=3', 11), 3);
  assert.equal(from('', 11), 1);
  assert.equal(from('?page=3'), 3);
  for (const bad of ['?page=', '?page=abc', '?page=0', '?page=-2', '?page=2.5', '?page=1e3', '?page=%20', '?page=3x']) assert.equal(from(bad, 11), 1, bad);
  assert.equal(from('?page=99', 11), 11);
  assert.equal(from('?page=99999999999999999999', 11), 1);
  assert.equal(from('?page=4', 1), 1);
  assert.equal(to('', 3), '?page=3');
  assert.equal(to('?page=3', 1), '');
  assert.equal(to('?page=3', 5), '?page=5');
  assert.equal(to('?x=1&page=3', 1), '?x=1');
  assert.equal(to('?x=1', 2), '?x=1&page=2');
  assert.equal(from(to('?x=1', 7), 11), 7);
});

test('the list search, filters and page share one address: parse, build and bad values', () => {
  const allowed = {match: ['exact', 'route-mismatch', 'ingredient-mismatch', 'unmatched'], status: ['ongoing', 'upcoming']};
  const from = search => plain(vm.runInContext('listFromUrl', context)(search, allowed));
  const to = (search, state) => vm.runInContext('listToUrl', context)(search, state);
  assert.deepEqual(from(''), {q: '', match: '', status: '', page: 1});
  assert.deepEqual(from('?q=hep&match=route-mismatch&status=ongoing&page=2'), {q: 'hep', match: 'route-mismatch', status: 'ongoing', page: 2});
  assert.deepEqual(from('?match=bogus&status=x&page=abc'), {q: '', match: '', status: '', page: 1});
  assert.deepEqual(from('?match=&status=&q=%20%20'), {q: '', match: '', status: '', page: 1});
  assert.equal(from('?q=' + 'a'.repeat(300)).q.length, 100);
  assert.equal(to('', {q: '', match: '', status: '', page: 1}), '');
  assert.equal(to('', {q: 'hep', match: 'route-mismatch', status: '', page: 2}), '?q=hep&match=route-mismatch&page=2');
  assert.equal(to('?match=exact&page=4&x=1', {q: '', match: '', status: 'upcoming', page: 1}), '?x=1&status=upcoming');
  assert.equal(to('', {q: 'a b&c', match: '', status: '', page: 1}), '?q=a+b%26c');
  const state = {q: 'a b&c', match: 'exact', status: 'ongoing', page: 3};
  assert.deepEqual(from(to('', state)), state);
});

// ---- Search finds past shortages: the list falls back to the removed events when the current list has no match.
const REMOVED = [
  {NordicArticleNumber:'560833', name:'Elvanse', strength:'40 mg', form:'kapseli, kova', pack_label:{en:'30 capsules', fi:'30 kapselia'}, substances:'Lisdexamfetamine dimesylate', atc:'N06BA12', Company:'Takeda', first_seen:'2026-09-15', last_seen:'2026-09-15', removed_on:'2026-09-23'},
  {NordicArticleNumber:'510642', name:'Ozempic', strength:'0.25 mg', form:'injektioneste, liuos', pack_label:{en:'1.5 ml', fi:'1,5 ml'}, substances:'Semaglutide', atc:'A10BJ06', Company:'Novo Nordisk', first_seen:'2024-11-18', last_seen:'2024-11-18', removed_on:'2026-09-15', removed_after_gap:true},
  {NordicArticleNumber:'427014', name:'Paramax Comp', strength:'500 mg', form:'tabletti', substances:'Paracetamol, Metoclopramide', atc:'N02', Company:'Sanofi', first_seen:'2026-09-23', last_seen:'2026-09-23', removed_on:'2026-10-06', gaps:[{from:'2026-09-23', to:'2026-10-20', days:27}]},
  {NordicArticleNumber:'141019', name:'Ibutabs', strength:'200 mg', form:'tabletti', substances:'Ibuprofen', atc:'M01AE01', Company:'Orion', first_seen:'2024-11-18', last_seen:'2024-11-18', removed_on:'2026-09-15', removed_after_gap:true}
];
const CURRENT = [{NordicArticleNumber:'100001', name:'Buranagel', strength:'50 mg/g', substances:'Ibuprofen', atc:'M02AA13', form:'geeli', Company:'Orion', UnavailableFrom:'2026-02-02', EndingDate:'2027-02-01', removed_on:null}];
// Runs shortages.js against a fake page with the given search; fetch serves current.json and removed.json and records what was asked for.
async function listPage(search, {failRemoved = false, lang = 'en', gate = null, after = null} = {}) {
  const elements = {}, requested = [];
  const get = id => elements[id] ||= {textContent:'', innerHTML:'', hidden:false, value:'', parentElement:{hidden:false}, dataset:{}, handlers:{}, addEventListener(type, fn){ this.handlers[type] = fn; }, setAttribute(){}, open:false};
  const files = {'current.json': {events: CURRENT, snapshot_date:'2026-11-21'}, 'removed.json': {events: REMOVED}};
  const fetch = url => { requested.push(url); return failRemoved && url === 'removed.json' ? Promise.reject(Error(url)) : (url === 'current.json' && gate ? gate : Promise.resolve()).then(() => ({ok:true, json:() => Promise.resolve(files[url])})); };
  const root = {dataset:{}, classList:{remove(){}}};
  const document = {getElementById:get, documentElement:root, querySelector:() => ({checked:false, value:''}), querySelectorAll:() => []};
  const env = vm.createContext({Intl, Date, URLSearchParams, matchMedia:() => ({matches:false}), document, navigator:{language:lang}, localStorage:{getItem:() => lang, setItem(){}}, fetch, location:{search}, history:{replaceState(){}}, URL, setTimeout, clearTimeout});
  vm.runInContext(shared + '\n' + read('shortages.js'), env);
  const settle = async () => { for (let i = 0; i < 8; i++) await new Promise(resolve => setTimeout(resolve, 0)); };
  await settle();
  if (after) { await after(get); await settle(); }
  return {settle, list:get('list').innerHTML, count:get('result-count').textContent, requested, root, get};
}

test('a past package shows when it was last seen in a capture, never as supply returned, and links to its archived page', () => {
  setLanguage(context, 'en');
  const elvanse = context.pastRow(REMOVED[0]);
  assert.match(elvanse, /<a href="medicine\.html\?vnr=560833">Elvanse<\/a>/);
  assert.match(nb(elvanse), /<span>40 mg<\/span> <span>30 capsules<\/span>/);
  assert.match(elvanse, /Earlier on the list: last seen 15 Sep 2026 \(capture\)/);
  assert.match(elvanse, /Not on the list in the capture of 23 Sep 2026/);
  assert.match(elvanse, /See the archived page/);
  assert.doesNotMatch(elvanse, /class="impact|Shortage now|Starting soon/);
  setLanguage(context, 'fi');
  assert.match(context.pastRow(REMOVED[0]), /Aiemmin listalla: viimeksi nähty 15\.9\.2026 \(tilannekuva\)/);
  setLanguage(context, 'en');
});

test('gaps between captures are shown as not observed, also for a removal after a long gap', () => {
  setLanguage(context, 'en');
  assert.deepEqual(plain(context.pastNotes(REMOVED[1])), ['Earlier on the list: last seen 18 Nov 2024 (capture)', 'Not observed between 18 Nov 2024 and 15 Sep 2026.']);
  const inside = plain(context.pastNotes(REMOVED[2]));
  assert.ok(inside.includes('Not observed between 23 Sep 2026 and 20 Oct 2026.'), inside.join('|'));
  // A removal one capture after the last sighting is the date of a capture, not a gap.
  assert.ok(!plain(context.pastNotes(REMOVED[0])).some(x => /Not observed/.test(x)));
  setLanguage(context, 'fi');
  assert.ok(plain(context.pastNotes(REMOVED[1])).includes('Ei havaintoja välillä 18.11.2024–15.9.2026.'));
  setLanguage(context, 'en');
});

test('Finnish and English names find past packages (Elvanse, Ozempic, parasetamoli, ibuprofeeni)', () => {
  const names = q => context.pastMatches(REMOVED, q).map(e => e.name);
  assert.deepEqual(names('elvanse'), ['Elvanse']);
  assert.deepEqual(names('Ozempic'), ['Ozempic']);
  assert.deepEqual(names('semaglutide'), ['Ozempic']);
  assert.deepEqual(names('parasetamoli'), ['Paramax Comp']);
  assert.deepEqual(names('ibuprofeeni'), ['Ibutabs']);
  assert.deepEqual(names('560833'), ['Elvanse']);
  assert.deepEqual(names('nosuchmedicine'), []);
});

test('the earlier packages are read only when the current list has no match', async () => {
  const hit = await listPage('?q=burana');
  assert.deepEqual(hit.requested, ['current.json']);
  assert.match(hit.list, /Buranagel/);
  assert.equal(hit.count, '1 package');
  const miss = await listPage('?q=elvanse');
  assert.deepEqual(miss.requested, ['current.json', 'removed.json']);
  assert.match(miss.list, /Elvanse[\s\S]*Earlier on the list: last seen 15 Sep 2026 \(capture\)/);
  assert.equal(miss.count, 'Not on the list now. 1 package was on it earlier.');
  assert.equal(miss.root.dataset.searching, 'true');
  const none = await listPage('?q=');
  assert.deepEqual(none.requested, ['current.json']);
  assert.equal(none.root.dataset.searching, undefined);
});

test('Finnish names fall back to earlier packages in Finnish', async () => {
  const page = await listPage('?q=parasetamoli', {lang:'fi'});
  assert.match(page.list, /Paramax Comp/);
  assert.equal(page.count, 'Ei listalla nyt. 1 pakkaus oli listalla aiemmin.');
  const ibu = await listPage('?q=ibuprofeeni', {lang:'fi'});
  assert.match(ibu.list, /Buranagel/);
  assert.deepEqual(ibu.requested, ['current.json']);
});

test('the empty state keeps "not on the list" apart from "not available" and survives a failed load', async () => {
  const none = await listPage('?q=zzzz');
  assert.match(none.list, /Not on the list\. That does not guarantee your pharmacy has it\./);
  assert.equal(none.count, '0 packages');
  assert.doesNotMatch(none.list, /Earlier on the list/);
  const failed = await listPage('?q=elvanse', {failRemoved:true});
  assert.match(failed.list, /Not on the list\./);
  assert.match(failed.list, /Earlier captures could not be loaded/);
  assert.equal(failed.requested.filter(x => x === 'removed.json').length, 1);
});

test('the wording about earlier listings never says supply returned or the medicine is available', () => {
  const copy = vm.runInContext('copy', context);
  for (const lang of ['en', 'fi']) {
    const text = ['pastCount', 'pastLast', 'pastGone', 'pastStatus', 'pastOpen', 'pastNote', 'pastLoading', 'pastError'].map(k => { const v = copy[lang][k]; return typeof v === 'function' ? v(2) : v; });
    for (const line of text) assert.doesNotMatch(line, /returned|back in|restored|resolved|ended|palannut|palautunut|ratkennut|päättynyt|ei enää/i, `${lang}: ${line}`);
    assert.match(copy[lang].pastNote, lang === 'en' ? /does not show whether a medicine is available now/ : /ei kerro, onko lääke nyt saatavilla/);
    // "Not on the list" says where the package is; it never claims anything about the pharmacy shelf.
    assert.doesNotMatch(copy[lang].pastStatus, /availab|saatavil/i);
  }
});

test('a result carries a short impact chip next to the full label, and the compact phone rules hide the intro and the callout while searching', () => {
  setLanguage(context, 'en');
  const html = context.pkgCard({name:'Test', UnavailableFrom:'2026-11-06', EndingDate:'2026-12-01', atc:'N02', substitution_group:'42', other_packages_count:0}, NOW);
  assert.match(html, /<span class="impact-chip">No interchangeable product on the market<\/span>/);
  const css = read('style.css');
  for (const selector of ['html[data-searching] .page-head .lead', 'html[data-searching] #search-hint', 'html[data-searching] .crit-callout']) assert.ok(css.includes(selector), selector);
  assert.match(css, /@media \(max-width:719px\)\{\s*html\[data-searching\] \.page-head\{/);
});

test('nothing is answered, and the archive is not read, while current.json is still loading; early input is kept', async () => {
  let release;
  const gate = new Promise(resolve => { release = resolve; });
  const early = await listPage('', {gate, after: async get => { get('search').value = 'ibuprofeeni'; get('search').handlers.input(); }});
  assert.deepEqual(early.requested, ['current.json']);
  assert.doesNotMatch(early.list, /Not on the list|Ibutabs|Earlier on the list|Buranagel/);
  assert.equal(early.count, '');
  release();
  await early.settle();
  assert.deepEqual(early.requested, ['current.json']);
  assert.match(early.get('list').innerHTML, /Buranagel/);
  assert.doesNotMatch(early.get('list').innerHTML, /Ibutabs|Earlier on the list/);
  assert.equal(early.get('search').value, 'ibuprofeeni');
});

test('a search that a filter limits says so, keeps the query and offers to clear the filters (?q=burana&status=soon)', async () => {
  const page = await listPage('?q=burana&status=soon');
  assert.match(page.list, /No package on the current list matches this search with these filters\./);
  assert.match(page.list, /id="clear-inline">Clear filters</);
  assert.doesNotMatch(page.list, /Not on the list\./);
  assert.deepEqual(page.requested, ['current.json']);
  assert.equal(page.get('search').value, 'burana');
  const fi = await listPage('?q=burana&status=soon', {lang:'fi'});
  assert.match(fi.list, /Nykyisellä listalla ei ole tähän hakuun sopivaa pakkausta näillä suodattimilla\./);
  assert.match(fi.list, /Tyhjennä suodattimet/);
  // Without a filter the old messages stay.
  assert.match((await listPage('?q=zzzz')).list, /Not on the list\./);
  assert.match((await listPage('?status=soon')).list, /Nothing matches these filters/);
});

test('the filter panel starts closed on a phone while a search is on, and open without a search, on a wide screen', async () => {
  const withSearch = await listPage('?q=burana&status=now');
  assert.equal(withSearch.get('filters').open, false);
  assert.match(withSearch.get('filters-count').textContent, /\(1\)/);
  assert.equal((await listPage('?status=now')).get('filters').open, true);
  assert.equal((await listPage('?q=burana')).get('filters').open, false);
});

test('the phone chip states only what the register shows, in both languages', () => {
  const copy = vm.runInContext('copy', context);
  assert.equal(copy.en.impactChip_substitute, 'Interchangeable package on the market');
  assert.equal(copy.fi.impactChip_substitute, 'Vaihtokelpoinen pakkaus kaupan');
  for (const lang of ['en', 'fi']) for (const level of ['substitute', 'no_alternative', 'nogroup', 'vet']) {
    assert.doesNotMatch(copy[lang]['impactChip_' + level], /usually|yleensä|available|saatavilla|substitute|can give/i, `${lang} ${level}`);
    setLanguage(context, lang);
    const html = context.pkgCard({name:'T', UnavailableFrom:'2026-11-06', atc: level === 'vet' ? 'QN02' : 'N02', substitution_group: level === 'nogroup' ? '' : '42', other_packages_count: level === 'substitute' ? 2 : 0}, NOW);
    assert.ok(html.includes(`<span class="impact-chip">${copy[lang]['impactChip_' + level]}</span>`), `${lang} ${level}`);
  }
  setLanguage(context, 'en');
});

// ---- Medicine pages (site/medicines.js): one page for a verified group, each package apart.
const mdEvent = (vnr, extra = {}) => ({NordicArticleNumber: vnr, name: 'Burana', strength: '400 mg', Company: 'Orion', UnavailableFrom: '2026-11-01', EndingDate: '2026-12-20', DateOfTheNotification: '2026-10-30', first_seen: '2026-11-03', last_seen: '2026-11-24', removed_on: null, listed_at_first_capture: false, end_changes: [{seen: '2026-11-03', date: '2026-12-20'}], pack_label: {en: `pack ${vnr}`, fi: `pakkaus ${vnr}`}, ...extra});
const mdPage = {id: 'm0123456789ab', snapshot_date: '2026-11-24', medicine: {name: 'Burana', strength: '400 mg', substances: ['Ibuprofen'], form: 'tabletti, kalvopäällysteinen', routes: ['Suun kautta'], atc: 'M01AE01', container: '', unit_size: '', device: ''},
  packages: [{vnr: '111111', events: [mdEvent('111111'), mdEvent('111111', {removed_on: '2026-10-01', last_seen: '2026-09-30', first_seen: '2026-09-01'})]}, {vnr: '222222', events: [mdEvent('222222', {removed_on: '2026-11-10', last_seen: '2026-11-09'})]}]};

test('a medicine page shows each package apart, with what Fimea says and our reading in separate blocks', () => {
  const [env, get] = pageEnv(['medicines.js']);
  for (const lang of ['en', 'fi']) {
    vm.runInContext(`language='${lang}'; page = ${JSON.stringify(mdPage)}`, env);
    env.render();
    const html = get('medicines').innerHTML, t = vm.runInContext(`copy.${lang}`, env);
    assert.equal((html.match(/class="panel med-pkg /g) || []).length, 2, 'one panel for each package');
    assert.equal((html.match(new RegExp(`<h4>${t.mdFimea}</h4>`, 'g')) || []).length, 2);
    assert.equal((html.match(new RegExp(`<h4>${t.mdOurs}</h4>`, 'g')) || []).length, 2);
    assert.match(html, /<h1 class="md-title">Burana 400.mg<\/h1>/); assert.match(html, /Ibuprofen/);
    for (const vnr of ['111111', '222222']) assert.match(html, new RegExp(String.raw`href="medicine\.html\?vnr=${vnr}"`), 'each package keeps its package page');
    // A package with a current and an ended notice keeps both; the ended package says when it was last listed, not that supply returned.
    assert.equal((html.match(/<details class="md-more">/g) || []).length, 1);
    assert.match(html, lang === 'en' ? /last listed on 9 Nov 2026/ : /viimeksi listalla 9\.11\.2026/);
    assert.match(html, new RegExp(t.mdReading.slice(0, 30)));
  }
});

test('a medicine page makes no substitute, stock or group claim and shows no Fimea substitution code', () => {
  const [env, get] = pageEnv(['medicines.js']);
  const withCode = JSON.parse(JSON.stringify(mdPage));
  withCode.packages[0].events[0].substitution_group = '1299';
  vm.runInContext(`language='en'; page = ${JSON.stringify(withCode)}`, env);
  env.render();
  const html = get('medicines').innerHTML;
  assert.doesNotMatch(html, /1299|Substitution group|substitution group|interchangeable|suitable|alternative|other packages|on the market|available/i);
  assert.doesNotMatch(html, /class="alts"|impact/);
  // The only words about replacing or stock are the denial in the note.
  const text = html.replace(/<[^>]+>/g, ' ');
  assert.equal((text.match(/replace|in stock/gi) || []).length, 2);
  for (const lang of ['en', 'fi']) {
    const copy = vm.runInContext(`copy.${lang}`, context);
    for (const [key, value] of Object.entries(copy)) if (key.startsWith('md') && typeof value === 'string' && key !== 'mdReading') assert.doesNotMatch(value, /replace|stock|interchang|suitable|alternative|substitut|korvaa|vaihto|saatavilla|sopiva/i, key);
  }
});

test('an unknown medicine address shows a helpful state, and the copy of both languages has the same keys', () => {
  const [env, get] = pageEnv(['medicines.js']);
  assert.equal(env.idFromSearch('?id=%20m0123456789ab%20'), 'm0123456789ab');
  assert.equal(env.validId('m0123456789ab'), true); assert.equal(env.validId('../x'), false); assert.equal(env.validId('0123456789ab'), false);
  vm.runInContext("language='fi'; page = {missing: true}", env);
  env.render();
  assert.match(get('medicines').innerHTML, /Lääkettä ei löytynyt/); assert.match(get('medicines').innerHTML, /action="shortages\.html"/);
  const en = Object.keys(vm.runInContext('copy.en', context)).filter(k => /^md|_medicines$/.test(k)), fi = Object.keys(vm.runInContext('copy.fi', context)).filter(k => /^md|_medicines$/.test(k));
  assert.deepEqual(en, fi); assert.equal(en.length, 26);
});

test('search results open the medicine page when the build made one, else the package page; past shortages keep working', () => {
  const [env] = pageEnv(['shortages.js']);
  vm.runInContext("language='en'", env);
  const paged = mdEvent('111111', {medicine_page: 'm0123456789ab'}), plain = mdEvent('333333');
  const now = Date.UTC(2026, 10, 24);
  assert.match(env.pkgCard(paged, now, 2, true), /href="medicines\.html\?id=m0123456789ab&amp;vnr=111111"/);
  assert.match(env.pkgCard(plain, now, 2, true), /href="medicine\.html\?vnr=333333"/);
  // Cards outside the search lists, and a bad id, keep the package page.
  assert.match(env.pkgCard(paged, now, 2), /href="medicine\.html\?vnr=111111"/);
  assert.match(env.pkgCard(mdEvent('111111', {medicine_page: '"><script>'}), now, 2, true), /href="medicine\.html\?vnr=111111"/);
  const gone = mdEvent('111111', {removed_on: '2026-11-10', last_seen: '2026-11-09', medicine_page: 'm0123456789ab'});
  assert.match(env.pastRow(gone), /href="medicines\.html\?id=m0123456789ab&amp;vnr=111111"/); assert.match(env.pastRow(mdEvent('333333', {removed_on: '2026-11-10'})), /href="medicine\.html\?vnr=333333"/);
  assert.equal(env.pastMatches([gone], 'burana').length, 1);
});

const dateText = (lang, iso) => { const [y, m, d] = iso.split('-').map(Number); return lang === 'fi' ? `${d}.${m}.${y}` : `${d} Nov ${y}`; };
test('a notice that left the list is not the package leaving it: the wording says notice, in English and Finnish', () => {
  const [env, get] = pageEnv(['medicines.js']);
  // The package is still listed under an updated notice (vnr_listed_at_removal), the older notice is gone.
  const pkg = {vnr: '168299', events: [mdEvent('168299', {first_seen: '2026-11-24', UnavailableFrom: '2026-11-20'}), mdEvent('168299', {removed_on: '2026-11-24', last_seen: '2026-11-23', first_seen: '2026-11-03', vnr_listed_at_removal: true})]};
  for (const lang of ['en', 'fi']) {
    vm.runInContext(`language='${lang}'; page = ${JSON.stringify({...mdPage, packages: [pkg]})}`, env);
    env.render();
    const html = get('medicines').innerHTML, t = vm.runInContext(`copy.${lang}`, env);
    const older = html.slice(html.indexOf('<details class="md-more">'));
    assert.ok(older.includes(t.mdLeftText(dateText(lang, '2026-11-23'))), 'status line speaks of the notice');
    assert.ok(older.includes(t.mdLastListed) && older.includes(t.mdGone(dateText(lang, '2026-11-24'))), 'timeline speaks of the notice');
    assert.match(older, lang === 'en' ? /This notice was on the list in our captures from 3 Nov 2026 to 23 Nov 2026\./ : /Ilmoitus oli listalla tilannekuvissamme 3\.11\.2026–23\.11\.2026\./);
    assert.doesNotMatch(older, /This package was last listed|Pakkaus oli viimeksi listalla|No longer on the list|Ei enää listalla/);
  }
  // The package-level tab names the notice too, and the package page's own wording is not changed.
  vm.runInContext("language='en'", env);
  assert.match(env.timelineMarkup(pkg.events[1], true), /Last listed/); assert.doesNotMatch(env.timelineMarkup(pkg.events[1], true), /Notice last listed/);
  // A gap in the captures keeps its wording and the removal time stays unknown.
  const gap = mdEvent('171603', {removed_on: '2026-09-15', last_seen: '2024-11-18', first_seen: '2024-11-03', removed_after_gap: true, gaps: []});
  vm.runInContext(`page = ${JSON.stringify({...mdPage, packages: [{vnr: '171603', events: [gap]}]})}`, env);
  env.render();
  const html = get('medicines').innerHTML;
  assert.match(html, /Not observed between 18 Nov 2024 and 15 Sep 2026\./);
  assert.match(html, /last seen in the capture of 18 Nov 2024, not on the list in the next capture, 15 Sep 2026, and no captures between\. When it left the list is not known/);
  assert.doesNotMatch(html, /absent on 15 Sep 2026/);
});

test('each notice names its own source and captures, and the page-level line is only the latest file date', () => {
  const [env, get] = pageEnv(['medicines.js']);
  vm.runInContext("language='en'", env);
  const ended = mdEvent('222222', {removed_on: '2026-11-10', last_seen: '2026-11-09'});
  vm.runInContext(`page = ${JSON.stringify(mdPage)}`, env);
  assert.match(env.noticeSource(ended, '2026-11-24'), /last seen in the capture of 9 Nov 2026, absent on 10 Nov 2026/);
  assert.doesNotMatch(env.noticeSource(ended, '2026-11-24'), /24 Nov/);
  assert.match(env.noticeSource(mdEvent('111111'), '2026-11-24'), /data of 24 Nov 2026/);
  vm.runInContext("language='fi'", env);
  assert.match(env.noticeSource({...ended, removed_after_gap: true}, '2026-11-24'), /ei listalla seuraavassa tilannekuvassa 10\.11\.2026.*ei ole tiedossa/);
  vm.runInContext("language='en'", env); env.render();
  const html = get('medicines').innerHTML;
  assert.match(html, /The latest file we hold is of 24 Nov 2026; each notice names its own captures/);
  assert.equal((html.match(/class="note md-notice-source"/g) || []).length, 3, 'one source line for each of the three notices');
});

test('a search result opens its own package on the medicine page, and falls back to the package page', async () => {
  const [env, get] = pageEnv(['medicines.js']);
  vm.runInContext("language='en'", env);
  assert.equal(env.vnrFromSearch('?id=m0123456789ab&vnr=222222'), '222222'); assert.equal(env.vnrFromSearch('?id=m0123456789ab'), '');
  assert.equal(env.packageUrlWhenAbsent(mdPage, '222222'), ''); assert.equal(env.packageUrlWhenAbsent(mdPage, ''), '');
  assert.equal(env.packageUrlWhenAbsent(mdPage, '999999'), 'medicine.html?vnr=999999');
  assert.equal(env.packageUrlWhenAbsent({missing: true}, '222222'), 'medicine.html?vnr=222222');
  assert.equal(env.packageUrlWhenAbsent({missing: true}, ''), '', 'no VNR: the not-found state');
  // The scroll is deferred: it waits for the fonts and a frame, runs once, and any reader input cancels it for good.
  const run = async (input) => {
    const scrolled = [], listeners = {}, frames = [];
    let fontsReady; const fonts = {ready: new Promise(resolve => { fontsReady = resolve; })};
    vm.runInContext('scrolled = false', env);
    env.window = {addEventListener: (name, fn) => { (listeners[name] ||= []).push(fn); }, removeEventListener: (name, fn) => { listeners[name] = (listeners[name] || []).filter(x => x !== fn); }};
    env.document.fonts = fonts; env.requestAnimationFrame = fn => frames.push(fn);
    get('pk-222222').scrollIntoView = () => scrolled.push('pk-222222');
    vm.runInContext(`selectedVnr='222222'; page = ${JSON.stringify(mdPage)}`, env);
    env.render(); env.render();
    assert.deepEqual(scrolled, [], 'nothing scrolls before the layout is ready');
    if (input) for (const fn of listeners[input] || []) fn();
    fontsReady(); await fonts.ready; await Promise.resolve();
    frames.splice(0).forEach(fn => fn());
    await new Promise(resolve => setTimeout(resolve, 600));   // no later timer scrolls again
    frames.splice(0).forEach(fn => fn());
    return {scrolled, left: Object.values(listeners).flat().length};
  };
  assert.deepEqual(await run(null), {scrolled: ['pk-222222'], left: 0}, 'one scroll, and its input listeners are removed');
  for (const input of ['wheel', 'touchstart', 'keydown', 'pointerdown']) assert.deepEqual((await run(input)).scrolled, [], `${input} from the reader cancels the scroll`);
  const html = get('medicines').innerHTML;
  assert.match(html, /is-selected" aria-labelledby="pk-222222"/); assert.doesNotMatch(html, /is-selected" aria-labelledby="pk-111111"/);
  assert.match(html, /<h3 id="pk-222222" class="med-pkg-name">pack 222222 <span class="md-vnr">VNR 222222<\/span><\/h3>/);
});

test('Home and Trends read the old count key in files saved before the rename, and an explicit new value wins', () => {
  const [home] = pageEnv(['home.js']);
  // The real summary.json before the rename: only `critical`.
  vm.runInContext("data = {impact: {substitute: 539, critical: 61, nogroup: 117, vet: 39}}", home);
  const legacy = home.impactCounts();
  assert.equal(legacy.no_alternative, 61); assert.equal(legacy.substitute, 539);
  assert.match(home.triageMarkup(legacy), /impact=no_alternative"[^>]*>.*?<span class="tri-num">61<\/span>/);
  // Both keys: the new one is read, even when it is 0.
  vm.runInContext("data = {impact: {substitute: 5, no_alternative: 0, critical: 61, nogroup: 1, vet: 0}}", home);
  assert.equal(home.impactCounts().no_alternative, 0);
  vm.runInContext("data = {impact: {substitute: 5, no_alternative: 7, critical: 7, nogroup: 1, vet: 0}}", home);
  assert.equal(home.impactCounts().no_alternative, 7);
  // Raw legacy counts (older HTML with the new script): the number, the share and the bar all use the old key.
  const raw = home.triageMarkup({substitute: 531, critical: 61, nogroup: 117});
  assert.match(raw, /impact=no_alternative"[^>]*>.*?<span class="tri-num">61<\/span>/);
  assert.match(raw, /impact=no_alternative".*?class="part" width="8.60"/);
  const [trends, get] = pageEnv(['trends.js']);
  const history = [{date:'2026-11-23', gap_days:1}, {date:'2026-11-24', gap_days:1}];
  const row = (date, extra) => Object.assign({date, register_date: date, total: 9, substitute: 1, nogroup: 2, vet: 3}, extra);
  trends.drawCritical({history, max_gap_days: 14, newly_critical: [], triage_counts: [row('2026-11-24', {critical: 61}), row('2026-11-23', {no_alternative: 0, critical: 60})]});
  const table = get('triage-record').innerHTML;
  assert.match(table, /<td>24 Nov 2026<\/td><td>1<\/td><td>61<\/td><td>2<\/td><td>3<\/td>/);
  assert.match(table, /<td>23 Nov 2026<\/td><td>1<\/td><td>0<\/td><td>2<\/td><td>3<\/td>/);
});

test('the About page and the footer feedback link exist in English and Finnish', () => {
  const copy = vm.runInContext('copy', context);
  for (const lang of ['en', 'fi']) for (const key of ['aboutShortTitle', 'aboutNot1', 'aboutNot2', 'aboutNot3', 'aboutSrcFimea', 'aboutSrcEma', 'aboutSrcChanged', 'aboutLimTitle', 'feedbackTitle', 'feedbackLink', 'footerFeedback']) assert.ok(copy[lang][key], lang + ' ' + key);
  assert.match(copy.en.aboutNot1, /unavailable everywhere/); assert.match(copy.fi.aboutNot1, /ei tarkoita, ettei lääke ole saatavilla missään/);
  assert.match(copy.en.aboutNot2, /not necessarily available/); assert.match(copy.fi.aboutNot2, /ei tarkoita, että se on saatavilla/);
  assert.match(copy.en.aboutNot3, /not medical advice/); assert.match(copy.fi.aboutNot3, /ei lääketieteellinen neuvo/);
  for (const html of Object.values(pages)) assert.match(html, /href="(?:\/shortage-radar\/)?about\.html#feedback" data-i18n="footerFeedback"/);
  assert.match(pages['about.html'], /id="feedback"/);
});
