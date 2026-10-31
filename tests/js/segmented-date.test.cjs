const test = require('node:test');
const assert = require('node:assert/strict');
const { makeDate, daysInMonth } = require('../../static/js/segmented-date.js');
test('birthdate serializes to the existing ISO format', () => {
  assert.equal(makeDate('2000', '1', '2'), '2000-01-02');
  assert.equal(makeDate('1998', '12', '31'), '1998-12-31');
});
test('calendar rejects rollover dates and handles leap centuries', () => {
  assert.equal(makeDate('2000', '2', '29'), '2000-02-29');
  assert.equal(makeDate('1900', '2', '29'), '');
  assert.equal(makeDate('2001', '2', '29'), '');
  assert.equal(makeDate('2000', '4', '31'), '');
  assert.equal(daysInMonth(2024, 2), 29);
});
test('incomplete dates are not saved as a partial birthdate', () => {
  assert.equal(makeDate('', '1', '2'), '');
  assert.equal(makeDate('2000', '', '2'), '');
  assert.equal(makeDate('2000', '1', ''), '');
});
