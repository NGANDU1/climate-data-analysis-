/* ============================================
   TemplateMo 3D Glassmorphism Dashboard
   https://templatemo.com
   JavaScript
============================================ */

(function() {
    'use strict';

    // ============================================
    // Theme Toggle
    // ============================================
    function initThemeToggle() {
        const themeToggle = document.getElementById('theme-toggle');
        if (!themeToggle) return;

        const iconSun = themeToggle.querySelector('.icon-sun');
        const iconMoon = themeToggle.querySelector('.icon-moon');
        
        function setTheme(theme) {
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('theme', theme);
            
            if (iconSun && iconMoon) {
                if (theme === 'light') {
                    iconSun.style.display = 'none';
                    iconMoon.style.display = 'block';
                } else {
                    iconSun.style.display = 'block';
                    iconMoon.style.display = 'none';
                }
            }
        }
        
        // Check for saved theme preference or default to light (report style)
        const savedTheme = localStorage.getItem('theme') || 'light';
        setTheme(savedTheme);
        
        themeToggle.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            setTheme(currentTheme === 'dark' ? 'light' : 'dark');
        });
    }

    // ============================================
    // 3D Tilt Effect
    // ============================================
    function initTiltEffect() {
        // Disabled for government/report style (avoid “playful” motion).
        return;
        document.querySelectorAll('.glass-card-3d').forEach(card => {
            card.addEventListener('mousemove', (e) => {
                const rect = card.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                
                const centerX = rect.width / 2;
                const centerY = rect.height / 2;
                
                const rotateX = (y - centerY) / 20;
                const rotateY = (centerX - x) / 20;
                
                card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateZ(10px)`;
            });
            
            card.addEventListener('mouseleave', () => {
                card.style.transform = 'perspective(1000px) rotateX(0) rotateY(0) translateZ(0)';
            });
        });
    }

    // ============================================
    // Animated Counters
    // ============================================
    function animateCounter(element, target, duration = 2000) {
        const start = 0;
        const startTime = performance.now();
        
        function update(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Easing function
            const easeOut = 1 - Math.pow(1 - progress, 3);
            const current = Math.floor(start + (target - start) * easeOut);
            
            if (element.dataset.prefix) {
                element.textContent = element.dataset.prefix + current.toLocaleString() + (element.dataset.suffix || '');
            } else {
                element.textContent = current.toLocaleString() + (element.dataset.suffix || '');
            }
            
            if (progress < 1) {
                requestAnimationFrame(update);
            }
        }
        
        requestAnimationFrame(update);
    }

    function initCounters() {
        const counters = document.querySelectorAll('.stat-value');
        counters.forEach(counter => {
            const text = counter.textContent;
            const value = parseInt(text.replace(/[^0-9]/g, ''));

            if (!Number.isFinite(value)) {
                return;
            }
            
            if (text.includes('$')) {
                counter.dataset.prefix = '$';
            }
            if (text.includes('%')) {
                counter.dataset.suffix = '%';
            }
            
            animateCounter(counter, value);
        });
    }

    // ============================================
    // Mobile Menu Toggle
    // ============================================
    function initMobileMenu() {
        const menuToggle = document.querySelector('.mobile-menu-toggle');
        const sidebar = document.getElementById('sidebar');
        
        if (menuToggle && sidebar) {
            menuToggle.addEventListener('click', () => {
                sidebar.classList.toggle('open');
            });

            // Close sidebar when clicking outside
            document.addEventListener('click', (e) => {
                if (sidebar.classList.contains('open') && 
                    !sidebar.contains(e.target) && 
                    !menuToggle.contains(e.target)) {
                    sidebar.classList.remove('open');
                }
            });
        }
    }

    // ============================================
    // Form Validation (for login/register)
    // ============================================
    function initFormValidation() {
        const forms = document.querySelectorAll('form[data-validate]');
        
        forms.forEach(form => {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                
                let isValid = true;
                const inputs = form.querySelectorAll('.form-input[required]');
                
                inputs.forEach(input => {
                    if (!input.value.trim()) {
                        isValid = false;
                        input.style.borderColor = '#ff6b6b';
                    } else {
                        input.style.borderColor = '';
                    }
                });

                // Email validation
                const emailInput = form.querySelector('input[type="email"]');
                if (emailInput && emailInput.value) {
                    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                    if (!emailRegex.test(emailInput.value)) {
                        isValid = false;
                        emailInput.style.borderColor = '#ff6b6b';
                    }
                }

                if (isValid) {
                    // Form is valid - you can add your submission logic here
                    console.log('Form is valid');
                    // For demo purposes, redirect to dashboard
                    if (form.dataset.redirect) {
                        window.location.href = form.dataset.redirect;
                    }
                }
            });
        });
    }

    // ============================================
    // Password Visibility Toggle
    // ============================================
    function initPasswordToggle() {
        const toggleButtons = document.querySelectorAll('.password-toggle');
        
        toggleButtons.forEach(button => {
            button.addEventListener('click', () => {
                const input = button.parentElement.querySelector('input');
                const icon = button.querySelector('svg');
                
                if (input.type === 'password') {
                    input.type = 'text';
                    icon.innerHTML = '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/>';
                } else {
                    input.type = 'password';
                    icon.innerHTML = '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>';
                }
            });
        });
    }

    // ============================================
    // Smooth Page Transitions
    // ============================================
    function initPageTransitions() {
        const links = document.querySelectorAll('a[href$=".html"]');
        
        links.forEach(link => {
            link.addEventListener('click', (e) => {
                // Skip external links
                if (link.hostname !== window.location.hostname) return;
                if (link.matches('[data-action="logout"]')) return;
                
                e.preventDefault();
                const href = link.getAttribute('href');
                
                document.body.style.opacity = '0';
                document.body.style.transition = 'opacity 0.3s ease';
                
                setTimeout(() => {
                    window.location.href = href;
                }, 300);
            });
        });

        // Fade in on page load
        window.addEventListener('load', () => {
            document.body.style.opacity = '1';
        });
    }

    // ============================================
    // Logout (viewer + admin)
    // ============================================
    function initLogout() {
        const logoutLinks = document.querySelectorAll('[data-action="logout"], #logout-link');
        if (logoutLinks.length === 0) return;

        logoutLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                try { window.localStorage.removeItem('userSession'); } catch (_) {}
                try { window.sessionStorage.removeItem('adminToken'); } catch (_) {}
                try { window.sessionStorage.removeItem('adminUser'); } catch (_) {}
                window.location.href = '/';
            });
        });
    }

    // ============================================
    // Settings Persistence (localStorage)
    // ============================================
    function initSettingsPersistence() {
        const allFields = Array.from(document.querySelectorAll('[data-setting-key]'));
        if (allFields.length === 0) return;

        const storageKey = 'ews_settings_v1';

        const API_BASE = (() => {
            const params = new URLSearchParams(window.location.search);
            const override = params.get('apiBase');
            if (override) return override.replace(/\/$/, '');

            const host = window.location.hostname;
            const port = window.location.port;
            const isLocalhost = host === 'localhost' || host === '127.0.0.1';
            const isFlaskPort = port === '5000';
            if (isLocalhost && !isFlaskPort) {
                return 'http://localhost:5000/api';
            }

            return '/api';
        })();

        function readForm() {
            const data = {};
            fields.forEach(el => {
                const key = el.getAttribute('data-setting-key');
                if (!key) return;

                if (el instanceof HTMLInputElement && el.type === 'checkbox') {
                    data[key] = !!el.checked;
                } else {
                    data[key] = el.value;
                }
            });
            return data;
        }

        function applyForm(data) {
            fields.forEach(el => {
                const key = el.getAttribute('data-setting-key');
                if (!key) return;
                if (!(key in data)) return;

                if (el instanceof HTMLInputElement && el.type === 'checkbox') {
                    el.checked = !!data[key];
                } else {
                    el.value = data[key];
                }
            });
        }

        function getAdminContext() {
            try {
                const token = window.sessionStorage.getItem('adminToken');
                const admin = JSON.parse(window.sessionStorage.getItem('adminUser') || 'null');
                if (token && admin && admin.id) return { token, admin };
            } catch (_) {}
            return null;
        }

        function getUserContext() {
            try {
                const session = JSON.parse(window.localStorage.getItem('userSession') || 'null');
                if (session && session.user && session.user.id) return session;
            } catch (_) {}
            return null;
        }

        const adminCtx = getAdminContext();
        const userCtx = getUserContext();
        const isAdmin = !!adminCtx;

        // Restrict admin-only sections/fields for normal users.
        if (!isAdmin) {
            document.querySelectorAll('[data-admin-only-section]').forEach(el => {
                el.style.display = 'none';
            });
            document.querySelectorAll('[data-setting-scope="admin"]').forEach(el => {
                try {
                    el.setAttribute('disabled', 'disabled');
                    el.setAttribute('readonly', 'readonly');
                } catch (_) {}
            });
        }

        // Update settings page identity text (avoid showing "Administrator" for normal users).
        const nameEl =
            document.getElementById('settings-profile-name') ||
            document.querySelector('#tab-profile .profile-info h2');
        const metaEl =
            document.getElementById('settings-profile-meta') ||
            document.querySelector('#tab-profile .profile-info p');
        if (nameEl) {
            if (adminCtx && adminCtx.admin && adminCtx.admin.username) {
                nameEl.textContent = adminCtx.admin.username;
            } else if (userCtx && userCtx.user && userCtx.user.name) {
                nameEl.textContent = userCtx.user.name;
            } else {
                nameEl.textContent = 'Climate EWS';
            }
        }
        if (metaEl) {
            if (adminCtx && adminCtx.admin && adminCtx.admin.username) {
                metaEl.textContent = 'System Administrator';
            } else if (userCtx && userCtx.user) {
                const email = userCtx.user.email ? String(userCtx.user.email) : '';
                metaEl.textContent = email ? email : 'User';
            } else {
                metaEl.textContent = 'Signed in';
            }
        }

        const fields = allFields.filter(el => {
            const scope = el.getAttribute('data-setting-scope');
            return isAdmin ? true : scope !== 'admin';
        });
        if (fields.length === 0) return;

        async function loadFromServer() {
            try {
                if (adminCtx) {
                    const res = await fetch(`${API_BASE}/admin/settings?admin_id=${encodeURIComponent(adminCtx.admin.id)}`, {
                        headers: { Authorization: `Bearer ${adminCtx.token}` }
                    });
                    const json = await res.json().catch(() => ({}));
                    if (res.ok && json && json.success) return json.settings || {};
                }
                if (userCtx) {
                    const res = await fetch(`${API_BASE}/users/${encodeURIComponent(userCtx.user.id)}/settings`, {
                        headers: userCtx.token ? { Authorization: `Bearer ${userCtx.token}` } : {}
                    });
                    const json = await res.json().catch(() => ({}));
                    if (res.ok && json && json.success) return json.settings || {};
                }
            } catch (_) {}

            return null;
        }

        async function saveToServer(settings) {
            if (adminCtx) {
                const res = await fetch(`${API_BASE}/admin/settings`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${adminCtx.token}` },
                    body: JSON.stringify({ admin_id: adminCtx.admin.id, settings })
                });
                const json = await res.json().catch(() => ({}));
                if (!res.ok || !json.success) throw new Error(json.message || json.error || 'Save failed');
                return;
            }

            if (userCtx) {
                const res = await fetch(`${API_BASE}/users/${encodeURIComponent(userCtx.user.id)}/settings`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json', ...(userCtx.token ? { Authorization: `Bearer ${userCtx.token}` } : {}) },
                    body: JSON.stringify({ settings })
                });
                const json = await res.json().catch(() => ({}));
                if (!res.ok || !json.success) throw new Error(json.message || json.error || 'Save failed');
                return;
            }

            throw new Error('Not signed in');
        }

        // Load: prefer server, fall back to local storage.
        (async () => {
            const fromServer = await loadFromServer();
            if (fromServer && typeof fromServer === 'object') {
                applyForm(fromServer);
                try { window.localStorage.setItem(storageKey, JSON.stringify(fromServer)); } catch (_) {}
                return;
            }

            let saved = {};
            try {
                saved = JSON.parse(window.localStorage.getItem(storageKey) || '{}') || {};
            } catch (_) {
                saved = {};
            }
            if (saved && typeof saved === 'object') {
                applyForm(saved);
            }
        })();

        const initialSnapshot = readForm();

        document.querySelectorAll('[data-action="settings-save"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const next = readForm();
                (async () => {
                    try {
                        await saveToServer(next);
                        try { window.localStorage.setItem(storageKey, JSON.stringify(next)); } catch (_) {}
                        alert('Settings saved');
                    } catch (err) {
                        alert(err && err.message ? err.message : 'Save failed');
                    }
                })();
            });
        });

        document.querySelectorAll('[data-action="settings-cancel"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                applyForm(initialSnapshot);
            });
        });
    }

    // ============================================
    // Settings Tab Navigation
    // ============================================
    function initSettingsTabs() {
        const tabLinks = document.querySelectorAll('.settings-nav-link[data-tab]');
        
        if (tabLinks.length === 0) return;

        tabLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                
                // Get target tab
                const tabId = link.getAttribute('data-tab');
                
                // Remove active class from all nav links
                document.querySelectorAll('.settings-nav-link').forEach(navLink => {
                    navLink.classList.remove('active');
                });
                
                // Add active class to clicked link
                link.classList.add('active');
                
                // Hide all tab contents
                document.querySelectorAll('.settings-tab-content').forEach(tab => {
                    tab.classList.remove('active');
                });
                
                // Show target tab content
                const targetTab = document.getElementById('tab-' + tabId);
                if (targetTab) {
                    targetTab.classList.add('active');
                }
            });
        });

        // Theme select sync with toggle
        const themeSelect = document.getElementById('theme-select');
        if (themeSelect) {
            const currentTheme = localStorage.getItem('theme') || 'dark';
            themeSelect.value = currentTheme;
            
            themeSelect.addEventListener('change', () => {
                const theme = themeSelect.value;
                if (theme === 'system') {
                    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                    document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
                } else {
                    document.documentElement.setAttribute('data-theme', theme);
                    localStorage.setItem('theme', theme);
                }
                
                // Update theme toggle icons
                const iconSun = document.querySelector('#theme-toggle .icon-sun');
                const iconMoon = document.querySelector('#theme-toggle .icon-moon');
                if (iconSun && iconMoon) {
                    const effectiveTheme = document.documentElement.getAttribute('data-theme');
                    if (effectiveTheme === 'light') {
                        iconSun.style.display = 'none';
                        iconMoon.style.display = 'block';
                    } else {
                        iconSun.style.display = 'block';
                        iconMoon.style.display = 'none';
                    }
                }
            });
        }
    }

    // ============================================
    // Initialize All Functions
    // ============================================
    function init() {
        initThemeToggle();
        initTiltEffect();
        initCounters();
        initMobileMenu();
        initFormValidation();
        initPasswordToggle();
        initPageTransitions();
        initSettingsTabs();
        initLogout();
        initSettingsPersistence();
    }

    // Run on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
