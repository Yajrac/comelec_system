const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function element() {
  const classes = new Set();
  return { value: '', type: 'password', listeners: {}, textContent: '',
    classList: { contains: name => classes.has(name), remove: name => classes.delete(name),
      toggle(name, enabled) { enabled ? classes.add(name) : classes.delete(name); } },
    addEventListener(name, callback) { this.listeners[name] = callback; } };
}

test('typing updates checks, preserves existing checks during input, and clears on empty', async () => {
  const input = element();
  input.form = { elements: { csrfmiddlewaretoken: { value: 'test-csrf' } } };
  const rules = Array.from({length: 4}, () => {
    const rule = element(); const children = {};
    rule.querySelector = key => children[key] ||= element();
    return rule;
  });
  const checklist = { dataset: { checkUrl: '/requirements/' }, querySelectorAll: () => rules };
  const status = element(); const show = element();
  const elements = { passwordChecklist: checklist, id_new_password1: input, passwordCheckStatus: status,
    showChangePasswords: show, id_old_password: element(), id_new_password2: element() };
  let scheduled; let checks = [true, false, true, false]; let calls = 0;
  vm.runInNewContext(fs.readFileSync('static/js/password-checklist.js', 'utf8'), {
    document: { getElementById: id => elements[id] }, window: { addEventListener() {} },
    AbortController, URLSearchParams, clearTimeout() {}, setTimeout(callback) { scheduled = callback; return 1; },
    fetch: async () => { calls++; return { ok: true, redirected: false, json: async () => ({ checks }) }; }
  });
  input.value = 'Example'; input.listeners.input(); await scheduled();
  assert.equal(calls, 1);
  assert.equal(rules[0].classList.contains('passed'), true);
  assert.equal(rules[1].classList.contains('passed'), false);
  input.value = 'Example-8!'; input.listeners.input();
  assert.equal(rules[0].classList.contains('passed'), true);
  checks = [true, true, true, true]; await scheduled();
  assert.equal(input.classList.contains('password-rules-met'), true);
  assert.equal(status.textContent, 'All password requirements met.');
  show.checked = true; show.listeners.change(); assert.equal(input.type, 'text');
  input.value = ''; input.listeners.input();
  assert.equal(rules.some(rule => rule.classList.contains('passed')), false);
  assert.equal(input.classList.contains('password-rules-met'), false);
});
