(() => {
    const button = document.getElementById('finishVerification');
    if (!button) return;
    function ready() {
        return button.dataset.complete === 'true' &&
            !document.querySelector('[data-slot-capture][aria-busy="true"], [data-busy="true"]');
    }
    const observer = new MutationObserver(() => {
        button.disabled = !ready();
    });
    observer.observe(document.querySelector('.biometrics-page'), {
        subtree: true, attributes: true, attributeFilter: ['aria-busy', 'data-busy']
    });
    button.addEventListener('click', async () => {
        if (!ready()) return;
        const message = 'All required fingerprints and signature samples have been saved. Finish verification and return to Applicants?';
        const confirmed = window.confirmAdminAction
            ? await window.confirmAdminAction(message)
            : window.confirm(message);
        if (confirmed && ready()) { button.disabled = true; button.form.submit(); }
    });
})();
