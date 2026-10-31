document.querySelectorAll('form').forEach((form) => {
  if (!form.querySelector('input[name="action"][value="find_applicant"]')) return;
  const button = form.querySelector('button[type="submit"]');
  if (!button) return;
  const reference = form.querySelector('input[name="registration_reference"]');
  const validReference = () => !reference || /^PD-[A-F0-9]{32}$/i.test(reference.value.trim());
  const updateButton = () => { button.disabled = submitting || !validReference(); };
  const original = button.innerHTML;
  const status = document.createElement('span');
  status.className = 'lookup-status';
  status.setAttribute('role', 'status');
  status.setAttribute('aria-live', 'polite');
  form.append(status);
  let submitting = false;
  if (reference && reference.type !== 'hidden') {
    reference.pattern = '[Pp][Dd]-[A-Fa-f0-9]{32}';
    reference.minLength = 35;
    reference.maxLength = 35;
    reference.title = 'Enter PD- followed by exactly 32 hexadecimal characters (0-9 and A-F).';
    reference.addEventListener('input', updateButton);
    reference.addEventListener('change', updateButton);
  }
  updateButton();
  form.addEventListener('submit', (event) => {
    if (event.defaultPrevented) return;
    if (submitting) { event.preventDefault(); return; }
    if (!validReference()) { event.preventDefault(); updateButton(); return; }
    if (!form.reportValidity()) { event.preventDefault(); return; }
    submitting = true;
    button.disabled = true;
    button.setAttribute('aria-busy', 'true');
    button.innerHTML = '<span class="lookup-spinner" aria-hidden="true"></span><span>Finding record...</span>';
    status.textContent = 'Finding your registration record. Please wait.';
  });
  window.addEventListener('pageshow', () => {
    submitting = false;
    updateButton();
    button.removeAttribute('aria-busy');
    button.innerHTML = original;
    status.textContent = '';
  });
});
