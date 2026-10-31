document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('valid_id_document');
  if (!input) return;
  const link = document.createElement('a');
  link.textContent = 'View selected document';
  link.target = '_blank'; link.rel = 'noopener'; link.hidden = true;
  input.after(link);
  let url;
  input.addEventListener('change', () => {
    if (url) URL.revokeObjectURL(url);
    link.hidden = true; link.removeAttribute('href');
    const file = input.files[0];
    if (!file) return;
    url = URL.createObjectURL(file); link.href = url; link.hidden = false;
  });
  window.addEventListener('pagehide', () => { if (url) URL.revokeObjectURL(url); });
});
