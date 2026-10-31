(() => {
  const dialog = document.getElementById('pendingCorrectionDialog');
  if (!dialog) return;
  let closing = false;
  let timer;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  dialog.removeAttribute('open');
  dialog.showModal();
  document.getElementById('pendingCorrectionTitle')?.focus({ preventScroll: true });
  function finishClose() {
    clearTimeout(timer);
    dialog.close();
  }
  function closeSmoothly(event) {
    event.preventDefault();
    if (closing) return;
    closing = true;
    if (reducedMotion.matches) { finishClose(); return; }
    dialog.classList.add('is-closing');
    timer = setTimeout(finishClose, 200);
  }
  dialog.querySelector('form[method="dialog"]').addEventListener('submit', closeSmoothly);
  dialog.addEventListener('cancel', closeSmoothly);
  dialog.addEventListener('close', () => {
    clearTimeout(timer);
    dialog.classList.remove('is-closing');
    closing = false;
    document.getElementById('registration_reference')?.focus({ preventScroll: true });
  });
})();
