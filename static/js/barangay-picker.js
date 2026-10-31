const barangayInput = document.getElementById('name');
const suggestions = document.getElementById('pioDuranBarangays');
if (barangayInput && suggestions) {
  const normalize = value => value.trim().replace(/\s+/g, ' ').toLocaleLowerCase();
  const choices = new Map([...suggestions.options].map(option => [normalize(option.value), option.value]));
  const save = document.getElementById('saveBarangay');
  const error = document.getElementById('barangaySelectionError');
  function update(showError = false) {
    const valid = choices.has(normalize(barangayInput.value));
    save.disabled = !valid;
    barangayInput.setCustomValidity(valid || !barangayInput.value ? '' : 'Select a barangay from the Pio Duran suggestions.');
    error.textContent = showError && barangayInput.value && !valid ? 'Select a barangay from the Pio Duran suggestions.' : '';
    return valid;
  }
  barangayInput.addEventListener('input', () => update());
  barangayInput.addEventListener('change', () => {
    const canonical = choices.get(normalize(barangayInput.value));
    if (canonical) barangayInput.value = canonical;
    update(true);
  });
  barangayInput.addEventListener('blur', () => update(true));
  barangayInput.form.addEventListener('submit', event => {
    if (!update(true)) { event.preventDefault(); barangayInput.focus(); }
  });
  update();
}
