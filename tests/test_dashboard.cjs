const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('site/app.js', 'utf8').split('function drawList(')[0];
const context = vm.createContext({Intl, Date});
vm.runInContext(source, context);

test('initial language is selected and content hidden before translation', () => {
  const html = fs.readFileSync('site/index.html', 'utf8');
  const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
  assert.match(html, /html\.i18n-pending body\{visibility:hidden\}/);
  for (const [browser, saved, expected] of [['fi-FI', null, 'fi'], ['en-US', 'fi', 'fi'], ['fi-FI', 'en', 'en']]) {
    const classes = new Set();
    const document = {documentElement: {lang:'en', classList: {add: name => classes.add(name)}}};
    vm.runInNewContext(script, {document, navigator:{language:browser}, localStorage:{getItem:() => saved}});
    assert.equal(document.documentElement.lang, expected);
    assert.ok(classes.has('i18n-pending'));
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
  assert.equal(context.timestampText('2026-11-21T00:30:00Z'), '21.11.2026 klo 00.30 UTC');
});

test('Finnish counts, forms and shortage wording read naturally', () => {
  vm.runInContext("language = 'fi'", context);
  assert.equal(vm.runInContext('copy.fi.count(1)', context), '1 ilmoitus');
  assert.equal(vm.runInContext('copy.fi.count(2)', context), '2 ilmoitusta');
  assert.equal(context.formText('resoribletti'), 'Kielen alle liukeneva tabletti');
  assert.equal(context.formText('peräruiskeliuos'), 'Peräruiske');
  assert.equal(context.groupName('B01', 'fi'), 'Veren ja verenkierron lääkkeet');
  const html = context.card({name:'Test', UnavailableFrom:'2026-11-06', EndingDate:'2026-12-01', atc:'B01'}, Date.UTC(2026,10,21));
  assert.match(html, /Saatavuushäiriö alkanut 6\.11\.2026 \(15 päivää\)/);
  assert.match(html, /Arvioidaan olevan taas saatavilla noin 1\.12\.2026 \(yrityksen arvio\)/);
  assert.match(html, /Lääkeryhmä: Veren ja verenkierron lääkkeet/);
});
