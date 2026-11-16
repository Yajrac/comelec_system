/* Home page: check an application's status by reference number without leaving the page. */
(() => {
  const form = document.getElementById('statusCheckForm');
  if (!form) return;
  const input = document.getElementById('statusReference');
  const button = document.getElementById('statusCheckButton');
  const result = document.getElementById('statusResult');
  const idleLabel = button.textContent;

  function show(text) {
    const box = document.createElement('div');
    box.className = 'status-result is-missing';
    const p = document.createElement('p');
    p.className = 'status-missing';
    p.textContent = text;
    box.append(p);
    result.replaceChildren(box);
  }

  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (!input.value.trim()) { show('Enter your reference number.'); input.focus(); return; }
    if (!navigator.onLine) { show('Checking your status needs an internet connection.'); return; }
    button.disabled = true;
    button.textContent = 'Checking…';
    try {
      const response = await fetch(form.action, {
        method: 'POST', body: new FormData(form), credentials: 'same-origin',
        headers: { 'X-Status-Fragment': '1' }, signal: AbortSignal.timeout(20000),
      });
      const html = await response.text();
      if (!html.trim()) throw new Error('empty');
      result.innerHTML = html; // rendered by Django's template, so values are escaped
    } catch {
      show('Checking your status needs an internet connection. Please try again.');
    } finally {
      button.disabled = false;
      button.textContent = idleLabel;
    }
  });
})();
