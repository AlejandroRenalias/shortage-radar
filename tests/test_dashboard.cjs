const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('site/app.js', 'utf8').split('function card(')[0];
const context = vm.createContext({Intl, Date});
vm.runInContext(source, context);

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
});
