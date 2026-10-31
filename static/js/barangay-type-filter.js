(() => {
  const results = document.getElementById('barangayFilteredResults');
  const status = document.getElementById('barangayFilterStatus');
  if (!results) return;
  let controller;
  async function load(url, push, focusTab) {
    controller?.abort();
    const current = new AbortController();
    controller = current;
    results.setAttribute('aria-busy', 'true');
    results.classList.add('is-loading');
    status.textContent = 'Updating applicants...';
    try {
      const response = await fetch(url, { signal: current.signal });
      if (!response.ok) throw new Error('Unable to load applicants');
      const html = new DOMParser().parseFromString(await response.text(), 'text/html');
      const next = html.getElementById('barangayFilteredResults');
      if (!next) throw new Error('Missing results');
      if (current.signal.aborted) return;
      results.replaceChildren(...next.childNodes);
      if (push) history.pushState(null, '', url);
      if (focusTab) results.querySelector('[aria-current="page"]')?.focus({ preventScroll: true });
      if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        results.querySelector('.table-responsive')?.animate([
          { opacity: 0, transform: 'translateY(4px)' },
          { opacity: 1, transform: 'translateY(0)' }
        ], { duration: 200, easing: 'ease-out' });
      }
      status.textContent = 'Applicants updated.';
    } catch (error) {
      if (error.name !== 'AbortError') window.location.assign(url);
    } finally {
      if (controller === current) {
        results.removeAttribute('aria-busy');
        results.classList.remove('is-loading');
        controller = null;
      }
    }
  }
  results.addEventListener('click', event => {
    const link = event.target.closest('.barangay-type-tab');
    if (!link || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    if (link.href === window.location.href && !controller) return;
    load(link.href, true, true);
  });
  window.addEventListener('popstate', () => load(window.location.href, false, false));
})();
