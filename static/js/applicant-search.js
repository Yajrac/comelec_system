const applicantFilters = document.getElementById('applicantFilters');
if (applicantFilters) {
  const search = applicantFilters.elements.search;
  const barangay = applicantFilters.elements.barangay;
  const status = document.getElementById('applicantSearchStatus');
  let timeout;
  let controller;
  let sequence = 0;
  let composing = false;
  async function runSearch() {
    clearTimeout(timeout);
    controller?.abort();
    controller = new AbortController();
    const current = ++sequence;
    const url = new URL(window.location.href);
    url.search = new URLSearchParams(new FormData(applicantFilters)).toString();
    const results = document.getElementById('applicantResults');
    results.setAttribute('aria-busy', 'true');
    status.textContent = 'Searching...';
    try {
      const response = await fetch(url, { signal: controller.signal, cache: 'no-store', credentials: 'same-origin' });
      if (!response.ok || response.redirected) throw new Error('Search failed');
      const page = new DOMParser().parseFromString(await response.text(), 'text/html');
      const fresh = page.getElementById('applicantResults');
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
      if (current === sequence) document.getElementById('applicantResults').removeAttribute('aria-busy');
    }
  }
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
  barangay.addEventListener('change', runSearch);
  applicantFilters.addEventListener('submit', event => { event.preventDefault(); runSearch(); });
}
