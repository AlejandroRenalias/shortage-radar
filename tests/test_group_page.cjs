const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {execFileSync} = require('node:child_process');
const read = name => fs.readFileSync('site/' + name, 'utf8');
const ctx = vm.createContext({Intl, Date, URLSearchParams});
vm.runInContext(read('i18n.js') + '\n' + read('lib.js') + '\n' + read('group.js'), ctx);
const run = code => vm.runInContext(code, ctx);

// Words the new texts of the group page must never use: they would say or suggest that a pharmacy has a package.
const BANNED_EN = [/\bavailab/i, /\bin stock\b/i, /\bout of stock\b/i, /\bsuppl(y|ied|ies|ier)/i, /shortage-free/i, /\bsafe/i, /\bfragile/i, /\brisk/i, /\bsubstitut/i];
const BANNED_FI = [/varastossa/i, /varasto(?!tarkistus)/i, /saatavilla/i, /saatavissa/i, /saatavuus(?!häiriö)/i, /toimitu/i, /toimitta/i, /toimitettavissa/i, /turvallinen/i, /turvallis/i, /turvaton/i, /korvaava/i, /korvike/i, /riski/i, /hauras/i, /loppunut/i];
const STOCK_EN = 'This is not a stock check. Ask your pharmacy.';
const STOCK_FI = 'Tämä ei ole varastotarkistus. Kysy apteekista.';
// Every text of the group page, for the numbers that change its words (and a company name).
function groupTexts(lang) {
  const t = run(`copy.${lang}`), out = [];
  run(`language='${lang}'`);
  for (const key of Object.keys(t).filter(k => /^grp[A-Z]/.test(k) || k === 'title_group' || k === 'desc_group')) {
    const v = t[key];
    if (typeof v === 'string') { out.push([key, v]); continue; }
    const args = {grpSummary: [[0, 0, 0, 0], [1, 1, 1, 1], [7, 7, 0, 0], [12, 2, 5, 3]], grpCode: [['0733']], grpAltMany: [[2], [29]], grpAllFrom: [['Glenmark Pharmaceuticals Nordic AB']], grpCoverage: [['25 Nov 2026', '25 Nov 2026']]}[key];
    assert.ok(args, `${lang} ${key}: add sample arguments`);
    for (const a of args) out.push([key, v(...a)]);
  }
  return out;
}

test('the group page has the same text keys in English and Finnish, and the fixed lines say what they must', () => {
  const keys = lang => Object.keys(run(`copy.${lang}`)).filter(k => /^grp[A-Z]/.test(k) || /_group$/.test(k)).sort();
  assert.deepEqual(keys('en'), keys('fi'));
  assert.ok(keys('en').length >= 14);
  assert.equal(run('copy.en.grpStock'), STOCK_EN);
  assert.equal(run('copy.fi.grpStock'), STOCK_FI);
  assert.equal(run('copy.en.grpAlt0'), 'No other interchangeable package found in the data.');
  assert.equal(run('copy.en.grpAlt1'), 'Narrow group: 1 other package listed.');
  assert.equal(run('copy.en.grpOnList'), 'On Fimea’s shortage list');
  assert.equal(run('copy.en.grpOffList'), 'Not on Fimea’s shortage list');
  assert.equal(run('copy.en.grpUnknown'), 'No package of this group is on Fimea’s shortage list now. This does not show if the pharmacy has it.');
  assert.equal(run('copy.en.grpCoverage')('25 Nov 2026', '24 Nov 2026'), 'Today only. Fimea shortage list of 25 Nov 2026, register of 24 Nov 2026.');
});

test('no new English or Finnish text of the group page uses a word that says or hints that a pharmacy has a package', () => {
  for (const [lang, banned, stock] of [['en', BANNED_EN, STOCK_EN], ['fi', BANNED_FI, STOCK_FI]]) {
    const texts = groupTexts(lang);
    assert.ok(texts.length > 15);
    for (const [key, text] of texts) {
      // The one sentence that names stock is the fixed line; "stock" is allowed nowhere else.
      const rest = text.replace(stock, '').replace(/ \| (Saatavuustutka|Shortage Radar)$/, '');  // the site's name is not new text
      for (const word of banned) assert.doesNotMatch(rest, word, `${lang} ${key}: ${text}`);
      if (lang === 'en') assert.doesNotMatch(rest, /\bstock\b/i, `${lang} ${key}: ${text}`);
      if (lang === 'fi') assert.doesNotMatch(rest, /varasto/i, `${lang} ${key}: ${text}`);
    }
  }
});

