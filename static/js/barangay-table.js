const barangaySearch = document.getElementById('barangaySearch');
if (barangaySearch) {
  const rows = [...document.querySelectorAll('[data-barangay-row]')];
  const batchSize = 10;
  let visibleLimit = batchSize;
  const more = document.getElementById('barangayShowMore');
  const less = document.getElementById('barangayShowLess');
  const count = document.getElementById('barangayResultCount');
  const table = document.querySelector('.barangay-table');
  const empty = document.createElement('tr');
  empty.hidden = true;
  const cell = document.createElement('td');
  cell.colSpan = table.tHead.rows[0].cells.length;
  cell.className = 'barangay-search-empty';
  cell.textContent = 'No matching barangays. Try another name.';
  empty.append(cell); table.tBodies[0].append(empty);
  function update() {
    const query = barangaySearch.value.trim().toLocaleLowerCase();
    const matching = rows.filter(row => row.dataset.name.toLocaleLowerCase().includes(query));
    const visible = new Set(matching.slice(0, visibleLimit));
    rows.forEach(row => { row.hidden = !visible.has(row); });
    empty.hidden = !query || matching.length > 0;
    count.textContent = `Showing ${visible.size} of ${matching.length} barangays`;
    more.hidden = matching.length <= visibleLimit;
    less.hidden = visibleLimit <= batchSize || matching.length <= batchSize;
  }
  barangaySearch.addEventListener('input', () => { visibleLimit = batchSize; update(); });
  more.addEventListener('click', () => { visibleLimit += batchSize; update(); if (more.hidden && !less.hidden) less.focus(); });
  less.addEventListener('click', () => {
    visibleLimit = batchSize; update();
    if (!more.hidden) more.focus(); else barangaySearch.focus();
  });
  document.getElementById('barangayTableTools').hidden = false;
  document.getElementById('barangayTableControls').hidden = false;
  update();
}
const deleteDialog = document.getElementById('barangayDeleteDialog');
if (deleteDialog) {
  const form = document.getElementById('barangayDeleteForm');
  const message = document.getElementById('barangayDeleteMessage');
  const confirm = document.getElementById('barangayDeleteConfirm');
  const cancel = document.getElementById('barangayDeleteCancel');
  document.querySelectorAll('[data-delete-barangay]').forEach(link => {
    link.addEventListener('click', event => {
      event.preventDefault();
      form.action = link.href;
      message.textContent = `Delete ${link.dataset.deleteBarangay}? This cannot be undone. Barangays used by applicants or registration requests cannot be deleted.`;
      confirm.hidden = false;
      cancel.textContent = 'Cancel';
      deleteDialog.showModal();
    });
  });
  cancel.addEventListener('click', () => deleteDialog.close());
  form.addEventListener('submit', async event => {
    event.preventDefault();
    confirm.disabled = true;
    cancel.disabled = true;
    confirm.textContent = 'Deleting...';
    try {
      const response = await fetch(form.action, {
        method: 'POST', body: new FormData(form), headers: { Accept: 'application/json' },
      });
      const result = await response.json();
      if (response.ok && result.deleted) { window.location.reload(); return; }
      message.textContent = result.error || 'Unable to delete this barangay. Please try again.';
      confirm.hidden = response.status === 409;
      cancel.textContent = 'Close';
    } catch (_) {
      message.textContent = 'Unable to delete this barangay. Please check your connection and try again.';
    } finally {
      confirm.disabled = false;
      cancel.disabled = false;
      confirm.textContent = 'Delete barangay';
    }
  });
}

if (barangaySearch) {
  const key = 'barangay-refresh-search:' + location.pathname;
  const saved = sessionStorage.getItem(key);
  if (saved !== null) {
    sessionStorage.removeItem(key);
    barangaySearch.value = saved;
    barangaySearch.dispatchEvent(new Event('input', { bubbles: true }));
  }
  document.querySelectorAll('.admin-table-refresh').forEach(link => link.addEventListener('click', () => {
    sessionStorage.setItem(key, barangaySearch.value);
  }));
}
