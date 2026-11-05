(() => {
  const form = document.getElementById('connectForm');
  const button = document.getElementById('connectButton');
  const message = document.getElementById('connectMessage');
  const disconnect = document.getElementById('unpairDevice');
  const server = 'https://pioduranvoterregistration.com';
  const key = 'signature-device-pairing';
  let token = localStorage.getItem(key), active = false, polling = false;
  async function request(path, options = {}) {
    const response = await fetch(server + path, {...options, cache: 'no-store', signal: AbortSignal.timeout(15000)});
    const data = await response.json();
    if (!response.ok || !data.success) {
      if (response.status === 401) { localStorage.removeItem(key); token = null; form.hidden = false; disconnect.hidden = true; }
      throw new Error(data.message || 'Connection failed.');
    }
    return data;
  }
  function waiting() {
    form.hidden = true; disconnect.hidden = false;
    message.dataset.error = 'false';
    message.textContent = 'Paired. Waiting for the officer to request a signature...';
  }
  async function poll() {
    if (!token || active || polling || document.hidden) return;
    polling = true;
    try {
      const data = await request('/comelec/api/signature/device/request/', {headers: {Authorization: `Bearer ${token}`}});
      if (!data.session) { waiting(); return; }
      const session = data.session;
      active = true;
      Object.assign(document.body.dataset, {sessionStatus: session.status, sessionId: session.session_id,
        statusUrl: `${server}/comelec/admin/signature/session/${session.session_id}/status/`, completeUrl: `${server}/comelec/api/signature/complete/`});
      document.querySelector('.applicant h3').textContent = session.applicant_name;
      document.querySelector('.applicant p').textContent = `Signature sample ${session.signature_slot}`;
      document.querySelector('.prototype-badge').textContent = `Sample ${session.signature_slot} / 3`;
      document.querySelector('.session-badge').textContent = 'Active session';
      document.getElementById('connectCard').hidden = true;
      document.getElementById('signingScreen').hidden = false;
      const script = document.createElement('script'); script.src = 'signing.js'; document.body.append(script);
    } catch (error) { message.dataset.error = 'true'; message.textContent = error.message + (token ? ' Retrying automatically...' : ' Pair again with the officer.'); }
    finally { polling = false; }
  }
  form.addEventListener('submit', async event => {
    event.preventDefault(); button.disabled = true; message.textContent = 'Pairing device...';
    try {
      const data = await request('/comelec/api/signature/pair/', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({code: document.getElementById('signingLink').value.trim()})});
      localStorage.setItem(key, data.token); token = data.token;
      document.getElementById('signingLink').value = ''; waiting(); await poll();
    } catch (error) { message.dataset.error = 'true'; message.textContent = error.message; }
    finally { button.disabled = false; }
  });
  disconnect.addEventListener('click', () => {
    if (confirm('Disconnect this signing device?')) { localStorage.removeItem(key); window.location.reload(); }
  });
  document.getElementById('newSession').addEventListener('click', () => {
    if (!document.getElementById('signaturePlaceholder').hidden && !document.body.dataset.notifiedClosed && !confirm('Leave this request and discard the drawing?')) return;
    window.location.reload();
  });
  window.addEventListener('signature:closed', () => setTimeout(() => window.location.reload(), 2200));
  document.addEventListener('visibilitychange', () => { if (!document.hidden) poll(); });
  setInterval(poll, 2500);
  if (token) { waiting(); poll(); }
})();
