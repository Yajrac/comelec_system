/* "Take a photo" for the Valid ID / Birth Certificate upload.
 * Phones open the back camera app; computers show a live webcam preview.
 * The photo is put into the normal file input, so validation, previews,
 * offline drafts and the AI document check all work as with an uploaded file. */
(() => {
  if (window.documentCamera) return;

  function el(tag, attrs = {}, text) {
    const node = document.createElement(tag);
    Object.entries(attrs).forEach(([k, v]) => node.setAttribute(k, v));
    if (text) node.textContent = text;
    return node;
  }

  function useFile(input, file) {
    const transfer = new DataTransfer();
    transfer.items.add(file);
    input.files = transfer.files;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }

  // Phones: the native camera app gives focus, flash and a better picture.
  function openDeviceCamera(input) {
    const picker = el('input', { type: 'file', accept: 'image/*', capture: 'environment', hidden: '' });
    picker.addEventListener('change', () => {
      if (picker.files.length) useFile(input, picker.files[0]);
      picker.remove();
    });
    document.body.append(picker);
    picker.click();
  }

  // Computers: live preview with Capture / Cancel.
  let panel, video, status, stream, target;

  function stop() {
    stream?.getTracks().forEach(track => track.stop());
    stream = null;
    if (video) video.srcObject = null;
    if (panel?.open) panel.close();
  }

  function ensurePanel() {
    if (panel) return;
    panel = el('dialog', { class: 'doc-camera-dialog', 'aria-labelledby': 'docCameraTitle' });
    video = el('video', { autoplay: '', muted: '', playsinline: '', 'aria-label': 'Live camera preview' });
    status = el('p', { class: 'doc-camera-status', role: 'status', 'aria-live': 'polite' });
    const capture = el('button', { type: 'button', class: 'doc-camera-capture' }, 'Capture');
    const cancel = el('button', { type: 'button' }, 'Cancel');
    const row = el('div', { class: 'doc-camera-buttons' });
    row.append(cancel, capture);
    panel.append(el('h2', { id: 'docCameraTitle' }, 'Take a photo of your document'),
      el('p', { class: 'doc-camera-tip' }, 'Place the whole ID or birth certificate inside the frame, in good light, and keep it steady.'),
      video, status, row);
    cancel.addEventListener('click', stop);
    panel.addEventListener('cancel', event => { event.preventDefault(); stop(); });
    capture.addEventListener('click', () => {
      if (!video.videoWidth) return;
      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      canvas.getContext('2d').drawImage(video, 0, 0);
      canvas.toBlob(blob => {
        if (!blob) { status.textContent = 'Could not take the photo. Please try again.'; return; }
        const input = target;
        stop();
        useFile(input, new File([blob], `document-photo-${Date.now()}.jpg`, { type: 'image/jpeg' }));
      }, 'image/jpeg', 0.92);
    });
    document.body.append(panel);
  }

  async function openWebcam(input) {
    ensurePanel();
    target = input;
    status.textContent = 'Allow camera access to take the photo.';
    panel.showModal();
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' }, width: { ideal: 1920 }, height: { ideal: 1080 } }, audio: false,
      });
      video.srcObject = stream;
      status.textContent = '';
    } catch (failure) {
      stop();
      const messages = {
        NotAllowedError: 'Camera access was blocked. Allow the camera in your browser settings, or upload a file instead.',
        NotFoundError: 'No camera was found. Upload a file instead.',
        NotReadableError: 'The camera is busy. Close other camera apps and try again, or upload a file instead.',
      };
      alertNear(input, messages[failure.name] || 'Could not open the camera. Upload a file instead.');
    }
  }

  function alertNear(input, text) {
    const row = input.closest('form')?.querySelector('.doc-camera-row');
    const note = row?.querySelector('.doc-camera-message');
    if (note) { note.textContent = text; note.hidden = false; }
  }

  function open(input) {
    const phone = window.matchMedia('(pointer: coarse)').matches;
    if (phone || !navigator.mediaDevices?.getUserMedia || !window.isSecureContext) openDeviceCamera(input);
    else openWebcam(input);
  }

  document.querySelectorAll('input[type="file"][name="valid_id_document"]').forEach(input => {
    if (input.dataset.cameraReady) return;
    input.dataset.cameraReady = '1';
    const row = el('div', { class: 'doc-camera-row' });
    const button = el('button', { type: 'button', class: 'doc-camera-button' });
    button.append(el('i', { class: 'bi bi-camera', 'aria-hidden': 'true' }), document.createTextNode(' Take a photo'));
    const message = el('p', { class: 'doc-camera-message', role: 'status', hidden: '' });
    button.addEventListener('click', () => { message.hidden = true; open(input); });
    row.append(button, message);
    input.insertAdjacentElement('afterend', row);
  });

  window.addEventListener('pagehide', stop);
  window.documentCamera = { open };
})();
