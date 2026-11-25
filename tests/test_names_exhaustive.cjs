// Exhaustive checks over the real register data (site/names.json and site/current.json, made by scripts/build.py).
// They are skipped when the build output is not there; the pages-build job of .github/workflows/test.yml builds it and runs them.
//  (a) every name + strength string of the name index, written in three formats, resolves to itself: a card for that exact name and strength, never "not found", never a suggestion only;
//  (b) every package on the shortage list shows its shortage card when searched by its own name + strength in the same three formats, and never a "not on the list" card for it.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const have = ['names.json', 'current.json'].every(f => fs.existsSync('site/' + f));
const read = name => fs.readFileSync('site/' + name, 'utf8');

function load() {
  const elements = {};
  const get = id => elements[id] ||= {textContent: '', innerHTML: '', hidden: true, href: '', value: 'en', dataset: {}, addEventListener() {}, setAttribute() {}};
  const document = {getElementById: get, documentElement: {dataset: {}, classList: {remove() {}}}, querySelector: () => ({}), querySelectorAll: () => []};
  const env = vm.createContext({Intl, Date, URLSearchParams, matchMedia: () => ({matches: false}), document, navigator: {language: 'en'}, localStorage: {getItem: () => null, setItem() {}}, fetch: () => new Promise(() => {}), location: {search: ''}});
  vm.runInContext(['i18n.js', 'lib.js', 'patient.js'].map(read).join('\n'), env);
  return env;
}

// The three formats of a label (name + strength), as a patient may type it.
const formats = (name, strength) => [
  `${name} ${strength}`.trim(),                                                     // as the register writes it
  `${name} ${strength.replace(/\s+/g, '')}`.trim(),                                 // no spaces in the strength: "50mg/g", "0.03mg/3mg"
  `  ${name} ${strength}`.toUpperCase().replace(/ /g, '   ').trim() + '  ',         // upper case and extra spaces
];

test('every name + strength of names.json, in three formats, resolves to itself', {skip: !have && 'site/names.json is not built'}, () => {
  const env = load();
  const index = JSON.parse(read('names.json'));
  env.index = index;
  const canon = s => vm.runInContext('normalizeStrength', env)(s);
  const bad = [];
  let tested = 0;
  const labels = [];
  for (const row of index.names) { const [name, ...strengths] = row.split('|'); if (strengths.length) for (const s of strengths) labels.push([name, s]); else labels.push([name, '']); }
  for (const [name, strength] of labels) {
    for (const q of formats(name, strength)) {
      tested++;
      env.q = q;
      const items = vm.runInContext('answerFor(q, [], [], index).map(i => ({state: i.state, base: i.e && i.e.base, matched: i.e && i.e.matched}))', env);
      const states = items.map(i => i.state);
      const ok = !states.includes('notfound') && !states.includes('unchecked') && items.some(i => i.state === 'registered' && i.base !== undefined && i.base.toLowerCase().normalize('NFD') === name.toLowerCase().normalize('NFD') && (!strength || canon(i.matched || '') === canon(strength)));
      if (!ok) bad.push(`${JSON.stringify(q)} -> ${states.join(',')}`);
    }
  }
  console.log(`names.json: ${labels.length} name+strength labels, ${tested} strings tested, ${bad.length} failures`);
  assert.deepEqual(bad.slice(0, 20), [], `${bad.length} of ${tested} strings did not resolve to themselves`);
});

test('every package on the shortage list shows its shortage card when searched by its own name + strength, in three formats', {skip: !have && 'site/current.json is not built'}, () => {
  const env = load();
  const rows = JSON.parse(read('current.json')).events.filter(e => !e.removed_on);
  env.rows = rows; env.index = JSON.parse(read('names.json'));
  const bad = [];
  let tested = 0;
  for (const e of rows) {
    for (const q of formats(e.name, e.strength || '')) {
      tested++;
      env.q = q;
      const items = vm.runInContext('answerFor(q, rows, [], index).map(i => ({state: i.state, vnr: i.e && i.e.NordicArticleNumber, base: i.e && i.e.base}))', env);
      const shortage = items.some(i => i.state === 'shortage' && i.vnr === e.NordicArticleNumber);
      // The same label never also reads as "not on the list" (a register card for this name) or as unknown.
      const wrong = items.some(i => i.state === 'notfound' || i.state === 'unchecked' || i.state === 'suggest' || (i.state === 'registered' && i.base && i.base.toLowerCase() === e.name.toLowerCase()));
      if (!shortage || wrong) bad.push(`${JSON.stringify(q)} (${e.NordicArticleNumber}) -> ${items.map(i => i.state).join(',')}`);
    }
  }
  console.log(`current.json: ${rows.length} packages, ${tested} strings tested, ${bad.length} failures`);
  assert.deepEqual(bad.slice(0, 20), [], `${bad.length} of ${tested} strings did not show their shortage card`);
});
