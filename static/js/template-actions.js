(() => {
  const confirmedClicks = new WeakSet();
  const confirmedForms = new WeakSet();
  document.addEventListener('submit', event => {
    const message = event.target.dataset.confirmSubmit;
    if (confirmedForms.delete(event.target) || event.defaultPrevented || !message) return;
    if (typeof window.confirmAdminAction === 'function') {
      event.preventDefault();
      const form = event.target;
      const submitter = event.submitter;
      window.confirmAdminAction(message).then(accepted => {
        if (!accepted || !form.isConnected) return;
        confirmedForms.add(form);
        form.requestSubmit(submitter || undefined);
      });
    } else if (!window.confirm(message)) event.preventDefault();
  });
  document.addEventListener('click', event => {
    const target = event.target.closest('[data-confirm-click], [data-click-action]');
    if (!target || event.defaultPrevented) return;
    if (!confirmedClicks.delete(target) && target.dataset.confirmClick) {
      if (typeof window.confirmAdminAction === 'function') {
        event.preventDefault();
        window.confirmAdminAction(target.dataset.confirmClick).then(accepted => {
          if (!accepted || !target.isConnected) return;
          confirmedClicks.add(target);
          target.click();
        });
        return;
      }
      if (!window.confirm(target.dataset.confirmClick)) { event.preventDefault(); return; }
    }
    const action = target.dataset.clickAction;
    if (!action) return;
    if (action === 'print') {
      window.print();
      return;
    }
    const actions = ['openDocumentViewer', 'closeDocumentViewer', 'showReview', 'backToForm', 'submitApplication'];
    if (actions.includes(action) && typeof window[action] === 'function') {
      if (window[action]() === false) event.preventDefault();
    }
  });
})();
