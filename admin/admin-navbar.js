(() => {
  'use strict';

  function isActive(file) {
    const page = (window.location.pathname.split('/').pop() || '').toLowerCase();
    return page === file.toLowerCase();
  }

  function initLogout() {
    document.querySelectorAll('[data-action="logout"]').forEach((el) => {
      el.addEventListener('click', (e) => {
        e.preventDefault();
        try { window.sessionStorage.removeItem('adminToken'); } catch (_) {}
        try { window.sessionStorage.removeItem('adminUser'); } catch (_) {}
        try { window.localStorage.removeItem('userSession'); } catch (_) {}
        window.location.href = '/';
      });
    });
  }

  function initMenuToggle(root) {
    const toggle = root.querySelector('.admin-topnav-toggle');
    const menu = root.querySelector('.admin-topnav-links');
    if (!toggle || !menu) return;

    toggle.addEventListener('click', () => {
      menu.classList.toggle('open');
      toggle.setAttribute('aria-expanded', menu.classList.contains('open') ? 'true' : 'false');
    });

    document.addEventListener('click', (e) => {
      if (!menu.classList.contains('open')) return;
      if (menu.contains(e.target) || toggle.contains(e.target)) return;
      menu.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
    });
  }

  function injectNavbar() {
    // Only inject on pages that have the admin sidebar layout.
    // Admin pages in this repo vary: some have `.dashboard` + `#sidebar`, others only have `aside.sidebar`.
    const hasSidebarLayout = !!document.querySelector('aside.sidebar');
    if (!hasSidebarLayout) return;
    if (document.querySelector('.admin-topnav')) return;

    document.body.classList.add('admin-topnav-enabled');

    const nav = document.createElement('header');
    nav.className = 'admin-topnav';
    nav.innerHTML = `
      <a class="admin-topnav-brand" href="dashboard.html" aria-label="Admin dashboard">
        <span class="admin-topnav-badge" aria-hidden="true">🛡️</span>
        <span>Climate EWS Admin</span>
      </a>

      <nav class="admin-topnav-links" aria-label="Admin navigation">
        <a class="admin-topnav-link ${isActive('dashboard.html') ? 'active' : ''}" href="dashboard.html">Dashboard</a>
        <a class="admin-topnav-link ${isActive('users.html') ? 'active' : ''}" href="users.html">Users</a>
        <a class="admin-topnav-link ${isActive('alerts.html') ? 'active' : ''}" href="alerts.html">Alerts</a>
        <a class="admin-topnav-link ${isActive('data.html') ? 'active' : ''}" href="data.html">Data</a>
        <a class="admin-topnav-link ${isActive('models.html') ? 'active' : ''}" href="models.html">Models</a>
        <a class="admin-topnav-link ${isActive('monitoring.html') ? 'active' : ''}" href="monitoring.html">Monitoring</a>
        <a class="admin-topnav-link ${isActive('reports.html') ? 'active' : ''}" href="reports.html">Reports</a>
      </nav>

      <div class="admin-topnav-right">
        <a class="admin-topnav-link" href="/" data-action="logout">Logout</a>
        <button class="admin-topnav-toggle" type="button" aria-label="Open menu" aria-expanded="false">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <line x1="3" y1="12" x2="21" y2="12"></line>
            <line x1="3" y1="6" x2="21" y2="6"></line>
            <line x1="3" y1="18" x2="21" y2="18"></line>
          </svg>
        </button>
      </div>
    `;

    document.body.insertBefore(nav, document.body.firstChild);
    initMenuToggle(nav);
    initLogout();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectNavbar);
  } else {
    injectNavbar();
  }
})();
