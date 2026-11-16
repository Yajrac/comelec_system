const form = document.getElementById('loginForm');
const password = document.getElementById('password');
document.getElementById('showPassword').addEventListener('change', (event) => {
  password.type = event.target.checked ? 'text' : 'password';
});
function resetButton() {
  document.getElementById('loginButton').disabled = false;
  document.getElementById('buttonContent').hidden = false;
  document.getElementById('buttonLoading').hidden = true;
  document.getElementById('loginStatus').textContent = '';
}
form.addEventListener('submit', () => {
  document.getElementById('loginButton').disabled = true;
  document.getElementById('buttonContent').hidden = true;
  document.getElementById('buttonLoading').hidden = false;
  document.getElementById('loginStatus').textContent = 'Signing in...';
});
window.addEventListener('pageshow', resetButton);

// Locked after too many failures: count down and keep Sign in disabled until the lock ends.
(() => {
  const box = document.querySelector('[data-lock-seconds]');
  const text = document.getElementById('loginErrorText');
  const button = document.getElementById('loginButton');
  if (!box || !text || !button) return;
  const endsAt = Date.now() + Number(box.dataset.lockSeconds) * 1000;
  const format = seconds => `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
  function tick() {
    const left = Math.ceil((endsAt - Date.now()) / 1000);
    if (left <= 0) {
      text.textContent = 'You can sign in again now.';
      box.classList.add('is-unlocked');
      button.disabled = false;
      button.removeAttribute('aria-disabled');
      return;
    }
    text.textContent = `Too many unsuccessful attempts. Please try again in ${format(left)}.`;
    button.disabled = true;
    button.setAttribute('aria-disabled', 'true');
    setTimeout(tick, 1000 - ((endsAt - Date.now()) % 1000 || 0));
  }
  window.addEventListener('pageshow', () => setTimeout(tick, 0)); // runs after resetButton re-enables it
  tick();
})();
