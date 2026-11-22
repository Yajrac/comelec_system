/* The upload (Choose File / Take a photo) appears only after the type of document is chosen,
 * and its label, tip and messages name that document ("Upload your IBP ID"). */
(() => {
  // How each choice is named in sentences.
  const sentenceName = option => (option.value === 'OTHER_GOVERNMENT' ? 'government-issued ID' : option.textContent.trim());

  document.querySelectorAll('select[name="valid_id_type"]').forEach(select => {
    if (select.dataset.toggleReady) return;
    select.dataset.toggleReady = '1';
    const box = select.closest('.valid-id-type-field')?.parentElement;
    const form = select.form;
    const file = form?.querySelector('input[type="file"][name="valid_id_document"]');
    if (!box || !file) return;
    const fileRequired = file.required;
    const label = form.querySelector('label[for="valid_id_document"]');
    const originalLabel = label?.innerHTML;
    const optional = /\(optional\)/i.test(label?.textContent || '');
    const asterisk = label?.querySelector('.required, .required-mark');

    let tip = box.querySelector('.valid-id-type-tip');
    if (!tip && label) {
      tip = document.createElement('small');
      tip.className = 'form-text d-block mb-2 valid-id-type-tip';
      label.insertAdjacentElement('afterend', tip);
    }

    const update = () => {
      // The type is needed whenever a document is (or must be) uploaded.
      select.required = fileRequired || file.files.length > 0;
      box.toggleAttribute('data-awaiting-id-type', !select.value);
      const option = select.selectedOptions[0];
      if (!select.value || !option) {
        if (label) label.innerHTML = originalLabel;
        if (tip) tip.textContent = '';
        delete file.dataset.documentName;
        delete file.dataset.requiredMessage;
        return;
      }
      const name = sentenceName(option);
      file.dataset.documentName = name;
      file.dataset.requiredMessage = `Upload your ${name} or take a photo of it.`;
      if (label) {
        label.replaceChildren(document.createTextNode(`Upload your ${name}${optional ? ' (optional)' : ''}`));
        if (asterisk) label.append(' ', asterisk.cloneNode(true));
      }
      if (tip) tip.textContent = `Upload a clear photo or scan of your ${name}. Make sure your name is readable.`;
    };
    select.addEventListener('change', update);
    file.addEventListener('change', update);
    form.addEventListener('reset', () => setTimeout(update));
    form.addEventListener('offline:submitted', update);
    window.addEventListener('pageshow', update);
    update();
  });
})();
