/**
 * Predictions page script
 * Uses /api/risk/predict and /api/risk/export
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
    const tableBody = document.getElementById('table-body');
    const searchEl = document.getElementById('search');
    const riskEl = document.getElementById('risk');
    const sortEl = document.getElementById('sort');

    const severityRank = { critical: 4, high: 3, medium: 2, low: 1 };

    let allPredictions = [];
    let chart = null;

    function escapeHtml(s) {
        return String(s ?? '').replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
    }

    function riskBadge(level) {
        const cls = (level || 'low').toLowerCase();
        return `<span class="risk-badge ${escapeHtml(cls)}">${escapeHtml(cls)}</span>`;
    }

    function fmtNum(v, suffix = '') {
        if (v === null || v === undefined || Number.isNaN(Number(v))) return '—';
        return `${Number(v).toFixed(1)}${suffix}`;
    }

    function updateSummary(summary) {
        if (!summary) { summaryEl.textContent = ''; return; }
        summaryEl.textContent =
            `Overall: ${summary.overall_risk_level} • ` +
            `Critical: ${summary.critical_regions} • High: ${summary.high_risk_regions} • ` +
            `Medium: ${summary.medium_risk_regions} • Low: ${summary.low_risk_regions}`;
    }

    function renderTable(rows) {
        if (!rows.length) {
            tableBody.innerHTML = '<tr><td colspan="7" class="mono">No predictions found.</td></tr>';
            return;
        }
        tableBody.innerHTML = rows.map((p) => {
            const cc = p.current_conditions || {};
            return `
                <tr>
                    <td>${escapeHtml(p.region_name || '')}</td>
                    <td>${riskBadge(p.risk_level)}</td>
                    <td>${escapeHtml(p.disaster_type || '')}</td>
                    <td>${fmtNum(p.confidence_score, '')}</td>
                    <td>${fmtNum(cc.temperature, '°C')}</td>
                    <td>${fmtNum(cc.humidity, '%')}</td>
                    <td>${fmtNum(cc.rainfall, 'mm')}</td>
                </tr>
            `;
        }).join('');
    }

    function renderChart(rows) {
        const counts = { low: 0, medium: 0, high: 0, critical: 0 };
        for (const r of rows) {
            const k = (r.risk_level || 'low').toLowerCase();
            if (k in counts) counts[k] += 1;
        }

        const ctx = document.getElementById('riskChart').getContext('2d');
        const data = [counts.low, counts.medium, counts.high, counts.critical];

        if (chart) chart.destroy();
        chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Low', 'Medium', 'High', 'Critical'],
                datasets: [{
                    data,
                    backgroundColor: ['#10b981', '#34d399', '#f97316', '#dc2626'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '62%',
                plugins: { legend: { position: 'bottom' } }
            }
        });

        document.getElementById('chart-note').textContent = `Total regions with predictions: ${rows.length}`;
    }

    function applyFilters() {
        const q = (searchEl.value || '').trim().toLowerCase();
        const risk = (riskEl.value || '').trim().toLowerCase();
        const sort = (sortEl.value || 'severity').trim().toLowerCase();

        let rows = allPredictions.slice();
        if (q) rows = rows.filter((p) => String(p.region_name || '').toLowerCase().includes(q));
        if (risk) rows = rows.filter((p) => String(p.risk_level || '').toLowerCase() === risk);

        if (sort === 'name') {
            rows.sort((a, b) => String(a.region_name || '').localeCompare(String(b.region_name || '')));
        } else if (sort === 'confidence') {
            rows.sort((a, b) => Number(b.confidence_score || 0) - Number(a.confidence_score || 0));
        } else {
            rows.sort((a, b) => (severityRank[b.risk_level] || 0) - (severityRank[a.risk_level] || 0));
        }

        renderTable(rows);
        renderChart(rows);
    }

    async function loadPredictions() {
        statusEl.textContent = 'Loading…';
        try {
            const res = await fetch(`${API_BASE}/risk/predict`);
            const json = await res.json();
            if (!json.success) throw new Error(json.error || 'Failed to load predictions');

            allPredictions = json.predictions || [];
            updateSummary(json.summary);
            applyFilters();

            statusEl.textContent = `Loaded ${allPredictions.length}`;
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

    document.getElementById('apply-btn').addEventListener('click', applyFilters);
    document.getElementById('refresh-btn').addEventListener('click', loadPredictions);
    document.getElementById('download-btn').addEventListener('click', () => {
        window.location.href = `${API_BASE}/risk/export?format=csv`;
    });

    attachLogout();
    loadPredictions();
    setInterval(loadPredictions, 60000);
})();

