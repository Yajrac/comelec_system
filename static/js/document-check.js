/* AI check of the uploaded valid ID / birth certificate before submitting.
 * Forms opt in with data-document-check="NEW|UPDATE|TRANSFER|REACTIVATION|REINSTATEMENT".
 * The server checks again on submit; this script only gives the applicant the result first. */
(() => {
  if (window.documentCheck) return; // loaded by both the page and the base template
  // Feature off: no checks anywhere (forms are not marked and offline sync uploads directly).
  if (!document.querySelector('form[data-document-check]') && document.body?.dataset.documentAi !== '1') return;
  const URL = '/document-check/';
  const PASS = new Set(['passed', 'unavailable', 'disabled', 'override']);
  const results = new WeakMap(); // form -> {key, result}
  let dialog, busy = false;

  // ---------------------------------------------------------------- dialog
  function el(tag, attrs = {}, text) {
    const node = document.createElement(tag);
    Object.entries(attrs).forEach(([k, v]) => node.setAttribute(k, v));
    if (text) node.textContent = text;
    return node;
  }

  function ensureDialog() {
    if (dialog) return dialog;
    dialog = el('dialog', { class: 'doc-check-dialog', 'aria-labelledby': 'docCheckTitle', 'aria-describedby': 'docCheckMessage' });
    dialog.append(
      el('div', { class: 'doc-check-icon', 'aria-hidden': 'true' }),
      el('h2', { id: 'docCheckTitle', tabindex: '-1' }),
      el('p', { id: 'docCheckMessage', class: 'doc-check-message' }),
      el('dl', { class: 'doc-check-details' }),
      el('p', { class: 'doc-check-note' }),
      el('div', { class: 'doc-check-buttons' }),
    );
    dialog.addEventListener('cancel', event => event.preventDefault()); // choose a button
    document.body.append(dialog);
    return dialog;
  }

  function render(state, { title, message = '', details = [], note = '', buttons = [] }) {
    const box = ensureDialog();
    box.dataset.state = state;
    box.querySelector('.doc-check-icon').textContent = { checking: '', passed: '✓', invalid: '✕', mismatch: '!', unavailable: 'i' }[state] || '';
    box.querySelector('h2').textContent = title;
    box.querySelector('.doc-check-message').textContent = message;
    const list = box.querySelector('dl');
    list.replaceChildren(...details.flatMap(([term, value]) => [el('dt', {}, term), el('dd', {}, value || '—')]));
    list.hidden = !details.length;
    const noteEl = box.querySelector('.doc-check-note');
    noteEl.textContent = note; noteEl.hidden = !note;
    const row = box.querySelector('.doc-check-buttons');
    row.replaceChildren();
    if (!box.open) box.showModal();
    box.querySelector('h2').focus({ preventScroll: true });
    if (!buttons.length) return Promise.resolve(null);
    return new Promise(resolve => {
      buttons.forEach(([label, value, primary]) => {
        const button = el('button', { type: 'button', class: primary ? 'doc-check-primary' : '' }, label);
        button.addEventListener('click', () => { box.close(); resolve(value); });
        row.append(button);
      });
      row.querySelector('.doc-check-primary, button')?.focus();
    });
  }

  function showChecking(text = 'Checking your document…') {
    render('checking', { title: text, message: 'This takes a few seconds. Please keep this page open.' });
  }

  function closeDialog() { if (dialog?.open) dialog.close(); }

  function detailsFor(result) {
    const rows = [];
    if (result.document_type) rows.push(['Document', result.document_type]);
    if (result.status === 'passed' && result.document_name) rows.push(['Name on the document', result.document_name]);
    return rows;
  }

  // Online form result. Resolves to the chosen action.
  function showResult(result, { canEdit }) {
    if (result.status === 'passed') {
      return render('passed', { title: 'This document is valid and matches your details.', details: detailsFor(result),
        buttons: [['Back', 'back'], ['Continue', 'continue', true]] });
    }
    if (result.status === 'unavailable') {
      return render('unavailable', { title: 'Document check is unavailable right now.',
        message: 'You can continue. The office will review your document.', buttons: [['Continue', 'continue', true]] });
    }
    const buttons = [['Upload another file', 'upload', true], ['Retake photo', 'retake']];
    if (result.status === 'mismatch' && canEdit) buttons.push(['Edit details', 'edit']);
    return render(result.status, {
      title: result.status === 'mismatch' ? 'This document is valid, but your name does not match.' : 'This document is not valid.',
      message: result.status === 'invalid' ? result.reason : 'Make sure the document belongs to you and your name is typed exactly as it appears.',
      details: detailsFor(result), buttons,
    });
  }

  // ---------------------------------------------------------------- requests
  async function requestCheck(file, fields) {
    const body = new FormData();
    body.append('valid_id_document', file);
    Object.entries(fields).forEach(([k, v]) => { if (v) body.append(k, v); });
    let response;
    try {
      response = await fetch(URL, { method: 'POST', body, credentials: 'same-origin', signal: AbortSignal.timeout(60000) });
    } catch {
      return { status: 'offline' };
    }
    let data = null;
    try { data = await response.json(); } catch { /* not JSON */ }
    if (!data) return { status: response.ok ? 'unavailable' : 'offline' };
    return data;
  }

  function formFields(form) {
    const value = name => form.elements.namedItem(name)?.value?.trim() || '';
    const fields = { application_type: form.dataset.documentCheck };
    if (form.elements.namedItem('lastname')) {
      Object.assign(fields, { lastname: value('lastname'), firstname: value('firstname'), middlename: value('middlename') });
    } else {
      fields.applicant_id = value('applicant_id');
    }
    return fields;
  }

  function stateKey(file, fields) {
    return [file.name, file.size, file.lastModified, fields.lastname, fields.firstname, fields.middlename, fields.applicant_id].join('|');
  }

  function fileInput(form) { return form.elements.namedItem('valid_id_document'); }

  function retake(input) {
    if (window.documentCamera) { window.documentCamera.open(input); return; }
    const camera = el('input', { type: 'file', accept: 'image/*', capture: 'environment', hidden: '' });
    camera.addEventListener('change', () => {
      if (camera.files.length) {
        const transfer = new DataTransfer();
        transfer.items.add(camera.files[0]);
        input.files = transfer.files;
        input.dispatchEvent(new Event('change', { bubbles: true }));
      }
      camera.remove();
    });
    document.body.append(camera);
    camera.click();
  }

  // ---------------------------------------------------------------- inline result under the upload
  function inlineBox(form) {
    let box = form.querySelector('.doc-check-inline');
    if (!box) {
      box = el('div', { class: 'doc-check-inline', role: 'status', 'aria-live': 'polite', hidden: '' });
      (form.querySelector('.doc-camera-row') || fileInput(form)).insertAdjacentElement('afterend', box);
    }
    return box;
  }

  function showInline(form, state, text, actions = []) {
    const box = inlineBox(form);
    box.dataset.state = state;
    box.replaceChildren(el('span', { class: 'doc-check-inline-icon', 'aria-hidden': 'true' },
      { checking: '', passed: '✓', valid: '✓', invalid: '✕', mismatch: '!', unavailable: 'i', offline: 'i' }[state] || ''),
      el('span', { class: 'doc-check-inline-text' }, text));
    if (actions.length) {
      const row = el('div', { class: 'doc-check-inline-actions' });
      actions.forEach(([label, handler]) => {
        const button = el('button', { type: 'button' }, label);
        button.addEventListener('click', handler);
        row.append(button);
      });
      box.append(row);
    }
    box.hidden = false;
  }

  function fixActions(form, result) {
    const input = fileInput(form);
    const actions = [['Upload another file', () => { input.value = ''; input.click(); }],
                     ['Retake photo', () => retake(input)]];
    if (result.status === 'mismatch' && form.elements.namedItem('lastname')) {
      actions.push(['Edit details', () => { window.backToForm?.(); form.elements.namedItem('lastname').focus(); }]);
    }
    return actions;
  }

  function renderInline(form, result) {
    const type = result.document_type ? ` (${result.document_type})` : '';
    switch (result.status) {
      case 'checking': return showInline(form, 'checking', 'Checking your document…');
      case 'valid': return showInline(form, 'valid', `Valid document${type}. Your name will be matched with the document when you submit.`);
      case 'passed': return showInline(form, 'passed', `Valid document${type}. The name matches${result.document_name ? `: ${result.document_name}` : ''}.`);
      case 'invalid': return showInline(form, 'invalid', `This document is not valid. ${result.reason || ''}`.trim(), fixActions(form, result));
      case 'mismatch': return showInline(form, 'mismatch',
        'This document is valid, but the name on it does not match the name you entered.', fixActions(form, result));
      case 'unavailable': return showInline(form, 'unavailable', 'Document check is unavailable right now. The office will review your document.');
      case 'offline': return showInline(form, 'offline', 'You are offline. The document will be checked before it is uploaded.');
      case 'error': return showInline(form, 'invalid', result.message || 'This document could not be checked.', fixActions(form, result));
      default: inlineBox(form).hidden = true;
    }
  }

  const ACCEPTED = new Set(['passed', 'unavailable', 'disabled', 'offline']);

  /** Check on upload (and when the name changes); never blocks, only shows the result. */
  async function inlineCheck(form) {
    const file = fileInput(form)?.files?.[0];
    if (!file) { renderInline(form, {}); results.delete(form); return; }
    const fields = formFields(form);
    const key = stateKey(file, fields);
    if (results.get(form)?.key === key) return;
    results.set(form, { key, result: { status: 'checking' } });
    renderInline(form, { status: 'checking' });
    const result = await requestCheck(file, fields);
    if (results.get(form)?.key !== key) return;            // a newer file or name was entered meanwhile
    results.set(form, { key, result, accepted: ACCEPTED.has(result.status) });
    renderInline(form, result);
  }

  /** Before submitting: compares the typed name (the document itself was read on upload). */
  async function ensure(form) {
    const input = fileInput(form);
    const file = input?.files?.[0];
    if (!file) return true;                                    // reusing a stored document
    if (form.querySelector('[name="officer_verified"]')?.checked) return true;
    const fields = formFields(form);
    const key = stateKey(file, fields);
    const known = results.get(form);
    if (known?.key === key && known.accepted) return true;
    if (busy) return false;
    busy = true;
    try {
      let result = known?.key === key && known.result.status !== 'checking' ? known.result : null;
      if (!result) {
        showChecking('Checking your document…');
        result = await requestCheck(file, fields);
        results.set(form, { key, result, accepted: ACCEPTED.has(result.status) });
        renderInline(form, result);
      }
      // "valid" means no name was compared yet; the server compares it on submit and reports a mismatch.
      if (ACCEPTED.has(result.status) || result.status === 'valid') { closeDialog(); return true; }
      if (result.status === 'error') result = { ...result, status: 'invalid', reason: result.message };
      const action = await showResult(result, { canEdit: Boolean(form.elements.namedItem('lastname')) });
      if (action === 'upload') { input.value = ''; input.click(); }
      if (action === 'retake') retake(input);
      if (action === 'edit') { window.backToForm?.(); form.elements.namedItem('lastname')?.focus(); }
      return false;
    } finally {
      busy = false;
    }
  }

  // ---------------------------------------------------------------- offline sync
  function entriesValue(entries, name) {
    return entries.find(([key]) => key === name)?.[1];
  }

  /** Review one queued registration before upload: 'upload' | 'later' | {fix: message} | throws when offline. */
  async function reviewQueued(entries, position = '') {
    const file = entriesValue(entries, 'valid_id_document');
    if (!(file instanceof Blob)) return 'upload';
    const fields = { application_type: 'NEW', lastname: entriesValue(entries, 'lastname'),
      firstname: entriesValue(entries, 'firstname'), middlename: entriesValue(entries, 'middlename') };
    showChecking(`Checking document before upload${position}…`);
    const result = await requestCheck(file instanceof File ? file : new File([file], 'document'), fields);
    if (result.status === 'offline') { closeDialog(); throw new Error('offline'); }
    if (result.status === 'disabled' || result.status === 'unavailable') { closeDialog(); return 'upload'; }
    if (result.status === 'passed') {
      const name = [entriesValue(entries, 'firstname'), entriesValue(entries, 'lastname')].filter(Boolean).join(' ');
      return render('passed', { title: 'This document is valid and matches your details.',
        message: name ? `Saved registration of ${name}.` : '', details: detailsFor(result),
        buttons: [['Later', 'later'], ['Upload now', 'upload', true]] });
    }
    const message = result.status === 'mismatch'
      ? 'This document is valid, but the name on it does not match the name you entered.'
      : `This document is not valid. ${result.reason || result.message || ''}`.trim();
    await render(result.status === 'mismatch' ? 'mismatch' : 'invalid', {
      title: result.status === 'mismatch' ? 'This document is valid, but your name does not match.' : 'This document is not valid.',
      message: 'This saved registration was not uploaded. Open it from Saved applications to replace the file or correct the name.',
      details: detailsFor(result), buttons: [['OK', 'ok', true]] });
    return { fix: message };
  }

  // ---------------------------------------------------------------- wiring
  function addFormExtras(form) {
    const input = fileInput(form);
    if (!input || input.dataset.documentCheckReady) return;
    input.dataset.documentCheckReady = '1';
    if (form.dataset.walkIn === '1') {
      const label = el('label', { class: 'doc-check-override' });
      const box = el('input', { type: 'checkbox', name: 'officer_verified', value: '1' });
      label.append(box, document.createTextNode(' Manually verified by officer (skip the AI result for this document)'));
      input.insertAdjacentElement('afterend', label);
    }
    input.addEventListener('change', () => setTimeout(() => inlineCheck(form), 0));
    ['lastname', 'firstname', 'middlename'].forEach(name => {
      form.elements.namedItem(name)?.addEventListener('change', () => {
        if (input.files?.length) inlineCheck(form);
      });
    });
  }

  document.querySelectorAll('form[data-document-check]').forEach(addFormExtras);

  // Service forms submit natively: check first, then submit again once accepted.
  document.addEventListener('submit', event => {
    const form = event.target.closest('form[data-document-check]');
    if (!form || form.dataset.documentCheck === 'NEW' || !form.checkValidity()) return;
    if (form.querySelector('[name="officer_verified"]')?.checked) return;
    const file = fileInput(form)?.files?.[0];
    const fields = file ? formFields(form) : null;
    if (!file || results.get(form)?.key === stateKey(file, fields) && results.get(form).accepted) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    const submitter = event.submitter;
    ensure(form).then(ok => { if (ok) form.requestSubmit(submitter || undefined); });
  }, true);

  window.documentCheck = { ensure, reviewQueued };
})();
