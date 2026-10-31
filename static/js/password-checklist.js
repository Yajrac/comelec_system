(() => {
  const showPasswords = document.getElementById('showChangePasswords');
  const passwordFields = ['id_old_password', 'id_new_password1', 'id_new_password2']
    .map(id => document.getElementById(id)).filter(Boolean);
  if (showPasswords) {
    showPasswords.addEventListener('change', () => {
      passwordFields.forEach(field => { field.type = showPasswords.checked ? 'text' : 'password'; });
    });
    window.addEventListener('pageshow', () => {
      showPasswords.checked = false;
      passwordFields.forEach(field => { field.type = 'password'; });
    });
  }
  const checklist = document.getElementById('passwordChecklist');
  const input = document.getElementById('id_new_password1');
  if (!checklist || !input) return;
  const rules = [...checklist.querySelectorAll('[data-password-rule]')];
  const status = document.getElementById('passwordCheckStatus');
  let timer;
  let controller;
  let generation = 0;
  function updateRule(rule, passed) {
    if (rule.classList.contains('passed') === passed) return;
    rule.classList.toggle('passed', passed);
    rule.querySelector('.password-rule-icon').textContent = '\u2713';
    rule.querySelector('.password-rule-state').textContent = passed ? 'Met' : 'Not met';
  }
  input.addEventListener('input', () => {
    clearTimeout(timer);
    controller?.abort();
    const current = ++generation;
    if (!input.value) {
      rules.forEach(rule => updateRule(rule, false));
      input.classList.remove('password-rules-met');
      status.textContent = '';
      return;
    }
    status.textContent = '';
    timer = setTimeout(async () => {
      controller = new AbortController();
      try {
        const response = await fetch(checklist.dataset.checkUrl, {
          method: 'POST', credentials: 'same-origin', cache: 'no-store', signal: controller.signal,
          headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRFToken': input.form.elements.csrfmiddlewaretoken.value },
          body: new URLSearchParams({ password: input.value }),
        });
        if (!response.ok || response.redirected) throw new Error('Check failed');
        const data = await response.json();
        if (current !== generation) return;
        if (!Array.isArray(data.checks) || data.checks.length !== rules.length) throw new Error('Invalid checks');
        rules.forEach((rule, index) => updateRule(rule, data.checks[index] === true));
        input.classList.toggle('password-rules-met', data.checks.every(Boolean));
        status.textContent = data.checks.every(Boolean) ? 'All password requirements met.' : 'Complete the remaining password requirements.';
      } catch (error) {
        if (error.name !== 'AbortError' && current === generation) status.textContent = 'Live check unavailable. Requirements will be checked when you save.';
      }
    }, 200);
  });
})();