test('the banned word lists catch what they are meant to catch', () => {
  for (const w of ['available', 'Availability', 'in stock', 'out of stock', 'supply', 'supplied', 'shortage-free', 'safe', 'fragile', 'substitute', 'risky']) assert.ok(BANNED_EN.some(r => r.test(w)), w);
  for (const w of ['varastossa', 'saatavilla', 'toimitus', 'turvallinen', 'korvaava', 'saatavuus', 'varasto']) assert.ok(BANNED_FI.some(r => r.test(w)), w);
  // The site's own word for a shortage and the fixed line are fine.
  assert.ok(!BANNED_FI.some(r => r.test('saatavuushäiriölistalla')) && !BANNED_FI.some(r => r.test('varastotarkistus')));
});

// The rendered page, from a group of the build's data shape.
const pack = (vnr, name, listed, extra = {}) => Object.assign({vnr, name, strength: '20 mg', pack_label: {en: '30 capsules', fi: '30 kapselia'}, company: 'Firma Oy', listed, alt: !listed, link: listed ? vnr : ''}, extra);
const GROUP = (alternatives, companies, packages) => ({heading: {substance: 'Isotretinoin', strength: '20 mg', form: 'kapseli, pehmeä'}, counts: {market: packages.length, listed: packages.filter(p => p.listed).length, alternatives, companies: companies.length}, alt_companies: companies, packages});
const META = {snapshot_date: '2026-11-25', source_metadata: {register_date: '2026-11-24'}};
function page(group, lang = 'en', g = '0733') {
  const root = {innerHTML: ''};
  ctx.document = {title: '', getElementById: () => root};
  run(`language='${lang}'; code='${g}'; shard=${JSON.stringify(Object.assign({groups: group ? {[g]: group} : {}}, META))}`);
  run('render()');
  return {html: root.innerHTML, title: ctx.document.title};
}
const nb = html => html.replace(/ /g, ' ');
const text = html => nb(html).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');

test('0 alternatives, exactly 1, many, and all from one company each get their own label', () => {
  const zero = page(GROUP(0, [], [pack('1', 'A', true), pack('2', 'A', true)])).html;
  assert.match(text(zero), /No other interchangeable package found in the data\./);
  assert.doesNotMatch(zero, /All from/);
  const one = page(GROUP(1, ['Teva B.V.'], [pack('1', 'A', true), pack('2', 'B', false)])).html;
  assert.match(text(one), /Narrow group: 1 other package listed\./);
  assert.match(text(one), /All from Teva B\.V\./);
  const many = page(GROUP(4, ['Glenmark', 'Orion'], [pack('1', 'A', true), pack('2', 'B', false), pack('3', 'B', false), pack('4', 'B', false), pack('5', 'B', false)])).html;
  assert.match(text(many), /4 other interchangeable packages found in the data\./);
  assert.doesNotMatch(many, /All from/);
  const same = page(GROUP(4, ['Glenmark'], [pack('1', 'A', true), pack('2', 'B', false)])).html;
  assert.match(text(same), /All from Glenmark/);
  assert.match(text(many), /5 packages of this group are on the market and 1 is on Fimea’s shortage list; 4 other interchangeable packages found in the data, from 2 companies\./);
});

