(() => {
  function daysInMonth(year, month) {
    return new Date(Date.UTC(year, month, 0)).getUTCDate();
  }
  function makeDate(year, month, day) {
    if (!/^[0-9]{4}$/.test(year) || Number(year) < 1900 || Number(month) < 1 || Number(month) > 12 || Number(day) < 1 || Number(day) > daysInMonth(Number(year), Number(month))) return '';
    return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = { daysInMonth, makeDate };
  if (typeof document === 'undefined') return;
  const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  document.querySelectorAll('input[type="date"][name="birthdate"]').forEach(original => {
    if (original.disabled || original.readOnly) return;
    const required = original.required;
    const wrapper = document.createElement('div');
    wrapper.className = 'segmented-date';
    wrapper.setAttribute('role', 'group');
    wrapper.setAttribute('aria-label', 'Birthdate: month, day, year');
    const icon = document.createElement('span');
    icon.className = 'segmented-date-icon';
    icon.setAttribute('aria-hidden', 'true');
    icon.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="3" y="5" width="18" height="16" rx="3"/><path d="M7 3v4m10-4v4M3 11h18"/></svg>';
    function segment(label, tag) {
      const container = document.createElement('label');
      container.className = 'date-segment';
      const caption = document.createElement('span'); caption.textContent = label;
      const control = document.createElement(tag);
      control.id = `${original.id}-${label.toLowerCase()}`;
      control.required = required;
      control.setAttribute('aria-label', `Birthdate ${label.toLowerCase()}`);
      container.append(caption, control); wrapper.append(container);
      return control;
    }
    wrapper.append(icon);
    const month = segment('Month', 'select');
    const day = segment('Day', 'select');
    const year = segment('Year', 'input');
    month.add(new Option('Month', ''));
    months.forEach((name, index) => month.add(new Option(name, String(index + 1))));
    day.add(new Option('Day', ''));
    for (let number = 1; number <= 31; number++) day.add(new Option(String(number), String(number)));
    year.type = 'text'; year.inputMode = 'numeric'; year.maxLength = 4; year.placeholder = 'YYYY'; year.pattern = '[0-9]{4}'; year.autocomplete = 'bday-year';
    month.autocomplete = 'bday-month'; day.autocomplete = 'bday-day';
    const yearOptions = document.createElement('datalist');
    yearOptions.id = `${original.id}-year-options`;
    for (let value = new Date().getFullYear(); value >= 1900; value--) {
      yearOptions.append(new Option(String(value), String(value)));
    }
    year.setAttribute('list', yearOptions.id);
    wrapper.append(yearOptions);
    year.setAttribute('aria-description', 'Type a four-digit birth year or choose from the suggestions. Future birthdates are not allowed.');

    const electionDate = original.dataset.electionDate;
    const eligibility = document.createElement('small');
    eligibility.className = 'birthdate-eligibility';
    eligibility.setAttribute('role', 'status');
    eligibility.setAttribute('aria-live', 'polite');
    const initial = original.value;
    original.type = 'hidden'; original.required = false;
    original.after(wrapper);
    if (electionDate) wrapper.after(eligibility);
    document.querySelector(`label[for="${original.id}"]`)?.setAttribute('for', month.id);
    function sync(emit = true) {
      year.setCustomValidity(''); day.setCustomValidity('');
      const allPresent = year.value && month.value && day.value;
      const iso = allPresent ? makeDate(year.value, month.value, day.value) : '';
      if (year.value.length === 4 && (Number(year.value) < 1900 || Number(year.value) > new Date().getFullYear())) year.setCustomValidity('Enter a valid birth year from 1900 to the current year.');
      if (allPresent && !iso && year.value.length === 4 && !year.validationMessage) day.setCustomValidity('Choose a valid day for this month and year.');
      if (iso) {
        const today = new Date();
        const todayIso = `${today.getFullYear()}-${String(today.getMonth()+1).padStart(2,'0')}-${String(today.getDate()).padStart(2,'0')}`;
        if (iso >= todayIso) year.setCustomValidity('Birthdate must be earlier than today.');
      }
      eligibility.textContent = '';
      eligibility.classList.remove('is-ineligible');
      if (iso && electionDate && !year.validationMessage && !day.validationMessage) {
        const [ey, em, ed] = electionDate.split('-').map(Number);
        const [by, bm, bd] = iso.split('-').map(Number);
        const age = ey - by - ((em < bm || (em === bm && ed < bd)) ? 1 : 0);
        const label = new Date(ey, em - 1, ed).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        if (age < 15) {
          year.setCustomValidity(`You must turn 15 on or before election day (${label}).`);
          eligibility.textContent = `Age ${age} on ${label}: below the minimum age of 15.`;
          eligibility.classList.add('is-ineligible');
        } else {
          const category = age < 18 ? 'SK age requirement met' : age <= 30 ? 'Regular voter and SK age requirements met' : 'Regular voter age requirement met';
          eligibility.textContent = `Age ${age} on ${label}: ${category}.`;
        }
      }
      original.value = iso;
      if (emit) {
        original.dispatchEvent(new Event('input', { bubbles: true }));
        original.dispatchEvent(new Event('change', { bubbles: true }));
      }
    }
    function restore(value) {
      const parts = value.split('-');
      year.value = parts[0] || ''; month.value = String(Number(parts[1]) || ''); day.value = String(Number(parts[2]) || '');
      sync(false);
    }
    restore(initial);
    month.addEventListener('change', () => { sync(); if (month.value) day.focus(); });
    day.addEventListener('change', () => { sync(); if (day.value) year.focus(); });
    year.addEventListener('input', () => { year.value = year.value.replace(/[^0-9]/g, '').slice(0, 4); sync(); });
    original.form?.addEventListener('reset', () => setTimeout(() => restore(original.defaultValue), 0));
  });
})();
