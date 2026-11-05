(() => {
  const canvas = document.getElementById('signatureCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const submit = document.getElementById('submitSignature');
  const undo = document.getElementById('undoSignature');
  const clear = document.getElementById('clearSignature');
  const message = document.getElementById('captureMessage');
  const placeholder = document.getElementById('signaturePlaceholder');
  const strokes = [];
  let stroke = null, pointer = null, busy = false, closed = document.body.dataset.sessionStatus !== 'WAITING';
  function report(text, error = false) { message.textContent = text; message.dataset.error = String(error); }
  function controls() {
    submit.disabled = busy || closed || !strokes.some(s => s.length > 2);
    undo.disabled = clear.disabled = busy || closed || !strokes.length;
    placeholder.hidden = strokes.length > 0;
  }
  function redraw() {
    const bounds = canvas.getBoundingClientRect();
    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.round(bounds.width * ratio); canvas.height = Math.round(bounds.height * ratio);
    ctx.scale(ratio, ratio); ctx.lineWidth = 2.5; ctx.strokeStyle = '#142b54'; ctx.lineCap = ctx.lineJoin = 'round';
    for (const points of strokes) {
      ctx.beginPath();
      points.forEach((p, i) => ctx[i ? 'lineTo' : 'moveTo'](p.x * bounds.width, p.y * bounds.height));
      ctx.stroke();
    }
    controls();
  }
  function point(event) {
    const r = canvas.getBoundingClientRect();
    return {x: Math.max(0, Math.min(1, (event.clientX - r.left) / r.width)), y: Math.max(0, Math.min(1, (event.clientY - r.top) / r.height))};
  }
  canvas.addEventListener('pointerdown', event => {
    if (busy || closed || pointer !== null || (event.pointerType === 'mouse' && event.button !== 0)) return;
    event.preventDefault(); pointer = event.pointerId; canvas.setPointerCapture(pointer);
    stroke = [point(event)]; strokes.push(stroke); controls();
  });
  canvas.addEventListener('pointermove', event => {
    if (event.pointerId !== pointer || !stroke) return;
    stroke.push(point(event)); redraw();
  });
  function end(event) { if (event.pointerId === pointer) { pointer = null; stroke = null; controls(); } }
  canvas.addEventListener('pointerup', end); canvas.addEventListener('pointercancel', end);
  undo.addEventListener('click', () => { strokes.pop(); redraw(); });
  clear.addEventListener('click', () => { strokes.length = 0; redraw(); });
  new ResizeObserver(redraw).observe(canvas.parentElement);
  function close(status) {
    closed = true; controls();
    document.querySelector('.status').textContent = status === 'COMPLETED' ? 'Saved' : 'Session closed';
    report(status === 'COMPLETED' ? 'Signature saved successfully. Please wait for the registration officer.' : 'This session is closed. Ask the officer to start a new capture.');
  }
  async function status() {
    try {
      const response = await fetch(document.body.dataset.statusUrl, {cache: 'no-store'});
      if (!response.ok) throw new Error();
      const data = await response.json();
      if (data.status !== 'WAITING') close(data.status);
    } catch { if (!closed) report('Unable to check the session. Check your connection before submitting.', true); }
  }
  submit.addEventListener('click', async () => {
    if (submit.disabled) return;
    busy = true; controls(); submit.textContent = 'Saving…'; report('Saving your signature…');
    try {
      const response = await fetch(document.body.dataset.completeUrl, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({session_id: document.body.dataset.sessionId, signature: canvas.toDataURL('image/png')}),
        signal: AbortSignal.timeout(30000),
      });
      const data = await response.json();
      if (!response.ok || !data.success) throw new Error(data.message || 'Unable to save your signature.');
      close('COMPLETED');
    } catch (error) {
      report(`${error.message} Your signature is still here. Check the connection and try again.`, true);
      await status();
    } finally { busy = false; submit.textContent = closed ? 'Session closed' : 'Submit signature →'; controls(); }
  });
  const timer = setInterval(() => { if (!closed && !busy) status(); }, 3000);
  window.addEventListener('pagehide', () => clearInterval(timer));
  window.addEventListener('beforeunload', event => { if (!closed && strokes.length) { event.preventDefault(); event.returnValue = ''; } });
  if (closed) close(document.body.dataset.sessionStatus); else status();
  redraw();
})();
