(() => {
  window.setApplicationSubmitting = button => {
    if (!button.dataset.idleHtml) button.dataset.idleHtml = button.innerHTML;
    button.disabled = true;
    button.setAttribute('aria-busy', 'true');
    const spinner = document.createElement('span');
    spinner.className = 'application-submit-spinner';
    spinner.setAttribute('aria-hidden', 'true');
    button.replaceChildren(spinner, document.createTextNode(' Submitting...'));
    document.querySelectorAll('.application-cancel').forEach(link => {
      link.setAttribute('aria-disabled', 'true');
    });
  };
  document.addEventListener('click', event => {
    if (event.target.closest('.application-cancel[aria-disabled="true"]')) event.preventDefault();
  });
  window.addEventListener('pageshow', () => {
    document.querySelectorAll('button[data-idle-html]').forEach(button => {
      button.innerHTML = button.dataset.idleHtml;
      button.disabled = false; button.removeAttribute('aria-busy');
    });
    document.querySelectorAll('.application-cancel').forEach(link => link.removeAttribute('aria-disabled'));
  });
})();
