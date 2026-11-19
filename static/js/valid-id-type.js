/* The upload (Choose File / Take a photo) appears only after the type of document is chosen. */
(() => {
  document.querySelectorAll('select[name="valid_id_type"]').forEach(select => {
    if (select.dataset.toggleReady) return;
    select.dataset.toggleReady = '1';
    const box = select.closest('.valid-id-type-field')?.parentElement;
    const form = select.form;
    const file = form?.querySelector('input[type="file"][name="valid_id_document"]');
    if (!box || !file) return;
    const fileRequired = file.required;

    const update = () => {
      // The type is needed whenever a document is (or must be) uploaded.
      select.required = fileRequired || file.files.length > 0;
      box.toggleAttribute('data-awaiting-id-type', !select.value);
    };
    select.addEventListener('change', update);
    file.addEventListener('change', update);
    form.addEventListener('reset', () => setTimeout(update));
    form.addEventListener('offline:submitted', update);
    window.addEventListener('pageshow', update);
    update();
  });
})();
