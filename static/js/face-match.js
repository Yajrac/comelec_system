/* New Registration: the selfie opens after the document, and (when turned on) is compared with the
 * photo on the ID. A birth certificate has no photo, so the office compares the selfie in person. */
(() => {
  const form = document.getElementById('registrationForm');
  const section = document.querySelector('.profile-fields');
  const lockedNote = document.getElementById('selfieLocked');
  if (!form || !section || !lockedNote || window.faceMatch) return;
  const select = form.elements.namedItem('valid_id_type');
  const documentInput = form.elements.namedItem('valid_id_document');
  const photo = document.getElementById('photo');
  const note = document.getElementById('selfieMatchNote');
  const consentRow = document.getElementById('faceConsentRow');
  const consent = document.getElementById('faceConsent');
  const result = document.getElementById('faceMatchResult');
  const take = document.getElementById('takeSelfie');
  if (!select || !documentInput || !photo) return;

  const enabled = form.dataset.faceMatch === '1' && Boolean(consent);
  const NO_PHOTO = new Set(['PSA_BIRTH_CERTIFICATE']);
  const BLOCKING = new Set(['not_matched', 'no_face', 'consent', 'error']);
  const DOCUMENT_BAD = new Set(['invalid', 'mismatch', 'type_mismatch', 'error']);
  const CONSENT = 'Tick the box above to agree to the selfie comparison.';
  let documentStatus = null; // latest result of the document check
  let known = null;          // {key, status, message}
  let pending = null;

  const hasPhoto = () => Boolean(select.value) && !NO_PHOTO.has(select.value);
  const documentName = () => (select.value === 'OTHER_GOVERNMENT' ? 'government-issued ID'
    : select.selectedOptions[0]?.textContent.trim() || 'ID');
  const selfie = () => photo.files?.[0] || null;
  const documentFile = () => documentInput.files?.[0] || null;
  const officerVerified = () => form.querySelector('[name="officer_verified"]')?.checked;
  const needsCheck = () => enabled && hasPhoto() && documentFile() && selfie();
  const fileKey = file => (file ? `${file.name}|${file.size}|${file.lastModified}` : '');
  const currentKey = () => [fileKey(selfie()), fileKey(documentFile()), select.value].join('#');

  function updateLock() {
    let locked = '';
    if (!select.value || !documentFile()) locked = 'Upload your document first. Then take a selfie.';
    else if (documentStatus === 'checking') locked = 'Verifying your document… Then take a selfie.';
    else if (DOCUMENT_BAD.has(documentStatus)) locked = 'Fix your document first. Then take a selfie.';
    section.toggleAttribute('data-selfie-locked', Boolean(locked));
    if (locked) lockedNote.textContent = locked;
    note.hidden = !select.value;
    if (select.value) {
      note.textContent = !hasPhoto()
        ? 'Take a selfie. Your birth certificate has no photo, so the office will compare your selfie with you in person during your biometrics visit.'
        : enabled ? `Take a selfie. It will be compared with the photo on your ${documentName()}.`
          : `Take a selfie. The office will compare it with the photo on your ${documentName()}.`;
    }
    if (consentRow) {
      consentRow.hidden = !hasPhoto();
      consent.required = enabled && hasPhoto();
    }
  }

  function show(state, text, retake = false) {
    const icon = document.createElement('span');
    icon.className = 'doc-check-inline-icon';
    icon.setAttribute('aria-hidden', 'true');
    icon.textContent = { checking: '', passed: '✓', invalid: '✕', unavailable: 'i', offline: 'i' }[state] || '';
    const message = document.createElement('span');
    message.className = 'doc-check-inline-text';
    message.textContent = text;
    result.replaceChildren(icon, message);
    if (retake && take) {
      const row = document.createElement('div');
      row.className = 'doc-check-inline-actions';
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = 'Retake selfie';
      button.addEventListener('click', () => take.click());
      row.append(button);
      result.append(row);
    }
    result.dataset.state = state;
    result.hidden = false;
  }

  function render(answer) {
    const status = answer.status;
    if (status === 'matched') return show('passed', answer.message);
    if (status === 'not_matched' || status === 'no_face') return show('invalid', answer.message, true);
    if (status === 'consent') return show('invalid', CONSENT);
    if (status === 'error') return show('invalid', answer.message || 'Take a selfie and upload your document first.');
    if (status === 'offline') return show('offline', 'You are offline. Your selfie will be compared with your ID before it is uploaded.');
    if (['flagged', 'unsure', 'unavailable'].includes(status)) return show('unavailable', answer.message);
    result.hidden = true;
  }

  async function ask() {
    const body = new FormData();
    body.append('photo', selfie());
    body.append('valid_id_document', documentFile());
    body.append('valid_id_type', select.value);
    if (consent?.checked) body.append('face_consent', '1');
    try {
      const response = await fetch('/face-check/', { method: 'POST', body, credentials: 'same-origin',
        signal: AbortSignal.timeout(60000) });
      const data = await response.json().catch(() => null);
      return data || { status: response.ok ? 'unavailable' : 'offline' };
    } catch {
      return { status: 'offline' };
    }
  }

  function check() {
    if (!needsCheck() || DOCUMENT_BAD.has(documentStatus) || documentStatus === 'checking') {
      result.hidden = true;
      return Promise.resolve(null);
    }
    if (!consent.checked) { render({ status: 'consent' }); return Promise.resolve({ status: 'consent' }); }
    const key = currentKey();
    if (known?.key === key) { render(known); return Promise.resolve(known); }
    if (pending?.key === key) return pending.promise;
    show('checking', 'Comparing your selfie with your ID…');
    const promise = ask().then(answer => {
      if (pending?.key === key) pending = null;
      if (currentKey() !== key) return answer; // a newer selfie or document was chosen meanwhile
      known = { key, ...answer };
      render(known);
      return known;
    });
    pending = { key, promise };
    return promise;
  }

  /** Before Review / Submit: true when the selfie may be used. */
  async function ensure() {
    if (!needsCheck() || officerVerified()) return true;
    const answer = await check();
    if (!answer || ['offline', 'disabled'].includes(answer.status)) return true;
    if (!BLOCKING.has(answer.status)) return true;
    window.backToForm?.();
    (answer.status === 'consent' ? consentRow : result)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    if (answer.status === 'consent') consent.focus({ preventScroll: true });
    return false;
  }

  const documentChanged = () => { documentStatus = null; updateLock(); check(); };
  select.addEventListener('change', documentChanged);
  documentInput.addEventListener('change', documentChanged);
  form.addEventListener('documentcheck:result', event => {
    documentStatus = event.detail?.status || null;
    updateLock();
    check();
  });
  photo.addEventListener('change', check);
  consent?.addEventListener('change', check);
  const reset = () => { known = null; pending = null; documentStatus = null; result.hidden = true; setTimeout(updateLock); };
  form.addEventListener('reset', reset);
  form.addEventListener('offline:submitted', reset);
  updateLock();

  window.faceMatch = { ensure };
})();
