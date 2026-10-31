(() => {
  const dialog = document.getElementById('applicationHelp');
  if (!dialog) return;
  const result = document.getElementById('applicationHelpResult');
  const choices = [...dialog.querySelectorAll('[data-service]')];
  choices.forEach(button => {
    button.setAttribute('aria-pressed', 'false');
    button.addEventListener('click', () => {
      const route = dialog.querySelector(`[data-route="${button.dataset.service}"]`);
      const service = [...document.querySelectorAll('.public-service-options a')].find(link => link.href === route.href);
      if (!service) return;
      choices.forEach(choice => choice.setAttribute('aria-pressed', String(choice === button)));
      document.getElementById('applicationHelpSuggestion').textContent = service.querySelector('span').textContent;
      document.getElementById('applicationHelpContinue').href = route.href;
      result.hidden = false;
      result.scrollIntoView({ block: 'nearest' });
    });
  });
})();
