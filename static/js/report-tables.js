document.querySelectorAll('.report-table-card').forEach((card, tableIndex) => {
  if (card.querySelector('#typeReportTitle')) return;
  const table = card.querySelector('table');
  if (!table) return;
  const rows = [...table.querySelectorAll('tbody > tr')].filter(row => !row.querySelector('td[colspan]'));
  const size = 10;
  const pages = Math.max(1, Math.ceil(rows.length / size));
  let current = 1;
  const footer = document.createElement('div');
  footer.className = 'report-pagination';
  const count = document.createElement('span');
  count.setAttribute('role', 'status');
  const nav = document.createElement('nav');
  nav.setAttribute('aria-label', `Report table ${tableIndex + 1} pages`);
  footer.append(count, nav);
  card.appendChild(footer);
  function button(label, page, disabled = false) {
    const element = document.createElement('button');
    element.type = 'button';
    element.textContent = label;
    element.disabled = disabled;
    if (page === current && /^\d+$/.test(label)) element.setAttribute('aria-current', 'page');
    element.addEventListener('click', () => { current = page; draw(); });
    nav.appendChild(element);
  }
  function draw() {
    rows.forEach((row, index) => { row.hidden = index < (current - 1) * size || index >= current * size; });
    count.textContent = rows.length ? `Showing ${(current - 1) * size + 1}–${Math.min(current * size, rows.length)} of ${rows.length} records` : '0 records';
    nav.replaceChildren();
    button('Previous', current - 1, current === 1);
    const numbers = new Set([1, pages]);
    for (let page = Math.max(1, current - 2); page <= Math.min(pages, current + 2); page++) numbers.add(page);
    let last = 0;
    [...numbers].sort((a, b) => a - b).forEach(page => {
      if (last && page - last > 1) { const dots = document.createElement('span'); dots.textContent = '…'; nav.appendChild(dots); }
      button(String(page), page);
      last = page;
    });
    button('Next', current + 1, current === pages);
  }
  draw();
});
