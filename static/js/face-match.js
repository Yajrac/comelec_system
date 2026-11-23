/* New Registration: the selfie opens after the document. A dark selfie must be retaken (checked here,
 * nothing is sent). When face match is on, the selfie is then compared with the photo on the ID.
 * A birth certificate has no photo, so the office compares the selfie in person. */
(() => {
  const form = document.getElementById('registrationForm');
  const section = document.querySelector('.profile-fields');
  const lockedNote = document.getElementById('selfieLocked');
  if (!form || !section || !lockedNote || window.faceMatch) return;
  const select = form.elements.namedItem('valid_id_type');
  const documentInput = form.elements.namedItem('valid_id_document');
  const photo = document.getElementById('photo');
  const note = document.getElementById('selfieMatchNote');
  const result = document.getElementById('faceMatchResult');
  const take = document.getElementById('takeSelfie');
  if (!select || !documentInput || !photo || !result) return;

  const enabled = form.dataset.faceMatch === '1';
  const NO_PHOTO = new Set(['PSA_BIRTH_CERTIFICATE']);
  const BLOCKING = new Set(['not_matched', 'no_face', 'unclear', 'error', 'too_dark']);
  const DOCUMENT_BAD = new Set(['invalid', 'mismatch', 'type_mismatch', 'error']);
  const DARK = 70;        // average brightness 0-255 below which a selfie is too dark
  const DARK_TRIES = 3;   // after this many dark selfies the applicant may continue (office reviews)
  let documentStatus = null; // latest result of the document check
  let known = null;          // {key, status, message}
  let pending = null;
  let quality = null;        // {key, dark}
  let darkTries = 0;

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
        : enabled ? `Your selfie will be automatically compared with the photo on your ${documentName()} to confirm your identity.`
          : `Take a selfie. The office will compare it with the photo on your ${documentName()}.`;
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
    if (['not_matched', 'no_face', 'unclear'].includes(status)) return show('invalid', answer.message, true);
    if (status === 'error') return show('invalid', answer.message || 'Take a selfie and upload your document first.');
    if (status === 'offline') return show('offline', 'You are offline. Your selfie will be compared with your ID before it is uploaded.');
    if (['flagged', 'unsure', 'unavailable'].includes(status)) return show('unavailable', answer.message);
    result.hidden = true;
  }

  /** Average brightness (0-255) of the photo, or null when it cannot be read. */
  function brightness(file) {
    return new Promise(resolve => {
      const url = URL.createObjectURL(file);
      const image = new Image();
      image.onload = () => {
        try {
          const width = 64;
          const height = Math.max(1, Math.round(width * image.naturalHeight / Math.max(1, image.naturalWidth)));
          const canvas = document.createElement('canvas');
          canvas.width = width; canvas.height = height;
          const context = canvas.getContext('2d', { willReadFrequently: true });
          context.drawImage(image, 0, 0, width, height);
          const pixels = context.getImageData(0, 0, width, height).data;
          let total = 0;
          for (let i = 0; i < pixels.length; i += 4) total += 0.2126 * pixels[i] + 0.7152 * pixels[i + 1] + 0.0722 * pixels[i + 2];
          resolve(total / (pixels.length / 4));
        } catch { resolve(null); } finally { URL.revokeObjectURL(url); }
      };
      image.onerror = () => { URL.revokeObjectURL(url); resolve(null); };
      image.src = url;
    });
  }

  /** Dark selfies are retaken before anything is sent. */
  async function checkLight() {
    const file = selfie();
    if (!file) { quality = null; return true; }
    const key = fileKey(file);
    if (quality?.key !== key) {
      const value = await brightness(file);
      if (fileKey(selfie()) !== key) return false; // a newer selfie was taken meanwhile
      const dark = value !== null && value < DARK;
      if (dark) darkTries += 1;
      quality = { key, dark, allowed: !dark || darkTries >= DARK_TRIES };
    }
    if (!quality.dark) return true;
    if (quality.allowed) {
      show('unavailable', 'Your selfie is still dark. You can continue; the office will check it.');
      return true;
    }
    show('invalid', 'Your selfie is too dark. Move to a brighter place or face a light, then retake it.', true);
    return false;
  }

  async function check() {
    if (!selfie()) { result.hidden = true; return null; }
    if (!(await checkLight())) return { status: 'too_dark' };
    if (!needsCheck() || DOCUMENT_BAD.has(documentStatus) || documentStatus === 'checking') {
      if (!quality?.dark) result.hidden = true;
      return null;
    }
    const key = currentKey();
    if (known?.key === key) { render(known); return known; }
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

  async function ask() {
    const body = new FormData();
    body.append('photo', selfie());
    body.append('valid_id_document', documentFile());
    body.append('valid_id_type', select.value);
    try {
      const response = await fetch('/face-check/', { method: 'POST', body, credentials: 'same-origin',
        signal: AbortSignal.timeout(60000) });
      const data = await response.json().catch(() => null);
      return data || { status: response.ok ? 'unavailable' : 'offline' };
    } catch {
      return { status: 'offline' };
    }
  }

  /** Before Review / Submit: true when the selfie may be used. */
  async function ensure() {
    if (!selfie() || officerVerified()) return true;
    const answer = await check();
    if (!answer || ['offline', 'disabled'].includes(answer.status) || !BLOCKING.has(answer.status)) return true;
    window.backToForm?.();
    result.scrollIntoView({ behavior: 'smooth', block: 'center' });
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
  const reset = () => {
    known = null; pending = null; quality = null; darkTries = 0; documentStatus = null;
    result.hidden = true;
    setTimeout(updateLock);
  };
  form.addEventListener('reset', reset);
  form.addEventListener('offline:submitted', reset);
  updateLock();

  window.faceMatch = { ensure };
})();
