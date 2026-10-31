const recordModal = document.getElementById('recordFoundModal');
if (recordModal) {
  const referenceInput = document.getElementById('homeReference');
  const closeModal = () => recordModal.close();
  recordModal.querySelectorAll('[data-close-record-modal]').forEach((button) => {
    button.addEventListener('click', closeModal);
  });
  recordModal.addEventListener('click', (event) => {
    if (event.target !== recordModal) return;
    const rect = recordModal.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right ||
        event.clientY < rect.top || event.clientY > rect.bottom) closeModal();
  });
  recordModal.addEventListener('close', () => {
    document.body.classList.remove('record-modal-open');
    recordModal.querySelectorAll('details[open]').forEach((menu) => { menu.open = false; });
    referenceInput?.focus();
    referenceInput?.select();
  });
  recordModal.showModal();
  document.body.classList.add('record-modal-open');
}
