(() => {
  const dialog = document.getElementById('adminActionDialog');
  if (!dialog) return;
  const title = document.getElementById('adminActionTitle');
  const message = document.getElementById('adminActionMessage');
  const confirm = document.getElementById('adminActionConfirm');
  const cancel = document.getElementById('adminActionCancel');
  let resolvePending;
  let closing = false;
  let returnFocus;
  let timer;
  window.confirmAdminAction = text => {
    if (resolvePending) return Promise.resolve(false);
    const kind = /disapprove/i.test(text) ? 'disapprove' : /delete|remove|suspend/i.test(text) ? 'delete' : /approve/i.test(text) ? 'approve' : /review/i.test(text) ? 'review' : 'confirm';
    const labels = { disapprove: 'Disapprove', delete: /suspend/i.test(text) ? 'Suspend' : 'Delete', approve: 'Approve', review: 'Review', confirm: 'Confirm' };
    title.textContent = `${labels[kind]}${kind === 'confirm' ? ' action' : ' request'}?`;
    message.textContent = text;
    confirm.textContent = labels[kind];
    dialog.dataset.kind = kind;
    returnFocus = document.activeElement;
    dialog.showModal();
    title.focus({ preventScroll: true });
    return new Promise(resolve => { resolvePending = resolve; });
  };
  function finish(result) {
    if (!resolvePending || closing) return;
    closing = true;
    dialog.classList.add('is-closing');
    const close = () => {
      const resolve = resolvePending;
      resolvePending = null;
      dialog.close();
      dialog.classList.remove('is-closing');
      closing = false;
      if (returnFocus?.isConnected) returnFocus.focus({ preventScroll: true });
      resolve(result);
    };
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) close();
    else timer = setTimeout(close, 180);
  }
  confirm.addEventListener('click', () => finish(true));
  cancel.addEventListener('click', () => finish(false));
  dialog.addEventListener('cancel', event => { event.preventDefault(); finish(false); });
  window.addEventListener('pagehide', () => clearTimeout(timer));
})();
