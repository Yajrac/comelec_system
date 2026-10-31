(() => {
  const form = document.getElementById('walkInSearch');
  if (!form) return;
  form.querySelectorAll('select').forEach(select => select.addEventListener('change', () => form.requestSubmit()));
  const menus = [...document.querySelectorAll('.walk-in-actions')];
  function closeMenus() { menus.forEach(menu => { menu.open = false; }); }
  menus.forEach(menu => {
    const trigger = menu.querySelector('summary');
    trigger.setAttribute('aria-expanded', 'false');
    menu.addEventListener('toggle', () => {
      trigger.setAttribute('aria-expanded', String(menu.open));
      if (!menu.open) return;
      menus.forEach(other => { if (other !== menu) other.open = false; });
      const popup = menu.querySelector('.walk-in-action-menu');
      const rect = trigger.getBoundingClientRect();
      const height = popup.offsetHeight;
      const below = window.innerHeight - rect.bottom - 12;
      popup.style.left = `${Math.max(12, Math.min(rect.right - popup.offsetWidth, window.innerWidth - popup.offsetWidth - 12))}px`;
      popup.style.top = `${Math.max(12, below >= height ? rect.bottom + 8 : rect.top - height - 8)}px`;
    });
  });
  document.addEventListener('click', event => {
    if (!event.target.closest('.walk-in-actions')) closeMenus();
  });
  document.addEventListener('focusin', event => {
    if (!event.target.closest('.walk-in-actions')) closeMenus();
  });
  window.addEventListener('resize', closeMenus);
  document.addEventListener('scroll', closeMenus, true);
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') document.querySelectorAll('.walk-in-actions[open]').forEach(menu => { menu.open = false; menu.querySelector('summary').focus(); });
  });
})();
