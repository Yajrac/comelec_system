let referenceCopyTimeout;
document.getElementById('copyReference').addEventListener('click', async () => {
  const reference = document.getElementById('registrationReference').textContent.trim();
  const status = document.getElementById('copyReferenceStatus');
  clearTimeout(referenceCopyTimeout);
  status.classList.remove('copy-error');
  try {
    if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
    await navigator.clipboard.writeText(reference);
    status.textContent = 'Copied!';
    referenceCopyTimeout = setTimeout(() => { status.textContent = ''; }, 2500);
  } catch {
    status.classList.add('copy-error');
    status.textContent = 'Unable to copy automatically. Select the reference and copy it manually.';
  }
});
document.getElementById('downloadReference').addEventListener('click', () => {
  const reference = document.getElementById('registrationReference').textContent.trim();
  const text = 'Pio Duran Voter Registration - Registration reference\n' + reference + '\n\nKeep this reference for future requests. Additional identity verification is required.\nSubmission does not mean approval.';
  const url = URL.createObjectURL(new Blob([text], {type: 'text/plain;charset=utf-8'}));
  const link = document.createElement('a'); link.href = url; link.download = reference + '.txt';
  document.body.appendChild(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
});
