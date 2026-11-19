/* "Registration already exists" / "pending - possible duplicate" modals.
 * Server-rendered dialogs (data-auto-open) open on load; scripts call window.showDuplicateDialog(). */
(() => {
  if (window.showDuplicateDialog) return;

  function el(tag, attrs = {}, text) {
    const node = document.createElement(tag);
    Object.entries(attrs).forEach(([k, v]) => node.setAttribute(k, v));
    if (text) node.textContent = text;
    return node;
  }

  function wire(dialog) {
    dialog.removeAttribute('open');
    dialog.querySelectorAll('form[method="dialog"]').forEach(form => form.addEventListener('submit', event => {
      event.preventDefault();
      dialog.close();
    }));
    dialog.addEventListener('close', () => { if (dialog.dataset.removeOnClose) dialog.remove(); });
    dialog.showModal();
    dialog.querySelector('h2')?.focus({ preventScroll: true });
  }

  const ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><circle cx="12" cy="7.5" r=".9" fill="currentColor" stroke="none"/></svg>';

  /** mode "exists": online duplicate (not saved). mode "pending": offline duplicate saved for review. */
  window.showDuplicateDialog = ({ mode = 'exists', references = [] } = {}) => {
    const dialog = el('dialog', { class: 'pending-correction-dialog duplicate-registration-dialog',
      'aria-labelledby': 'duplicateDialogTitle', 'aria-describedby': 'duplicateDialogMessage' });
    dialog.dataset.removeOnClose = '1';
    const icon = el('div', { class: 'pending-correction-icon', 'aria-hidden': 'true' });
    icon.innerHTML = ICON;
    const actions = el('div', { class: 'duplicate-dialog-actions' });
    const back = el('form', { method: 'dialog' });
    back.append(el('button', { type: 'submit' }, 'Back'));
    if (mode === 'pending') {
      dialog.append(icon, el('h2', { id: 'duplicateDialogTitle', tabindex: '-1' }, 'Registration pending – possible duplicate'),
        el('p', { id: 'duplicateDialogMessage' }, 'Your registration was received, but it has the same name and birthdate as an existing record. The office will review it and send you an SMS.'));
      if (references.length) {
        const list = el('ul', { class: 'duplicate-dialog-references' });
        references.forEach(reference => {
          const item = el('li');
          item.append(el('span', {}, 'Reference number'), el('strong', {}, reference));
          list.append(item);
        });
        dialog.append(list);
      }
      actions.append(el('a', { class: 'duplicate-dialog-primary', href: '/check-status/' }, 'Check my status'), back);
    } else {
      dialog.append(icon, el('h2', { id: 'duplicateDialogTitle', tabindex: '-1' }, 'Registration already exists'),
        el('p', { id: 'duplicateDialogMessage' }, "A registration with this name and birthdate already exists. If this is you, you don't need to register again."));
      actions.append(el('a', { class: 'duplicate-dialog-primary', href: '/check-status/' }, 'Check my status'),
        el('a', { href: '/#applicationHelp' }, 'Choose another service'), back);
    }
    dialog.append(actions);
    document.body.append(dialog);
    wire(dialog);
    return new Promise(resolve => dialog.addEventListener('close', resolve, { once: true }));
  };

  document.querySelectorAll('dialog[data-auto-open]').forEach(wire);
})();
