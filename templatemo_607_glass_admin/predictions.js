/**
 * Predictions page script
 * Uses /api/risk/outlook (location + date) and works offline using saved DB readings.
 */

(function () {
    'use strict';

    const API_BASE = (() => {
        const params = new URLSearchParams(window.location.search);
        const override = params.get('apiBase') || window.localStorage.getItem('apiBase');
        if (override) return override.replace(/\/$/, '');

        const host = window.location.hostname;
        const port = window.location.port;
        if ((host === 'localhost' || host === '127.0.0.1') && port && port !== '5000') {
            return 'http://localhost:5000/api';
        }
        return '/api';
    })();

    function hasAdminSession() {
        try { return !!window.sessionStorage.getItem('adminToken'); } catch (_) { return false; }
    }

    function requireViewerSession() {
        const session = window.localStorage.getItem('userSession');
        if (!session && !hasAdminSession()) {
            window.location.href = 'login.html';
            return false;
        }
        return true;
    }

    if (!requireViewerSession()) return;

    const statusEl = document.getElementById('status');
    const summaryEl = document.getElementById('summary');
    const messageEl = document.getElementById('message');
    const actionsEl = document.getElementById('actions');
    const pillEl = document.getElementById('risk-pill');
    const tableBody = document.getElementById('table-body');

    const regionEl = document.getElementById('region');
    const dateEl = document.getElementById('date');
    const daysEl = document.getElementById('days');
    const methodEl = document.getElementById('method');

    function escapeHtml(s) {
        return String(s ?? '').replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
    }

    function fmtNum(v, suffix = '') {
        if (v === null || v === undefined || Number.isNaN(Number(v))) return '—';
        return `${Number(v).toFixed(1)}${suffix}`;
    }

    function setRiskPill(level) {
        const cls = (level || 'low').toLowerCase();
        pillEl.className = `pill ${escapeHtml(cls)}`;
        pillEl.textContent = String(level || 'low').toUpperCase();
    }

    function renderActions(items) {
        const list = Array.isArray(items) ? items : [];
        if (!list.length) {
            actionsEl.innerHTML = '';
            return;
        }
        actionsEl.innerHTML = list.map((x) => `<li>${escapeHtml(x)}</li>`).join('');
    }

    function renderTable(rows) {
        if (!rows.length) {
            tableBody.innerHTML = '<tr><td colspan="7" class="mono">No predictions found.</td></tr>';
            return;
        }
        tableBody.innerHTML = rows.map((r) => {
            const cc = r.predicted_conditions || {};
            const lvl = (r.risk_level || 'low').toLowerCase();
            return `
                <tr>
                    <td class="mono">${escapeHtml(r.date || '')}</td>
                    <td><span class="risk-badge ${escapeHtml(lvl)}">${escapeHtml(String(r.risk_level || 'low').toUpperCase())}</span></td>
                    <td>${escapeHtml(r.message || '')}</td>
                    <td>${fmtNum(r.confidence_score, '')}</td>
                    <td>${fmtNum(cc.temperature, '°C')}</td>
                    <td>${fmtNum(cc.humidity, '%')}</td>
                    <td>${fmtNum(cc.rainfall, 'mm')}</td>
                </tr>
            `;
        }).join('');
    }

    async function loadRegions() {
        const res = await fetch(`${API_BASE}/weather`);
        const json = await res.json();
        if (!json.success) throw new Error(json.error || 'Failed to load locations');
        const rows = (json.data || []).slice().sort((a, b) => String(a.region_name || '').localeCompare(String(b.region_name || '')));
        regionEl.innerHTML = rows.map((r) => `<option value="${escapeHtml(r.region_id)}">${escapeHtml(r.region_name)}</option>`).join('');
        if (!regionEl.value && rows.length) regionEl.value = String(rows[0].region_id);
    }

    function todayIso() {
        const d = new Date();
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const dd = String(d.getDate()).padStart(2, '0');
        return `${d.getFullYear()}-${mm}-${dd}`;
    }

    async function loadOutlook() {
        statusEl.textContent = 'Loading…';
        messageEl.textContent = '';
        actionsEl.innerHTML = '';
        try {
            const regionId = regionEl.value;
            const date = dateEl.value || todayIso();
            const days = daysEl.value || '7';
            const method = methodEl.value || 'naive';

            const url = `${API_BASE}/risk/outlook?region_id=${encodeURIComponent(regionId)}&date=${encodeURIComponent(date)}&days=${encodeURIComponent(days)}&method=${encodeURIComponent(method)}`;
            const res = await fetch(url);
            const json = await res.json();
            if (!json.success) throw new Error(json.message || json.error || 'Failed to load outlook');

            const rows = json.outlook || [];
            const worst = json.worst_day || {};
            summaryEl.textContent = `Worst day: ${worst.date || ''} • ${String(worst.risk_level || '').toUpperCase()} • ${worst.disaster_type || ''}`;

            if (rows.length) {
                setRiskPill(rows[0].risk_level);
                messageEl.textContent = rows[0].message || '';
                renderActions(rows[0].actions || rows[0].recommendations || []);
            } else {
                setRiskPill('low');
            }

            renderTable(rows);
            const est = json.estimated ? ` • Estimated (${json.estimate_source || 'national'})` : '';
            statusEl.textContent = `Updated ${new Date().toLocaleTimeString()}${est}`;
        } catch (e) {
            console.error(e);
            statusEl.textContent = 'Failed';
            tableBody.innerHTML = `<tr><td colspan="7" class="mono">Error: ${escapeHtml(e.message || String(e))}</td></tr>`;
        }
    }

    function attachLogout() {
        const logoutLink = document.getElementById('logout-link');
        if (!logoutLink) return;
        logoutLink.addEventListener('click', (e) => {
            e.preventDefault();
            try { window.localStorage.removeItem('userSession'); } catch (_) {}
            try { window.sessionStorage.removeItem('adminToken'); window.sessionStorage.removeItem('adminUser'); } catch (_) {}
            window.location.href = 'home.html';
        });
    }

    document.getElementById('predict-btn').addEventListener('click', loadOutlook);
    document.getElementById('refresh-btn').addEventListener('click', loadOutlook);
    document.getElementById('download-btn').addEventListener('click', () => {
        window.location.href = `${API_BASE}/risk/export?format=csv`;
    });

    attachLogout();
    (async () => {
        try {
            await loadRegions();
            dateEl.value = todayIso();
            await loadOutlook();
        } catch (e) {
            console.error(e);
            statusEl.textContent = 'Failed to initialize';
        }
    })();
    setInterval(loadOutlook, 60000);
})();
