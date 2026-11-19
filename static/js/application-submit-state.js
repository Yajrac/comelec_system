(() => {
  window.setApplicationSubmitting = (button, label = 'Submitting...') => {
    if (!button.dataset.idleHtml) button.dataset.idleHtml = button.innerHTML;
    button.disabled = true;
    button.setAttribute('aria-busy', 'true');
    const spinner = document.createElement('span');
    spinner.className = 'application-submit-spinner';
    spinner.setAttribute('aria-hidden', 'true');
    button.replaceChildren(spinner, document.createTextNode(' ' + label));
    document.querySelectorAll('.application-cancel').forEach(link => {
      link.setAttribute('aria-disabled', 'true');
    });
  };
  window.resetApplicationButton = button => {
    if (button.dataset.idleHtml) button.innerHTML = button.dataset.idleHtml;
    button.disabled = false;
    button.removeAttribute('aria-busy');
    document.querySelectorAll('.application-cancel').forEach(link => link.removeAttribute('aria-disabled'));
  };
  document.addEventListener('click', event => {
    if (event.target.closest('.application-cancel[aria-disabled="true"]')) event.preventDefault();
  });
  window.addEventListener('pageshow', event => {
    // Back from the success page: the form that was submitted comes back empty.
    if (event.persisted) {
      document.querySelectorAll('button[aria-busy="true"]').forEach(button => {
        const form = button.form || button.closest('form') || document.querySelector('form[data-document-check]');
        if (!form) return;
        form.reset();
        form.dispatchEvent(new Event('offline:submitted'));
        window.backToForm?.();
      });
    }
    document.querySelectorAll('button[data-idle-html]').forEach(button => {
      button.innerHTML = button.dataset.idleHtml;
      button.disabled = false; button.removeAttribute('aria-busy');
    });
    document.querySelectorAll('.application-cancel').forEach(link => link.removeAttribute('aria-disabled'));
  });
})();
