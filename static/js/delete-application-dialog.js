/* Typed confirmation before permanently deleting an application. */
(() => {
  const dialog = document.getElementById('deleteApplicationDialog');
  if (!dialog) return;
  const summary = document.getElementById('deleteApplicationSummary');
  const effects = document.getElementById('deleteApplicationEffects');
  const input = document.getElementById('deleteApplicationConfirm');
  const submit = document.getElementById('deleteApplicationSubmit');
  const cancel = document.getElementById('deleteApplicationCancel');
  const WORD = 'DELETE';
  let activeForm = null;
  let returnFocus = null;

  const WHOLE_APPLICANT = [
    'The applicant and their whole registration record',
    'All of their other applications and requests',
    'Fingerprints, signatures and previous biometrics',
    'Acknowledgment receipts and uploaded documents and photos',
  ];
  const ONE_REQUEST = [
    'This request and its uploaded document',
    'Its entry in the application history',
    'Changes already applied to the applicant record stay as they are',
  ];

  function open(form) {
    activeForm = form;
    returnFocus = document.activeElement;
    const { applicant, typeLabel, status, wholeApplicant } = form.dataset;
    summary.textContent = `${typeLabel} of ${applicant} (${status}).`;
    effects.replaceChildren(...(wholeApplicant === 'true' ? WHOLE_APPLICANT : ONE_REQUEST).map(text => {
      const li = document.createElement('li');
      li.textContent = (wholeApplicant === 'true' ? 'Deletes: ' : '') + text;
      return li;
    }));
    input.value = '';
    submit.disabled = true;
    dialog.showModal();
    input.focus();
  }

  function close() {
    dialog.close();
    activeForm = null;
    if (returnFocus?.isConnected) returnFocus.focus({ preventScroll: true });
  }

  input.addEventListener('input', () => {
    submit.disabled = input.value.trim() !== WORD;
  });
  input.addEventListener('keydown', event => {
    if (event.key === 'Enter') {
      event.preventDefault();
      if (!submit.disabled) submit.click();
    }
  });
  submit.addEventListener('click', () => {
    if (!activeForm || input.value.trim() !== WORD) return;
    const form = activeForm;
    form.elements.confirm_text.value = WORD;
    submit.disabled = true;
    submit.textContent = 'Deleting…';
    form.submit();
  });
  cancel.addEventListener('click', close);
  dialog.addEventListener('cancel', event => { event.preventDefault(); close(); });

  // Forms are re-rendered by the live search, so listen on the document.
  document.addEventListener('submit', event => {
    const form = event.target.closest('form[data-delete-application]');
    if (!form || form.elements.confirm_text.value === WORD) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    open(form);
  }, true);
})();
