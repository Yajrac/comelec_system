const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');

function setup(confirmed) {
  const listeners = {}; let prints = 0; let actions = 0;
  const window = { confirm: () => confirmed, print: () => prints++, showReview: () => actions++ };
  vm.runInNewContext(fs.readFileSync('static/js/template-actions.js', 'utf8'), {
    document: { addEventListener: (name, callback) => listeners[name] = callback }, window,
  });
  return { window, listeners, prints: () => prints, actions: () => actions };
}
function click(dataset) {
  return { defaultPrevented: false, target: { closest: () => ({ dataset }) },
    preventDefault() { this.defaultPrevented = true; } };
}
test('cancelled confirmation blocks click and submit actions', () => {
  const page = setup(false);
  const event = click({ confirmClick: 'Approve?' }); page.listeners.click(event);
  assert.equal(event.defaultPrevented, true);
  const submit = { defaultPrevented: false, target: { dataset: { confirmSubmit: 'Delete?' } }, preventDefault() { this.defaultPrevented = true; } };
  page.listeners.submit(submit); assert.equal(submit.defaultPrevented, true);
});
test('print and review actions work after moving event handlers out of HTML', () => {
  const page = setup(true);
  page.listeners.click(click({ clickAction: 'print' }));
  page.listeners.click(click({ clickAction: 'showReview' }));
  page.listeners.click(click({ clickAction: 'unapprovedFunction' }));
  assert.equal(page.prints(), 1); assert.equal(page.actions(), 1);
});


test('admin modal approval replays the action once and cancellation does not submit', async () => {
  const page = setup(false);
  let prompts = 0; let clicks = 0; let accepted = false;
  page.window.confirmAdminAction = async () => { prompts++; return accepted; };
  const target = { dataset: { confirmClick: 'Approve?' }, isConnected: true,
    click() { clicks++; page.listeners.click(event()); } };
  function event() { return { defaultPrevented: false, target: { closest: () => target },
    preventDefault() { this.defaultPrevented = true; } }; }
  page.listeners.click(event()); await Promise.resolve();
  assert.equal(clicks, 0);
  accepted = true;
  page.listeners.click(event()); await Promise.resolve();
  assert.equal(clicks, 1);
  assert.equal(prompts, 2);
});

test('admin modal preserves submit validation and original submitter', async () => {
  const page = setup(false);
  let prompts = 0; let submissions = 0;
  page.window.confirmAdminAction = async () => { prompts++; return true; };
  const submitter = {};
  const form = { dataset: { confirmSubmit: 'Delete?' }, isConnected: true,
    requestSubmit(button) { assert.equal(button, submitter); submissions++; page.listeners.submit(event()); } };
  function event() { return { defaultPrevented: false, target: form, submitter,
    preventDefault() { this.defaultPrevented = true; } }; }
  page.listeners.submit(event()); await Promise.resolve();
  assert.equal(submissions, 1);
  assert.equal(prompts, 1);
});
