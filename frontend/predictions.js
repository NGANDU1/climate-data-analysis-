/**
 * FloodGuard-style Predictions page
 * Uses:
 *  - GET /api/weather (regions)
 *  - GET /api/risk/outlook (region + date + horizon)
 *  - GET /api/alerts (active watch count, best-effort)
 *  - GET /api/risk/export?format=csv (export)
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

  const el = (id) => document.getElementById(id);

  const statusEl = el('status');
  const summaryEl = el('summary');
  const messageEl = el('message');
  const actionsEl = el('actions');
  const tableBody = el('table-body');

  const regionEl = el('region');
  const dateEl = el('date');
  const daysEl = el('days'); // hidden select (kept for compatibility)
  const methodEl = el('method');

  // FloodGuard UI elements
  const fgSearchEl = el('fg-search');
  const fgLocationEl = el('fg-location-display');
  const fgDateEl = el('fg-date-display');
  const fgTimeEl = el('fg-time-display');
  const fgAlertCountEl = el('fg-alert-count');
  const fgRiskLevelEl = el('fg-risk-level');
  const fgRiskTextEl = el('fg-risk-text');
  const fgRain24El = el('fg-rain-24h');
  const fgConfidenceEl = el('fg-confidence');
  const fgTempEl = el('fg-temp');
  const fgHumEl = el('fg-hum');
  const fgOutlookListEl = el('fg-outlook-list');
  const daysRangeEl = el('days-range');
  const daysPillEl = el('days-pill');
  const exportPdfBtn = el('export-pdf-btn');

  const riskChartCanvas = el('fg-risk-chart');
  const rainChartCanvas = el('fg-rain-chart');
  const heatChartCanvas = el('fg-heat-chart');

  let regions = [];
  let riskChart = null;
  let rainChart = null;
  let heatChart = null;

  function escapeHtml(s) {
    return String(s ?? '').replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
  }

  function fmtNum(v, suffix = '') {
    if (v === null || v === undefined || Number.isNaN(Number(v))) return '—';
    return `${Number(v).toFixed(1)}${suffix}`;
  }

  function todayIso() {
    const d = new Date();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return `${d.getFullYear()}-${mm}-${dd}`;
  }

  function todayPretty() {
    try {
      return new Intl.DateTimeFormat(navigator.language || 'en-GB', { month: 'long', day: 'numeric', year: 'numeric' }).format(new Date());
    } catch (_) {
      return new Date().toDateString();
    }
  }

  function updateClock() {
    if (!fgTimeEl) return;
    try {
      fgTimeEl.textContent = new Intl.DateTimeFormat(navigator.language || 'en-GB', { hour: '2-digit', minute: '2-digit' }).format(new Date());
    } catch (_) {
      fgTimeEl.textContent = new Date().toLocaleTimeString();
    }
  }

  function setFloodRisk(level) {
    if (!fgRiskLevelEl) return;
    const cls = String(level || 'low').toLowerCase();
    fgRiskLevelEl.className = `fg-risk-level ${escapeHtml(cls)}`;
    fgRiskLevelEl.textContent = String(level || 'low').toUpperCase();
  }

  function riskProb(level, confidence) {
    const lvl = String(level || 'low').toLowerCase();
    const base = { low: 0.15, medium: 0.35, high: 0.60, critical: 0.85 }[lvl] ?? 0.15;
    const c = Number(confidence);
    const conf = Number.isFinite(c) ? Math.max(0.35, Math.min(0.95, c)) : 0.6;
    return Math.max(0.05, Math.min(0.98, base * (0.75 + conf * 0.35)));
  }

  function dayIcon(level) {
    const lvl = String(level || 'low').toLowerCase();
    if (lvl === 'critical') return '⛈️';
    if (lvl === 'high') return '🌧️';
    if (lvl === 'medium') return '🌦️';
    return '☁️';
  }

  function isoToShort(iso) {
    const d = new Date(String(iso || ''));
    if (Number.isNaN(d.getTime())) return String(iso || '');
    try {
      return new Intl.DateTimeFormat(navigator.language || 'en-GB', { month: 'short', day: 'numeric' }).format(d);
    } catch (_) {
      return d.toISOString().slice(5, 10);
    }
  }

  function renderActions(items) {
    if (!actionsEl) return;
    const list = Array.isArray(items) ? items : [];
    actionsEl.innerHTML = list.length ? list.map((x) => `<li>${escapeHtml(x)}</li>`).join('') : '';
  }

  function renderTable(rows) {
    if (!tableBody) return;
    const list = Array.isArray(rows) ? rows : [];
    if (!list.length) {
      tableBody.innerHTML = '<tr><td colspan="7" class="mono">No predictions found.</td></tr>';
      return;
    }
    tableBody.innerHTML = list.map((r) => {
      const cc = r.predicted_conditions || {};
      const lvl = String(r.risk_level || 'low').toLowerCase();
      return `
        <tr>
          <td class="mono">${escapeHtml(r.date || '')}</td>
          <td><span class="risk-badge ${escapeHtml(lvl)}">${escapeHtml(String(r.risk_level || 'low').toUpperCase())}</span></td>
          <td>${escapeHtml(r.message || '')}</td>
          <td>${escapeHtml(fmtNum(r.confidence_score, ''))}</td>
          <td>${escapeHtml(fmtNum(cc.temperature, '°C'))}</td>
          <td>${escapeHtml(fmtNum(cc.humidity, '%'))}</td>
          <td>${escapeHtml(fmtNum(cc.rainfall, 'mm'))}</td>
        </tr>
      `;
    }).join('');
  }

  function ensureCharts(labels, probs, rainMm) {
    if (typeof window.Chart === 'undefined') return;

    const commonOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: 'rgba(255,255,255,0.55)', font: { size: 11, weight: '700' } }, grid: { color: 'rgba(255,255,255,0.06)' } },
        y: { ticks: { color: 'rgba(255,255,255,0.55)', font: { size: 11, weight: '700' } }, grid: { color: 'rgba(255,255,255,0.06)' } }
      }
    };

    const points = probs.map((p) => Math.round(p * 100));

    if (riskChartCanvas) {
      const ctx = riskChartCanvas.getContext('2d');
      if (!riskChart) {
        riskChart = new window.Chart(ctx, {
          type: 'line',
          data: { labels, datasets: [{ data: points, borderColor: 'rgba(24,211,159,0.95)', backgroundColor: 'rgba(24,211,159,0.14)', tension: 0.35, fill: true, pointRadius: 3 }] },
          options: { ...commonOptions, scales: { ...commonOptions.scales, y: { ...commonOptions.scales.y, suggestedMin: 0, suggestedMax: 100 } } }
        });
      } else {
        riskChart.data.labels = labels;
        riskChart.data.datasets[0].data = points;
        riskChart.update();
      }
    }

    if (rainChartCanvas) {
      const ctx = rainChartCanvas.getContext('2d');
      if (!rainChart) {
        rainChart = new window.Chart(ctx, {
          type: 'bar',
          data: { labels, datasets: [{ data: rainMm, backgroundColor: 'rgba(14,165,233,0.35)', borderColor: 'rgba(14,165,233,0.85)', borderWidth: 1, borderRadius: 8 }] },
          options: { ...commonOptions, scales: { ...commonOptions.scales, y: { ...commonOptions.scales.y, suggestedMin: 0 } } }
        });
      } else {
        rainChart.data.labels = labels;
        rainChart.data.datasets[0].data = rainMm;
        rainChart.update();
      }
    }

    if (heatChartCanvas) {
      const ctx = heatChartCanvas.getContext('2d');
      const colors = probs.map((p) => {
        const v = Math.round(p * 100);
        if (v >= 80) return 'rgba(239,68,68,0.75)';
        if (v >= 60) return 'rgba(251,146,60,0.70)';
        if (v >= 35) return 'rgba(245,158,11,0.65)';
        return 'rgba(34,197,94,0.60)';
      });
      if (!heatChart) {
        heatChart = new window.Chart(ctx, {
          type: 'bar',
          data: { labels, datasets: [{ data: points, backgroundColor: colors, borderRadius: 10 }] },
          options: { ...commonOptions, scales: { ...commonOptions.scales, y: { ...commonOptions.scales.y, suggestedMin: 0, suggestedMax: 100 } } }
        });
      } else {
        heatChart.data.labels = labels;
        heatChart.data.datasets[0].data = points;
        heatChart.data.datasets[0].backgroundColor = colors;
        heatChart.update();
      }
    }
  }

  function renderOutlookList(rows) {
    if (!fgOutlookListEl) return;
    const list = Array.isArray(rows) ? rows : [];
    if (!list.length) {
      fgOutlookListEl.innerHTML = '<div class="mono">No outlook available.</div>';
      return;
    }

    fgOutlookListEl.innerHTML = list.map((r, idx) => {
      const cc = r.predicted_conditions || {};
      const lvl = String(r.risk_level || 'low').toLowerCase();
      const p = Math.round(riskProb(lvl, r.confidence_score) * 100);
      return `
        <div class="fg-day ${idx === 0 ? 'active' : ''}" data-idx="${idx}">
          <div>
            <div class="fg-day-date">${escapeHtml(isoToShort(r.date))}</div>
            <div class="fg-day-sub">${escapeHtml(String(r.disaster_type || '').replace('_', ' '))}</div>
          </div>
          <div class="fg-day-metrics">
            <span><strong>${escapeHtml(String(lvl).toUpperCase())}</strong> • ${p}%</span>
            <span>🌧️ ${escapeHtml(fmtNum(cc.rainfall, 'mm'))}</span>
            <span>🌡️ ${escapeHtml(fmtNum(cc.temperature, '°C'))}</span>
            <span>💧 ${escapeHtml(fmtNum(cc.humidity, '%'))}</span>
          </div>
          <div class="fg-ico" aria-hidden="true">${dayIcon(lvl)}</div>
        </div>
      `;
    }).join('');

    const selectRow = (idx) => {
      const r = list[idx];
      if (!r) return;
      const cc = r.predicted_conditions || {};

      setFloodRisk(r.risk_level);
      if (fgRiskTextEl) fgRiskTextEl.textContent = r.message || '';
      if (fgRain24El) fgRain24El.textContent = fmtNum(cc.rainfall, 'mm');
      if (fgTempEl) fgTempEl.textContent = fmtNum(cc.temperature, '°C');
      if (fgHumEl) fgHumEl.textContent = fmtNum(cc.humidity, '%');
      if (fgConfidenceEl) fgConfidenceEl.textContent = fmtNum(r.confidence_score, '');

      if (messageEl) messageEl.textContent = r.message || '';
      renderActions(r.actions || r.recommendations || []);
    };

    fgOutlookListEl.querySelectorAll('.fg-day').forEach((node) => {
      node.addEventListener('click', () => {
        fgOutlookListEl.querySelectorAll('.fg-day').forEach((x) => x.classList.remove('active'));
        node.classList.add('active');
        selectRow(Number(node.getAttribute('data-idx') || 0));
      });
    });

    selectRow(0);
  }

  async function loadActiveAlertsCount() {
    if (!fgAlertCountEl) return;
    try {
      const res = await fetch(`${API_BASE}/alerts`);
      const json = await res.json();
      if (!json.success) throw new Error(json.error || 'alerts');
      const items = Array.isArray(json.data) ? json.data : [];
      fgAlertCountEl.textContent = String(items.length);
    } catch (_) {
      fgAlertCountEl.textContent = '—';
    }
  }

  async function loadRegions() {
    const res = await fetch(`${API_BASE}/weather`);
    const json = await res.json();
    if (!json.success) throw new Error(json.error || 'Failed to load locations');
    regions = (json.data || []).slice().sort((a, b) => String(a.region_name || '').localeCompare(String(b.region_name || '')));

    if (regionEl) {
      regionEl.innerHTML = regions.map((r) => `<option value="${escapeHtml(r.region_id)}">${escapeHtml(r.region_name)}</option>`).join('');
      if (!regionEl.value && regions.length) regionEl.value = String(regions[0].region_id);
      const selected = regions.find((r) => String(r.region_id) === String(regionEl.value));
      if (fgLocationEl) fgLocationEl.textContent = selected?.region_name ? `${selected.region_name}, Zambia` : 'Zambia';
    }
  }

  async function loadOutlook() {
    if (statusEl) statusEl.textContent = 'Loading…';
    if (messageEl) messageEl.textContent = '';
    if (actionsEl) actionsEl.innerHTML = '';

    try {
      const regionId = regionEl ? regionEl.value : '';
      const date = (dateEl && dateEl.value) ? dateEl.value : todayIso();
      const days = (daysRangeEl && daysRangeEl.value) ? String(daysRangeEl.value) : ((daysEl && daysEl.value) ? daysEl.value : '14');
      const method = (methodEl && methodEl.value) ? methodEl.value : 'naive';

      const url = `${API_BASE}/risk/outlook?region_id=${encodeURIComponent(regionId)}&date=${encodeURIComponent(date)}&days=${encodeURIComponent(days)}&method=${encodeURIComponent(method)}`;
      const res = await fetch(url);
      const json = await res.json();
      if (!json.success) throw new Error(json.message || json.error || 'Failed to load outlook');

      const rows = json.outlook || [];
      const worst = json.worst_day || {};
      if (summaryEl) summaryEl.textContent = `Worst day: ${worst.date || ''} • ${String(worst.risk_level || '').toUpperCase()} • ${worst.disaster_type || ''}`;

      renderOutlookList(rows);
      renderTable(rows);

      // charts
      const labels = rows.map((r) => isoToShort(r.date));
      const probs = rows.map((r) => riskProb(r.risk_level, r.confidence_score));
      const rainMm = rows.map((r) => Number((r && r.predicted_conditions && r.predicted_conditions.rainfall) || 0));
      ensureCharts(labels, probs, rainMm);

      const est = json.estimated ? ` • Estimated (${json.estimate_source || 'national'})` : '';
      if (statusEl) statusEl.textContent = `Updated ${new Date().toLocaleTimeString()}${est}`;
    } catch (e) {
      console.error(e);
      if (statusEl) statusEl.textContent = 'Failed';
      if (tableBody) tableBody.innerHTML = `<tr><td colspan="7" class="mono">Error: ${escapeHtml(e.message || String(e))}</td></tr>`;
      if (fgRiskTextEl) fgRiskTextEl.textContent = 'Failed to load outlook.';
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

  function wireEvents() {
    const predictBtn = el('predict-btn');
    const refreshBtn = el('refresh-btn');
    const downloadBtn = el('download-btn');
    if (predictBtn) predictBtn.addEventListener('click', loadOutlook);
    if (refreshBtn) refreshBtn.addEventListener('click', loadOutlook);
    if (downloadBtn) downloadBtn.addEventListener('click', () => {
      window.location.href = `${API_BASE}/risk/export?format=csv`;
    });
    if (exportPdfBtn) exportPdfBtn.addEventListener('click', () => window.print());

    if (daysRangeEl && daysPillEl && daysEl) {
      daysEl.innerHTML = '';
      for (let i = 1; i <= 14; i += 1) {
        const opt = document.createElement('option');
        opt.value = String(i);
        opt.textContent = String(i);
        daysEl.appendChild(opt);
      }

      const sync = () => {
        const v = String(daysRangeEl.value || '14');
        daysPillEl.textContent = v;
        daysEl.value = v;
      };
      daysRangeEl.addEventListener('input', sync);
      sync();
    }

    if (regionEl && fgLocationEl) {
      regionEl.addEventListener('change', () => {
        const selected = regions.find((r) => String(r.region_id) === String(regionEl.value));
        fgLocationEl.textContent = selected?.region_name ? `${selected.region_name}, Zambia` : 'Zambia';
      });
    }

    if (fgSearchEl && regionEl) {
      fgSearchEl.addEventListener('input', () => {
        const q = String(fgSearchEl.value || '').trim().toLowerCase();
        if (!q) return;
        const match = regions.find((r) => String(r.region_name || '').toLowerCase().includes(q));
        if (match) {
          regionEl.value = String(match.region_id);
          if (fgLocationEl) fgLocationEl.textContent = `${match.region_name}, Zambia`;
          loadOutlook();
        }
      });
    }
  }

  (async () => {
    try {
      attachLogout();
      wireEvents();

      if (dateEl) dateEl.value = todayIso();
      if (fgDateEl) fgDateEl.textContent = todayPretty();
      updateClock();
      setInterval(updateClock, 15000);

      await loadRegions();
      await loadActiveAlertsCount();
      setInterval(loadActiveAlertsCount, 60000);

      await loadOutlook();
    } catch (e) {
      console.error(e);
      if (statusEl) statusEl.textContent = 'Failed to initialize';
    }
  })();

  setInterval(loadOutlook, 60000);
})();
