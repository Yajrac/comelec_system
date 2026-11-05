(() => {
    const header = document.querySelector('.public-header');
    const button = document.getElementById('publicMenuToggle');
    const menu = document.getElementById('publicNavigation');
    if (!header || !button || !menu) return;
    header.dataset.menuReady = 'true';
    button.hidden = false;
    function close(returnFocus = false) {
        menu.classList.remove('is-open');
        button.setAttribute('aria-expanded', 'false');
        button.setAttribute('aria-label', 'Open navigation menu');
        if (returnFocus) button.focus();
    }
    button.addEventListener('click', () => {
        const open = menu.classList.toggle('is-open');
        button.setAttribute('aria-expanded', String(open));
        button.setAttribute('aria-label', open ? 'Close navigation menu' : 'Open navigation menu');
    });
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && menu.classList.contains('is-open')) close(true);
    });
    document.addEventListener('click', event => {
        if (!header.contains(event.target)) close();
        else if (event.target.closest('#publicNavigation a')) close();
    });
    matchMedia('(min-width: 992px)').addEventListener('change', () => close());
})();
