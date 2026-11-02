/* Keep the visible date order independent of the device's regional settings. */
(() => {
  document.querySelectorAll('#applicationFilters input[type="date"]').forEach(picker => {
    const wrapper = document.createElement('div');
    wrapper.className = 'application-date-field';
    picker.before(wrapper);
    const display = document.createElement('input');
    display.type = 'text';
    display.className = 'form-control';
    display.placeholder = 'mm/dd/yyyy';
    display.inputMode = 'numeric';
    display.maxLength = 10;
    display.autocomplete = 'off';
    display.id = picker.id;
    picker.id += 'Picker';
    picker.setAttribute('aria-label', `${picker.name === 'date_from' ? 'From' : 'To'} date calendar`);
    picker.className = 'application-date-picker';
    const icon = document.createElement('i');
    icon.className = 'bi bi-calendar3 application-date-icon';
    icon.setAttribute('aria-hidden', 'true');
    wrapper.append(display, icon, picker);
    function restore() {
      const [year, month, day] = picker.value.split('-');
      display.value = year ? `${month}/${day}/${year}` : '';
      display.setCustomValidity('');
    }
    restore();
    picker.addEventListener('change', restore);
    picker.addEventListener('click', () => {
      if (typeof picker.showPicker === 'function') {
        try { picker.showPicker(); } catch (_) { /* Native control remains available. */ }
      }
    });
    display.addEventListener('input', () => {
      const match = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(display.value);
      let iso = '';
      if (match) {
        const [, month, day, year] = match;
        const date = new Date(`${year}-${month}-${day}T00:00:00Z`);
        if (Number(year) > 0 && !Number.isNaN(date.getTime()) &&
            date.toISOString().slice(0, 10) === `${year}-${month}-${day}`) {
          iso = `${year}-${month}-${day}`;
        }
      }
      picker.value = iso;
      display.setCustomValidity(display.value && !iso ? 'Enter a valid date in mm/dd/yyyy format.' : '');
    });
    display.addEventListener('change', () => {
      // Do not overwrite an incomplete entry when notifying the filter handler.
      if (display.validity.valid) {
        picker.dispatchEvent(new Event('change', { bubbles: true }));
      } else {
        display.reportValidity();
      }
    });
    picker.form?.addEventListener('reset', () => setTimeout(restore, 0));
  });
})();
