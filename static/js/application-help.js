(() => {
  const guide = document.getElementById('applicationHelp');
  if (!guide) return;
  const result = document.getElementById('applicationHelpResult');
  const suggestion = document.getElementById('applicationHelpSuggestion');
  const proceed = document.getElementById('applicationHelpContinue');
  const confirmation = document.getElementById('applicationProceedDialog');
  const confirmLink = document.getElementById('applicationProceedConfirm');
  const choices = [...guide.querySelectorAll('[data-service]')];
  let selected, loading = false;
  choices.forEach(button => {
    button.addEventListener('click', () => {
      if (loading) return;
      const route = guide.querySelector(`[data-route="${button.dataset.service}"]`);
      if (!route) return;
      const service = [...document.querySelectorAll('.public-service-options a')].find(link => link.href === route.href);
      if (!service) return;
      const card = button.closest('.home-service-card');
      if (card === result.parentElement && !result.hidden) {
        card.getAnimations().forEach(animation => animation.cancel());
        const expandedHeight = card.getBoundingClientRect().height;
        result.hidden = true;
        selected = null;
        button.setAttribute('aria-pressed', 'false');
        card.classList.remove('is-selected');
        if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
          const collapsedHeight = card.getBoundingClientRect().height;
          card.animate([
            {height: `${expandedHeight}px`, overflow: 'hidden'},
            {height: `${collapsedHeight}px`, overflow: 'hidden'},
          ], {duration: 240, easing: 'ease-out'});
        }
        return;
      }
      const previous = result.closest('.home-service-card');
      const cards = [...new Set([previous, card].filter(Boolean))];
      cards.forEach(item => item.getAnimations().forEach(animation => animation.cancel()));
      const heights = cards.map(item => item.getBoundingClientRect().height);
      selected = {url: route.href, label: service.querySelector('span').textContent};
      choices.forEach(choice => {
        const active = choice === button;
        choice.setAttribute('aria-pressed', String(active));
        choice.closest('.home-service-card').classList.toggle('is-selected', active);
      });
      suggestion.textContent = selected.label;
      card.append(result);
      result.hidden = false;
      if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        cards.forEach((item, index) => {
          const height = item.getBoundingClientRect().height;
          item.animate([
            {height: `${heights[index]}px`, overflow: 'hidden'},
            {height: `${height}px`, overflow: 'hidden'},
          ], {duration: 240, easing: 'ease-out'});
        });
      }
    });
  });
  proceed.addEventListener('click', async () => {
    if (!selected || loading) return;
    loading = true;
    proceed.disabled = true;
    proceed.setAttribute('aria-busy', 'true');
    const spinner = document.createElement('span');
    spinner.className = 'home-proceed-spinner';
    spinner.setAttribute('aria-hidden', 'true');
    proceed.replaceChildren(spinner, document.createTextNode(' Preparing form…'));
    // Allow the loading state to paint before the confirmation opens.
    await new Promise(resolve => setTimeout(resolve, 350));
    document.getElementById('applicationProceedType').textContent = selected.label;
    confirmLink.href = selected.url;
    confirmation.showModal();
    document.getElementById('applicationProceedCancel').focus();
    proceed.disabled = false;
    proceed.removeAttribute('aria-busy');
    proceed.textContent = 'Proceed →';
    loading = false;
  });
  document.getElementById('applicationProceedCancel').addEventListener('click', () => confirmation.close());
  confirmation.addEventListener('close', () => proceed.focus());
  confirmLink.addEventListener('click', event => {
    if (confirmLink.getAttribute('aria-disabled') === 'true') { event.preventDefault(); return; }
    confirmLink.setAttribute('aria-disabled', 'true');
    confirmLink.setAttribute('aria-busy', 'true');
    const spinner = document.createElement('span');
    spinner.className = 'home-proceed-spinner';
    spinner.setAttribute('aria-hidden', 'true');
    confirmLink.replaceChildren(spinner, document.createTextNode(' Opening form…'));
  });
  window.addEventListener('pageshow', () => {
    confirmLink.removeAttribute('aria-disabled');
    confirmLink.removeAttribute('aria-busy');
    confirmLink.textContent = 'Yes, open form →';
    if (confirmation.open) confirmation.close();
  });
})();
