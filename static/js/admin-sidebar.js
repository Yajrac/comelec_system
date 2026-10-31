const collapseButton = document.getElementById('sidebarCollapse');
if (collapseButton) {
  const key = 'admin-sidebar-collapsed';
  let collapsed = false;
  const tooltip = document.createElement('div');
  tooltip.className = 'admin-nav-tooltip';
  tooltip.id = 'adminNavTooltip';
  tooltip.setAttribute('role', 'tooltip');
  tooltip.hidden = true;
  document.body.appendChild(tooltip);
  let tooltipLink;
  function hideTooltip() {
    tooltip.hidden = true;
    tooltipLink?.removeAttribute('aria-describedby');
    tooltipLink = null;
  }
  try { collapsed = localStorage.getItem(key) === 'true'; } catch { /* Storage may be unavailable. */ }
  function apply() {
    hideTooltip();
    document.body.classList.toggle('admin-sidebar-collapsed', collapsed);
    collapseButton.setAttribute('aria-expanded', String(!collapsed));
    collapseButton.setAttribute('aria-label', collapsed ? 'Expand sidebar' : 'Collapse sidebar');
    collapseButton.title = collapsed ? 'Expand sidebar' : 'Collapse sidebar';
  }
  document.querySelectorAll('.admin-sidebar .admin-nav-link').forEach(link => {
    const label = link.textContent.trim().replace(/\s+/g, ' ');
    link.setAttribute('aria-label', label);
    function showTooltip() {
      if (!collapsed || !window.matchMedia('(min-width: 992px)').matches) return;
      hideTooltip();
      tooltipLink = link;
      tooltip.textContent = label;
      tooltip.hidden = false;
      const rect = link.getBoundingClientRect();
      tooltip.style.left = `${document.getElementById('adminDesktopSidebar').getBoundingClientRect().right + 10}px`;
      tooltip.style.top = `${Math.max(8, Math.min(rect.top + (rect.height - tooltip.offsetHeight) / 2, window.innerHeight - tooltip.offsetHeight - 8))}px`;
      link.setAttribute('aria-describedby', tooltip.id);
    }
    link.addEventListener('mouseenter', showTooltip);
    link.addEventListener('focus', showTooltip);
    link.addEventListener('mouseleave', hideTooltip);
    link.addEventListener('blur', hideTooltip);
  });
  window.addEventListener('resize', hideTooltip);
  document.addEventListener('scroll', hideTooltip, true);
  document.addEventListener('keydown', event => { if (event.key === 'Escape') hideTooltip(); });
  apply();
  collapseButton.addEventListener('click', () => {
    collapsed = !collapsed;
    apply();
    try { localStorage.setItem(key, String(collapsed)); } catch { /* Continue without persistence. */ }
  });
}
const mobileSidebar = document.getElementById('adminMobileSidebar');
const mobileToggle = document.querySelector('[data-bs-target="#adminMobileSidebar"]');
if (mobileSidebar && mobileToggle) {
  mobileToggle.setAttribute('aria-expanded', 'false');
  mobileSidebar.addEventListener('shown.bs.offcanvas', () => mobileToggle.setAttribute('aria-expanded', 'true'));
  mobileSidebar.addEventListener('hidden.bs.offcanvas', () => mobileToggle.setAttribute('aria-expanded', 'false'));
  const desktop = window.matchMedia('(min-width: 992px)');
  desktop.addEventListener('change', event => {
    if (event.matches) window.bootstrap?.Offcanvas.getInstance(mobileSidebar)?.hide();
  });
}
