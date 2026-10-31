(() => {
  const dialog = document.getElementById('adminLogoutDialog');
  if (!dialog) return;
  let opener;
  document.querySelectorAll('[data-admin-logout]').forEach(button => {
    button.addEventListener('click', () => {
      opener = button;
      dialog.showModal();
    });
  });
  document.getElementById('cancelAdminLogout').addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => opener?.focus());
})();
