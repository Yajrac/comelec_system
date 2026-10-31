/* Shared form checks for the web UI and React mobile screens. */
(() => {
  const names = new Set(['firstname', 'lastname', 'middlename', 'father', 'mother']);
  const namePattern = /^[\p{L}\p{M} .\u2019'\-]+$/u;
  const fields = 'input:not([type="hidden"]):not([type="button"]):not([type="submit"]), select, textarea';
  function messageFor(input) {
    if (input.disabled || input.readOnly || input.type === 'checkbox' || input.type === 'radio') return '';
    const key = input.name;
    const value = input.value.trim();
    if (key === 'middlename' && !value) return '';
    if (input.required && !value) return 'This field is required.';
    if (!value) return '';
    if (names.has(key) && (value.length > 255 || !namePattern.test(value) || !/\p{L}/u.test(value))) return 'Use letters, spaces, hyphens, apostrophes, or periods only (maximum 255 characters).';
    if (key === 'phone' && !/^09[0-9]{9}$/.test(value)) return 'Enter 11 digits starting with 09.';
    if (key === 'email' && (input.validity.typeMismatch || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) || value.length > 254)) return 'Enter a valid email address.';
    if (key === 'age' && (!/^[0-9]{1,3}$/.test(value) || Number(value) < 1 || Number(value) > 150)) return 'Enter a whole-number age between 1 and 150.';
    if (key === 'age') {
      const scope = input.closest('form') || document;
      const birthdate = scope.querySelector('[name="birthdate"]')?.value;
      if (birthdate) {
        const born = new Date(birthdate + 'T00:00:00');
        const today = new Date();
        const age = today.getFullYear() - born.getFullYear() - (today.getMonth() < born.getMonth() || (today.getMonth() === born.getMonth() && today.getDate() < born.getDate()) ? 1 : 0);
        if (!Number.isNaN(born.getTime()) && Number(value) !== age) return 'Age must match the date of birth.';
      }
    }

    if (key === 'birthdate') {
      const born = new Date(value + 'T00:00:00');
      const today = new Date(); today.setHours(0, 0, 0, 0);
      if (Number.isNaN(born.getTime()) || born >= today) return 'Enter a valid birthdate earlier than today.';
    }
    if (key === 'registration_reference' && !/^PD-[A-F0-9]{32}$/i.test(value)) return 'Enter PD- followed by exactly 32 characters (0-9 and A-F).';
    if (['birthplace', 'province', 'municipality'].includes(key) && value.length > 255) return 'Use no more than 255 characters.';
    if (key === 'reason' && value.length > 5000) return 'Use no more than 5,000 characters.';
    if (input.type === 'file' && input.files?.length) {
      const file = input.files[0];
      if (file.size > 5 * 1024 * 1024) return 'File must be 5 MB or smaller.';
      if (!/\.(pdf|png|jpe?g)$/i.test(file.name)) return 'Upload a PDF, PNG, or JPEG file.';
    }
    if (input.validity.badInput || input.validity.rangeUnderflow || input.validity.rangeOverflow || input.validity.patternMismatch) return 'Enter a valid value.';
    return '';
  }
  function updateAge(birthdate) {
    const scope = birthdate.closest('form');
    const age = scope?.querySelector('[name="age"]');
    if (!age) return;
    const parts = birthdate.value.split('-').map(Number);
    const born = new Date(parts[0], parts[1] - 1, parts[2]);
    const today = new Date();
    const valid = parts.length === 3 && born.getFullYear() === parts[0] && born.getMonth() === parts[1] - 1 && born.getDate() === parts[2] && born < today;
    age.readOnly = true;
    age.value = valid ? String(today.getFullYear() - born.getFullYear() - (today.getMonth() < born.getMonth() || (today.getMonth() === born.getMonth() && today.getDate() < born.getDate()) ? 1 : 0)) : '';
    const error = age._fieldValidationError;
    if (error) error.textContent = '';
    age.classList.remove('input-invalid');
    age.removeAttribute('aria-invalid');
  }
  document.querySelectorAll('input[name="birthdate"]').forEach(birthdate => {
    updateAge(birthdate);
    birthdate.addEventListener('input', () => updateAge(birthdate));
    birthdate.addEventListener('change', () => updateAge(birthdate));
  });
  let nextId = 0;
  function validate(input) {
    const message = messageFor(input);
    let error = input._fieldValidationError;
    if (message && !error) {
      error = document.createElement('small'); error.className = 'input-validation-error';
      error.id = 'field-validation-' + (++nextId); error.setAttribute('aria-live', 'polite');
      input.insertAdjacentElement('afterend', error); input._fieldValidationError = error;
      input.setAttribute('aria-describedby', [input.getAttribute('aria-describedby'), error.id].filter(Boolean).join(' '));
    }
    if (error) error.textContent = message;
    input.classList.toggle('input-invalid', Boolean(message));
    if (message) input.setAttribute('aria-invalid', 'true'); else input.removeAttribute('aria-invalid');
    return !message;
  }
  function relevant(input) { return names.has(input.name) || ['phone','email','birthdate','age','registration_reference','reason','brgy','new_brgy','birthplace','province','municipality','sex','civil_status','pwd_status','citizenship_status','valid_id_document'].includes(input.name); }
  function visible(input) { return input.getClientRects().length > 0; }
  function validateScope(scope) {
    let first;
    scope.querySelectorAll(fields).forEach(input => {
      if (relevant(input) && visible(input) && !validate(input) && !first) first = input;
    });
    first?.focus();
    return !first;
  }
  document.addEventListener('focusout', event => {
    if (event.target.matches?.(fields) && relevant(event.target)) validate(event.target);
  });
  document.addEventListener('input', event => {
    if (event.target.matches?.(fields) && relevant(event.target) && event.target.getAttribute('aria-invalid') === 'true') validate(event.target);
  });
  document.addEventListener('change', event => {
    if (event.target.matches?.(fields) && relevant(event.target)) validate(event.target);
  });
  document.addEventListener('submit', event => {
    if (!validateScope(event.target)) { event.preventDefault(); event.stopImmediatePropagation(); }
  }, true);
  document.addEventListener('click', event => {
    const button = event.target.closest?.('button');
    if (!button || button.type === 'submit' || !/review|submit application|submit request/i.test(button.textContent)) return;
    if (!validateScope(button.closest('form') || document.querySelector('main') || document.body)) {
      event.preventDefault(); event.stopImmediatePropagation();
    }
  }, true);
})();
