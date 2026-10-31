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
