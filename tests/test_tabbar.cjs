const {test} = require('node:test');
const assert = require('node:assert/strict');
const {slideSteps} = require('../site/tabbar.js');
const NOW = 1_000_000;
const ok = {from: 1, at: NOW - 300};

test('slides from the old tab to the new one after a tap', () => {
  assert.equal(slideSteps(ok, 3, 'navigate', NOW, false, 5), -2);
  assert.equal(slideSteps({from: 4, at: NOW}, 0, 'navigate', NOW, false, 5), 4);
});
test('no slide without a stored tab, on the same tab, or with bad values', () => {
  assert.equal(slideSteps(null, 3, 'navigate', NOW, false, 5), 0);
  assert.equal(slideSteps({from: 3, at: NOW}, 3, 'navigate', NOW, false, 5), 0);
  assert.equal(slideSteps({from: 9, at: NOW}, 3, 'navigate', NOW, false, 5), 0);
  assert.equal(slideSteps({from: '1', at: NOW}, 3, 'navigate', NOW, false, 5), 0);
  assert.equal(slideSteps(ok, -1, 'navigate', NOW, false, 5), 0);
});
test('stale or future values are ignored', () => {
  assert.equal(slideSteps({from: 1, at: NOW - 6000}, 3, 'navigate', NOW, false, 5), 0);
  assert.equal(slideSteps({from: 1, at: NOW + 10}, 3, 'navigate', NOW, false, 5), 0);
});
test('reload, back and forward never slide; reduced motion never slides', () => {
  for (const t of ['reload', 'back_forward', 'prerender', undefined]) assert.equal(slideSteps(ok, 3, t, NOW, false, 5), 0);
  assert.equal(slideSteps(ok, 3, 'navigate', NOW, true, 5), 0);
});
