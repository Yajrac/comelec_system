document.addEventListener('click', (event) => {
  document.querySelectorAll('details[open]').forEach((menu) => {
    if (!menu.contains(event.target)) menu.open = false;
  });
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') document.querySelectorAll('details[open]').forEach((menu) => {
    menu.open = false;
    menu.querySelector('summary').focus();
  });
});

// Filters submit immediately; typed search text is applied with Search or Enter.
document.querySelectorAll('[data-auto-filter]').forEach((filter) => {
  filter.addEventListener('change', () => {
    filter.form.requestSubmit();
  });
});

document.querySelectorAll('[data-refresh-records]').forEach((button) => {
  const panel = button.closest('.records-panel');
  const status = document.createElement('p');
  status.className = 'records-refresh-status';
  status.setAttribute('role', 'status');
  status.setAttribute('aria-live', 'polite');
  button.closest('.panel-heading').after(status);

  button.addEventListener('click', async () => {
    if (button.disabled) return;
    button.disabled = true;
    button.setAttribute('aria-busy', 'true');
    panel.querySelector('.table-scroll').setAttribute('aria-busy', 'true');
    button.querySelector('span').textContent = 'Refreshing...';
    status.textContent = '';
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(window.location.href, {
        cache: 'no-store',
        credentials: 'same-origin',
        signal: controller.signal,
      });
      if (!response.ok || response.redirected) throw new Error('Refresh failed');
      const page = new DOMParser().parseFromString(await response.text(), 'text/html');
      const freshPanel = page.querySelector('.records-panel');
      const selectors = ['.table-scroll', '.table-footer', '#records-heading .count'];
      const replacements = selectors.map((selector) => ({
        current: panel.querySelector(selector),
        fresh: freshPanel?.querySelector(selector),
      }));
      if (replacements.some(({ current, fresh }) => !current || !fresh)) {
        throw new Error('Missing records content');
      }
      const scrollLeft = panel.querySelector('.table-scroll').scrollLeft;
      replacements.forEach(({ current, fresh }) => current.replaceWith(fresh));
      panel.querySelector('.table-scroll').scrollLeft = scrollLeft;
      status.textContent = 'Records updated.';
      status.classList.remove('refresh-error');
    } catch (error) {
      status.textContent = 'Unable to refresh records. Please try again.';
      status.classList.add('refresh-error');
    } finally {
      clearTimeout(timeout);
      button.disabled = false;
      button.removeAttribute('aria-busy');
      panel.querySelector('.table-scroll').removeAttribute('aria-busy');
      button.querySelector('span').textContent = 'Refresh';
    }
  });
});
