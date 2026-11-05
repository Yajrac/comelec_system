const signatureCapture = document.getElementById('signatureCapture');
if (signatureCapture) {
  const cards = [...signatureCapture.querySelectorAll('[data-signature-slot]')];
  const token = document.querySelector('#csrfForm [name="csrfmiddlewaretoken"]')?.value || '';
  document.getElementById('pairSignatureDevice')?.addEventListener('click', async event => {
    if (!confirm('Pair a signing device to your officer account? Any previously paired device will be disconnected.')) return;
    const button = event.currentTarget;
    const output = document.getElementById('signaturePairingCode');
    button.disabled = true;
    try {
      const response = await fetch(signatureCapture.dataset.pairUrl, {method: 'POST', headers: {'X-CSRFToken': token}});
      const data = await response.json();
      if (!response.ok || !data.success) throw new Error(data.message || 'Unable to generate code.');
      output.textContent = `Pairing code: ${data.code.match(/.{1,4}/g).join('-')} — enter in the app within 5 minutes, then start Capture Signature. One device per officer account.`;
    } catch (error) { output.textContent = error.message; }
    finally { button.disabled = false; }
  });
  const uuidPlaceholder = '00000000-0000-0000-0000-000000000000';
  let active = null;
  let timer;
  function setMessage(card, text, error = false) {
    const message = card.querySelector('[data-slot-message]');
    message.textContent = text;
    message.className = 'bio-message ' + (error ? 'error' : 'info');
  }
  function updateSummary() {
    const count = cards.filter(card => card.dataset.captured === 'true').length;
    const status = document.getElementById('allSignaturesStatus');
    status.textContent = `${count} / 3 captured`;
    status.className = 'bio-status' + (count === 3 ? ' success' : '');
    const summary = document.getElementById('summarySignature');
    if (summary) summary.textContent = `${count} / 3 saved`;
  }
  function showLoading(button, text) {
    const spinner = document.createElement('span');
    spinner.className = 'signature-loading-spinner';
    spinner.setAttribute('aria-hidden', 'true');
    const label = document.createElement('span');
    label.textContent = text;
    button.replaceChildren(spinner, label);
  }
  function resetControls() {
    clearTimeout(timer);
    cards.forEach(card => {
      const button = card.querySelector('[data-slot-capture]');
      button.disabled = false;
      button.removeAttribute('aria-busy');
      button.textContent = `${card.dataset.captured === 'true' ? 'Retake' : 'Capture'} Signature ${card.dataset.signatureSlot}`;
      card.querySelector('[data-slot-cancel]').hidden = true;
    });
    active = null;
  }
  async function jsonResponse(response) {
    const data = await response.json();
    if (!response.ok || !data.success) throw new Error(data.message || 'Unable to complete the request.');
    return data;
  }
  async function cancelCapture(card) {
    if (!active?.session) return;
    try {
      const url = signatureCapture.dataset.cancelUrl.replace(uuidPlaceholder, active.session);
      const data = await jsonResponse(await fetch(url, { method: 'POST', headers: { 'X-CSRFToken': token } }));
      if (data.status === 'COMPLETED') { await poll(); return; }
      resetControls();
      setMessage(card, 'Capture cancelled. Previously saved samples have been kept.');
    } catch (error) { setMessage(card, error.message + ' Try cancelling again.', true); }
  }
  async function poll() {
    const current = active;
    if (!current?.session) return;
    try {
      const url = signatureCapture.dataset.statusUrl.replace(uuidPlaceholder, current.session);
      const data = await jsonResponse(await fetch(url, { cache: 'no-store' }));
      if (active !== current) return;
      if (data.status === 'COMPLETED' && data.signature_captured && data.signature_url) {
        const preview = current.card.querySelector('[data-slot-preview]');
        const link = document.createElement('a');
        link.href = data.signature_url; link.target = '_blank'; link.rel = 'noopener noreferrer';
        const image = document.createElement('img');
        image.src = data.signature_url; image.alt = `Applicant signature ${current.card.dataset.signatureSlot}`;
        link.append(image); preview.replaceChildren(link); preview.classList.add('captured');
        current.card.dataset.captured = 'true';
        const status = current.card.querySelector('[data-slot-status]');
        status.textContent = 'Captured'; status.className = 'bio-status success';
        resetControls(); updateSummary(); setMessage(current.card, 'Signature saved successfully.');
        const overall = document.getElementById('summaryVerification');
        if (overall) overall.textContent = data.biometrics_completed ? 'Complete' : 'Pending';
        if (data.biometrics_completed) window.location.reload();
        return;
      }
      if (['CANCELLED', 'EXPIRED'].includes(data.status)) {
        resetControls(); setMessage(current.card, 'Session closed. Start a new capture when ready.', true); return;
      }
      if (Date.now() - current.started > 5 * 60 * 1000) {
        setMessage(current.card, 'Still waiting for the device. You can cancel and try again.', true);
      }
    } catch (error) {
      if (active !== current) return;
      setMessage(current.card, 'Connection interrupted. Retrying status check; do not start another capture yet.', true);
    }
    if (active === current) timer = setTimeout(poll, 1500);
  }
  cards.forEach(card => {
    card.querySelector('[data-slot-capture]').addEventListener('click', async () => {
      if (active) return;
      active = { card, session: null, started: Date.now() };
      cards.forEach(item => { item.querySelector('[data-slot-capture]').disabled = true; });
      const button = card.querySelector('[data-slot-capture]');
      button.setAttribute('aria-busy', 'true'); showLoading(button, 'Starting capture...');
      try {
        const data = await jsonResponse(await fetch(signatureCapture.dataset.startUrl, {
          method: 'POST', headers: { 'X-CSRFToken': token, 'Content-Type': 'application/json' },
          body: JSON.stringify({ signature_slot: Number(card.dataset.signatureSlot) }),
        }));
        active.session = data.session_id;
        showLoading(button, 'Waiting for signing device...');
        card.querySelector('[data-slot-cancel]').hidden = false;
        setMessage(card, `Please sign sample ${card.dataset.signatureSlot} on the connected device. Other samples will not be changed.`);
        if (data.signing_url) {
          const link = document.createElement('a');
          link.href = data.signing_url; link.target = '_blank'; link.rel = 'noopener noreferrer';
          link.textContent = ' Open signing page (copy this link to the tablet).';
          card.querySelector('[data-slot-message]').append(link);
        }
        poll();
      } catch (error) { resetControls(); setMessage(card, error.message, true); }
    });
    card.querySelector('[data-slot-cancel]').addEventListener('click', () => cancelCapture(card));
  });
  window.addEventListener('beforeunload', () => clearTimeout(timer));
  updateSummary();
}
