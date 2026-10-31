const applicationFilters = document.getElementById('applicationFilters');
if (applicationFilters) {
  const search = applicationFilters.elements.search;
  const filters = [...applicationFilters.querySelectorAll('select, input[type="date"]')];
  const status = document.getElementById('applicationSearchStatus');
  let timeout;
  let controller;
  let sequence = 0;
  let composing = false;
  async function runSearch(options = {}) {
    clearTimeout(timeout);
    if (!applicationFilters.reportValidity()) return;
    const from = applicationFilters.elements.date_from;
    const to = applicationFilters.elements.date_to;
    if (from.value && to.value && from.value > to.value) {
      status.textContent = 'From date must be on or before To date.';
      return;
    }
    controller?.abort();
    controller = new AbortController();
    const current = ++sequence;
    const url = new URL(window.location.href);
    const previousPage = url.searchParams.get('page');
    url.search = new URLSearchParams(new FormData(applicationFilters)).toString();
    if (options.keepPage === true && previousPage) url.searchParams.set('page', previousPage);
    const results = document.getElementById('applicationResults');
    results.setAttribute('aria-busy', 'true');
    status.textContent = 'Searching...';
    try {
      const response = await fetch(url, { signal: controller.signal, cache: 'no-store', credentials: 'same-origin' });
      if (!response.ok || response.redirected) throw new Error('Search failed');
      const page = new DOMParser().parseFromString(await response.text(), 'text/html');
      const fresh = page.getElementById('applicationResults');
      if (!fresh) throw new Error('Missing results');
      if (current !== sequence) return;
      results.replaceWith(fresh);
      history.replaceState(null, '', url);
      status.textContent = 'Results updated.';
    } catch (error) {
      if (error.name !== 'AbortError' && current === sequence) {
        status.textContent = 'Unable to load results. Press Enter to try again.';
      }
    } finally {
      if (current === sequence) document.getElementById('applicationResults').removeAttribute('aria-busy');
    }
  }
  document.addEventListener('click', event => {
    const refresh = event.target.closest('#applicationRefresh');
    if (!refresh || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    runSearch({ keepPage: true });
  });
  search.addEventListener('input', () => {
    clearTimeout(timeout);
    controller?.abort();
    sequence++;
    if (!composing) timeout = setTimeout(runSearch, 400);
  });
  search.addEventListener('compositionstart', () => { composing = true; clearTimeout(timeout); });
  search.addEventListener('compositionend', () => { composing = false; clearTimeout(timeout); timeout = setTimeout(runSearch, 400); });
  search.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.isComposing) { event.preventDefault(); runSearch(); }
  });
  filters.forEach(filter => filter.addEventListener('change', runSearch));
  applicationFilters.addEventListener('submit', event => { event.preventDefault(); runSearch(); });
}