test('rows: name, strength, pack, company, VNR, a plain mark, listed first; only a package with a page links to it', () => {
  const html = nb(page(GROUP(1, ['Teva'], [pack('034370', 'Isotretinoin Orifarm', true), pack('048600', 'Other', false)])).html);
  const rows = html.split('<li class="grp-row').slice(1);
  assert.equal(rows.length, 2);
  assert.match(rows[0], /On Fimea’s shortage list/);
  assert.match(rows[0], /Isotretinoin Orifarm 20 mg/);
  assert.match(rows[0], /30 capsules/);
  assert.match(rows[0], /Firma Oy/);
  assert.match(rows[0], /<a href="medicine\.html\?vnr=034370">034370<\/a>/);
  assert.match(rows[1], /Not on Fimea’s shortage list/);
  assert.doesNotMatch(rows[1], /<a href="medicine/);
  assert.match(rows[1], /048600/);
});

test('the page has one h1 then h2 only, the code is small text, the two fixed lines are always there, and no row needs a wide table', () => {
  const shot = page(GROUP(0, [], [pack('1', 'A', true)])), html = nb(shot.html), title = nb(shot.title);
  assert.equal((html.match(/<h1/g) || []).length, 1);
  assert.equal((html.match(/<h2/g) || []).length, 1);
  assert.doesNotMatch(html, /<h[3-6]|<table/);
  assert.match(html, /<h1 class="grp-title">Isotretinoin 20 mg, capsule<\/h1><p class="grp-code">Group 0733<\/p>/);
  assert.match(text(html), /This is not a stock check\. Ask your pharmacy\./);
  assert.match(text(html), /Today only\. Fimea shortage list of 25 Nov 2026, register of 24 Nov 2026\./);
  assert.equal(title, 'Isotretinoin 20 mg, capsule | Shortage Radar');
  const fi = page(GROUP(0, [], [pack('1', 'A', true)]), 'fi');
  assert.match(text(fi.html), /Ryhmä 0733/);
  assert.match(text(fi.html), /Tämä ei ole varastotarkistus\. Kysy apteekista\./);
  assert.match(text(fi.html), /Vain tämä päivä\. Fimean saatavuushäiriölista 25\.11\.2026, rekisteri 24\.11\.2026\./);
});

test('a long group shows every listed package and the first others, the rest opens on request', () => {
  const packages = [pack('1', 'A', true), pack('2', 'A', true)].concat(Array.from({length: 24}, (_, i) => pack(String(100 + i), 'B', false)));
  const html = page(GROUP(24, ['X', 'Y'], packages)).html;
  assert.equal((html.match(/<li class="grp-row/g) || []).length, 26);
  const [shown, rest] = html.split('<details');
  assert.equal((shown.match(/<li class="grp-row/g) || []).length, 2 + 8);
  assert.match(rest, /Show all 26/);
});

test('an unknown or invalid code gives the short neutral page, with no data', () => {
  for (const g of ['9999', 'abc', '']) {
    const html = page(null, 'en', g).html;
    assert.match(text(html), /No package of this group is on Fimea’s shortage list now\. This does not show if the pharmacy has it\./);
    assert.match(text(html), /This is not a stock check\. Ask your pharmacy\./);
    assert.doesNotMatch(html, /grp-row|grp-alt|Narrow group|other interchangeable/);
    assert.equal((html.match(/<h1/g) || []).length, 1);
  }
  assert.match(page(null, 'en', '9999').html, /<h1 class="grp-title">Group 9999<\/h1>/);
  assert.doesNotMatch(page(null, 'en', '<b>').html, /<b>/);
  assert.match(text(page(null, 'fi', '9999').html), /Mikään tämän ryhmän pakkaus ei ole nyt Fimean saatavuushäiriölistalla\./);
});

test('every text the rendered page shows passes the banned-word check in both languages', () => {
  const packages = [pack('1', 'A', true), pack('2', 'B', false)];
  for (const [lang, banned, stock] of [['en', BANNED_EN, STOCK_EN], ['fi', BANNED_FI, STOCK_FI]]) {
    for (const group of [GROUP(0, [], packages), GROUP(1, ['Teva'], packages), GROUP(5, ['A', 'B'], packages), null]) {
      const shown = text(page(group, lang).html).replace(stock, '').replace(/Not medical advice\./, '');
      for (const word of banned) assert.doesNotMatch(shown, word, `${lang}: ${shown}`);
    }
  }
});

test('the medicine page and the shortage list link to the group page, and the page is not in the main menu', () => {
  run("language='en'");
  const card = run('pkgCard')({NordicArticleNumber: '034370', name: 'X', UnavailableFrom: '2026-11-01', substitution_group: '0733', impact: 'no_alternative', form: 'kapseli', atc: 'D10'}, Date.UTC(2026, 10, 25), 3, true, true);
  assert.match(card, /<a href="group\.html\?g=0733">Packages of this group<\/a>/);
  assert.doesNotMatch(run('pkgCard')({NordicArticleNumber: '034370', name: 'X', UnavailableFrom: '2026-11-01', substitution_group: '0733', impact: 'no_alternative', form: 'kapseli', atc: 'D10'}, Date.UTC(2026, 10, 25)), /group\.html/);
  assert.doesNotMatch(run('pkgCard')({NordicArticleNumber: '1', name: 'X', UnavailableFrom: '2026-11-01', substitution_group: '', form: 'kapseli', atc: 'D10'}, Date.UTC(2026, 10, 25), 3, true, true), /group\.html/);
  assert.doesNotMatch(run('pkgCard')({NordicArticleNumber: '1', name: 'X', UnavailableFrom: '2026-11-01', substitution_group: '0733', form: 'injektio', atc: 'QJ01'}, Date.UTC(2026, 10, 25), 3, true, true), /group\.html/);
  assert.match(read('medicine.js'), /group\.html\?g=\$\{encodeURIComponent\(code\)\}/);
  const pages = JSON.parse(execFileSync('python', ['-c', "import json,sys;sys.path.insert(0,'scripts');from pages import render_pages;print(json.dumps(render_pages(749)))"], {encoding: 'utf8'}));
  const nav = pages['group.html'].match(/<nav class="nav"[\s\S]*?<\/nav>/)[0];
  assert.equal((nav.match(/<a /g) || []).length, 5);
  assert.doesNotMatch(nav, /group\.html/);
  assert.match(pages['group.html'], /<script src="group\.js" defer><\/script>/);
  assert.doesNotMatch(pages['index.html'] + pages['shortages.html'], /href="group\.html/);
});
