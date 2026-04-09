(() => {
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

  const state = {
    regions: [],
    selectedRegionId: null,
    chart: null,
    externalDaily: null,
    selectedDate: null,
    floodOutlook: null,
    weatherTimer: null,
    externalTimer: null,
    lastExternalRefreshAt: 0
  };

  const forecastTitleEl = $('wa-forecast-title');
  const rainTitleEl = $('wa-rain-title');
  const DEG = '\u00B0';
  const DASH = '\u2014';

  function $(id) {
    return document.getElementById(id);
  }

  function setText(id, value) {
    const el = $(id);
    if (!el) return;
    el.textContent = value;
  }

  function formatC(value, digits = 1) {
    const n = Number(value);
    if (!Number.isFinite(n)) return DASH;
    return `${n.toFixed(digits)}${DEG}C`;
  }

  function initLogout() {
    const logoutLink = $('logout-link');
    if (!logoutLink) return;
    logoutLink.addEventListener('click', (e) => {
      e.preventDefault();
      try {
        window.localStorage.removeItem('userSession');
      } catch (_) {}
      window.location.href = 'home.html';
    });
  }

  function renderAqiRing(aqi) {
    const c = $('wa-aqi-progress');
    if (!c) return;

    // Circumference in CSS uses 289 (approx for r=46)
    const circumference = 289;
    const clamped = Math.max(0, Math.min(500, Number(aqi) || 0));
    const pct = Math.max(0, Math.min(1, clamped / 100));
    const dashOffset = Math.round(circumference * (1 - pct));
    c.style.strokeDashoffset = String(dashOffset);
  }

  function renderForecastAxes(chart) {
    if (!chart) return;
    // Ensure axis titles exist (Chart.js v4)
    chart.options.scales = chart.options.scales || {};
    chart.options.scales.x = chart.options.scales.x || {};
    chart.options.scales.y = chart.options.scales.y || {};
    chart.options.scales.x.title = { display: true, text: 'Date', color: 'rgba(255,255,255,0.60)', font: { weight: '700', size: 12 } };
    chart.options.scales.y.title = { display: true, text: `Temperature (${DEG}C)`, color: 'rgba(255,255,255,0.60)', font: { weight: '700', size: 12 } };
    chart.options.scales.y.ticks = chart.options.scales.y.ticks || {};
    chart.options.scales.y.ticks.callback = (v) => `${v}${DEG}C`;
  }

  function styleForecastChart(chart) {
    if (!chart) return;
    chart.options = chart.options || {};
    chart.options.scales = chart.options.scales || {};
    chart.options.scales.x = chart.options.scales.x || {};
    chart.options.scales.y = chart.options.scales.y || {};

    chart.options.scales.x.title = chart.options.scales.x.title || {};
    chart.options.scales.x.title.display = true;
    chart.options.scales.x.title.text = 'Date';
    chart.options.scales.x.title.color = 'rgba(255,255,255,0.60)';
    chart.options.scales.x.title.font = { weight: '700', size: 12 };

    chart.options.scales.y.title = chart.options.scales.y.title || {};
    chart.options.scales.y.title.display = true;
    chart.options.scales.y.title.text = `Temperature (${DEG}C)`;
    chart.options.scales.y.title.color = 'rgba(255,255,255,0.60)';
    chart.options.scales.y.title.font = { weight: '700', size: 12 };

    chart.options.scales.y.ticks = chart.options.scales.y.ticks || {};
    chart.options.scales.y.ticks.callback = (v) => `${v}${DEG}C`;

    chart.options.layout = chart.options.layout || {};
    chart.options.layout.padding = chart.options.layout.padding || { top: 8, right: 10, bottom: 18, left: 10 };
  }

  function renderRainList(rows) {
    const list = $('wa-rain-list');
    if (!list) return;
    list.innerHTML = '';

    (rows || []).forEach((r) => {
      const row = document.createElement('div');
      row.className = 'wa-rain-row';
      row.innerHTML = `
        <div class="wa-rain-day">${escapeHtml(r.day)}</div>
        <div class="wa-rain-bar"><span style="width:${Math.max(0, Math.min(100, Number(r.chance) || 0))}%;"></span></div>
      `;
      list.appendChild(row);
    });
  }

  function escapeHtml(text) {
    return (text || '').toString()
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function initCityTabs() {
    const tabs = Array.from(document.querySelectorAll('.wa-city-tab'));
    if (tabs.length === 0) return;

    tabs.forEach((tab) => {
      tab.addEventListener('click', () => {
        const regionId = Number(tab.dataset.regionId);
        if (!Number.isFinite(regionId)) return;
        setRegion(regionId);
      });
    });
  }

  function getSelectedRegion() {
    return state.regions.find((r) => r.region_id === state.selectedRegionId) || null;
  }

  function deriveCondition(region) {
    const rainfall = Number.parseFloat(region?.rainfall);
    const humidity = Number.parseFloat(region?.humidity);

    if (Number.isFinite(rainfall) && rainfall >= 12) return { label: 'Storm with Rain', icon: '\u26C8\uFE0F' }; // ⛈️
    if (Number.isFinite(rainfall) && rainfall >= 2) return { label: 'Rain', icon: '\uD83C\uDF27\uFE0F' }; // 🌧️
    if (Number.isFinite(humidity) && humidity >= 78) return { label: 'Cloudy', icon: '\u2601\uFE0F' }; // ☁️
    return { label: 'Sunny', icon: '\u2600\uFE0F' }; // ☀️
  }

  function formatUpdated(date) {
    try {
      return new Intl.DateTimeFormat(navigator.language || 'en-GB', { day: '2-digit', month: 'short' }).format(date);
    } catch (_) {
      return date.toDateString();
    }
  }

  function formatUpdatedWithTime(date) {
    try {
      return new Intl.DateTimeFormat(navigator.language || 'en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }).format(date);
    } catch (_) {
      return date.toLocaleString();
    }
  }

  function formatTime(d) {
    if (!d || typeof d.getTime !== 'function' || Number.isNaN(d.getTime())) return DASH;
    try {
      return new Intl.DateTimeFormat(navigator.language || 'en-GB', { hour: '2-digit', minute: '2-digit' }).format(d);
    } catch (_) {
      return d.toTimeString().slice(0, 5);
    }
  }

  // NOAA-style sunrise/sunset approximation.
  function calcSunTimes(date, latitude, longitude) {
    const rad = Math.PI / 180;
    const day = new Date(date.getFullYear(), date.getMonth(), date.getDate());

    const N1 = Math.floor(275 * (day.getMonth() + 1) / 9);
    const N2 = Math.floor((day.getMonth() + 1 + 9) / 12);
    const N3 = (1 + Math.floor((day.getFullYear() - 4 * Math.floor(day.getFullYear() / 4) + 2) / 3));
    const N = N1 - (N2 * N3) + day.getDate() - 30;

    const lngHour = longitude / 15;
    const zenith = 90.833; // official

    function calc(isSunrise) {
      const t = N + ((isSunrise ? 6 : 18) - lngHour) / 24;
      const M = (0.9856 * t) - 3.289;
      let L = M + (1.916 * Math.sin(M * rad)) + (0.020 * Math.sin(2 * M * rad)) + 282.634;
      L = (L + 360) % 360;
      let RA = Math.atan(0.91764 * Math.tan(L * rad)) / rad;
      RA = (RA + 360) % 360;

      const Lquadrant = Math.floor(L / 90) * 90;
      const RAquadrant = Math.floor(RA / 90) * 90;
      RA = RA + (Lquadrant - RAquadrant);
      RA = RA / 15;

      const sinDec = 0.39782 * Math.sin(L * rad);
      const cosDec = Math.cos(Math.asin(sinDec));

      const cosH = (Math.cos(zenith * rad) - (sinDec * Math.sin(latitude * rad))) / (cosDec * Math.cos(latitude * rad));
      if (cosH > 1 || cosH < -1) return null;

      let H = isSunrise ? (360 - (Math.acos(cosH) / rad)) : (Math.acos(cosH) / rad);
      H = H / 15;

      const T = H + RA - (0.06571 * t) - 6.622;
      let UT = (T - lngHour) % 24;
      if (UT < 0) UT += 24;

      const local = new Date(Date.UTC(day.getFullYear(), day.getMonth(), day.getDate(), 0, 0, 0));
      local.setUTCHours(0, 0, 0, 0);
      local.setUTCMinutes(0);
      const ms = UT * 60 * 60 * 1000;

      // Convert "UTC hours" to a Date; then let browser display local time.
      return new Date(local.getTime() + ms);
    }

    return { sunrise: calc(true), sunset: calc(false) };
  }

  function aqiToReplica(aqi) {
    const n = Number(aqi);
    if (!Number.isFinite(n) || n < 1) return { label: 'No data', value: null, pct: 0 };
    // OpenWeather AQI is 1..5. Map to a 0..100-ish replica score.
    const map = {
      1: { label: 'Good', value: 25, pct: 0.25 },
      2: { label: 'Fair', value: 40, pct: 0.40 },
      3: { label: 'Moderate', value: 55, pct: 0.55 },
      4: { label: 'Poor', value: 75, pct: 0.75 },
      5: { label: 'Very Poor', value: 95, pct: 0.95 }
    };
    return map[n] || { label: 'No data', value: null, pct: 0 };
  }

  function setPollutantValues(components) {
    const c = components || {};
    const lookup = {
      PM10: c.pm10,
      O3: c.o3,
      SO2: c.so2,
      'PM2.5': c.pm2_5,
      CO: c.co,
      NO2: c.no2
    };

    const rows = Array.from(document.querySelectorAll('.wa-pol'));
    rows.forEach((row) => {
      const labelEl = row.querySelector('.wa-pol-label');
      const valueEl = row.querySelector('.wa-pol-value');
      if (!labelEl || !valueEl) return;
      const key = labelEl.textContent.trim();
      const v = lookup[key];
      valueEl.textContent = Number.isFinite(Number(v)) ? String(Math.round(Number(v))) : DASH;
    });
  }

  async function loadExternal(regionId, region) {
    try {
      const [w, aq] = await Promise.allSettled([
        apiGetJson(`/external/weather?region_id=${encodeURIComponent(regionId)}`),
        apiGetJson(`/external/uv?region_id=${encodeURIComponent(regionId)}`)
      ]);

      if (w.status === 'fulfilled') {
        const sunriseUtc = w.value?.data?.sunrise_utc;
        const sunsetUtc = w.value?.data?.sunset_utc;
        const visibilityM = w.value?.data?.visibility_m;
        const uviMax = w.value?.data?.uvi_max;

        if (sunriseUtc) setText('wa-sunrise', formatTime(new Date(sunriseUtc)));
        if (sunsetUtc) setText('wa-sunset', formatTime(new Date(sunsetUtc)));

        if (Number.isFinite(Number(visibilityM))) {
          setText('wa-visibility', `${(Number(visibilityM) / 1000).toFixed(1)} km`);
        }

        if (Number.isFinite(Number(uviMax))) {
          setText('wa-uv', String(Number(uviMax).toFixed(1)));
        }
      } else {
        // Fallback to computed sunrise/sunset if we have coords.
        if (region && Number.isFinite(region.latitude) && Number.isFinite(region.longitude)) {
          const sun = calcSunTimes(new Date(), Number(region.latitude), Number(region.longitude));
          setText('wa-sunrise', `${formatTime(sun.sunrise)} (approx)`);
          setText('wa-sunset', `${formatTime(sun.sunset)} (approx)`);
        }
      }

      if (aq.status === 'fulfilled') {
        const uvi = aq.value?.data?.uvi;
        if (Number.isFinite(Number(uvi))) {
          setText('wa-uv', String(Number(uvi).toFixed(1)));
        }
      }
    } catch (e) {
      console.error('External enrichment failed:', e);
    }
  }

  function renderCurrentRegion(region) {
    if (!region) return;

    setText('wa-location', region.region_name || DASH);
    setText('wa-temp', Number(region.temperature || 0).toFixed(1));
    const cond = deriveCondition(region);
    setText('wa-desc', cond.label);
    const iconEl = document.querySelector('.wa-main-icon');
    if (iconEl) iconEl.textContent = cond.icon;

    setText('wa-humidity', `${Math.round(Number(region.humidity || 0))}%`);
    setText('wa-wind', `${Number(region.wind_speed || 0).toFixed(1)} kph`);
    setText('wa-pressure', `${Math.round(Number(region.pressure || 0))} mb`);
    setText('wa-precip', `${Number(region.rainfall || 0).toFixed(2)} mm`);
  }

  function setRegion(regionId) {
    state.selectedRegionId = regionId;

    const tabs = Array.from(document.querySelectorAll('.wa-city-tab'));
    tabs.forEach((t) => {
      const id = Number(t.dataset.regionId);
      const isActive = id === regionId;
      t.classList.toggle('active', isActive);
      t.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });

    const region = getSelectedRegion();
    if (!region) return;

    setText('wa-location', region.region_name || DASH);
    setText('wa-temp', Number(region.temperature || 0).toFixed(1));
    const cond = deriveCondition(region);
    setText('wa-desc', cond.label);
    const iconEl = document.querySelector('.wa-main-icon');
    if (iconEl) iconEl.textContent = cond.icon;

    setText('wa-humidity', `${Math.round(Number(region.humidity || 0))}%`);
    setText('wa-wind', `${Number(region.wind_speed || 0).toFixed(1)} kph`);
    setText('wa-pressure', `${Math.round(Number(region.pressure || 0))} mb`);
    setText('wa-precip', `${Number(region.rainfall || 0).toFixed(2)} mm`);

    // UV isn't available from our internal weather model.
    setText('wa-uv', DASH);

    // External enrichment from the API (sunrise/sunset, visibility, UV, and optional OpenWeather forecast).
    setText('wa-visibility', DASH);
    setText('wa-sunrise', DASH);
    setText('wa-sunset', DASH);
    setText('wa-uv', DASH);

    // Flood card placeholders (reusing ring UI)
    setText('wa-aqi-value', DASH);
    setText('wa-aqi-label', 'Loading\u2026');
    renderAqiRing(0);
    setText('wa-flood-foot', 'Risk for selected date');
    setText('wa-flood-risk', DASH);
    setText('wa-flood-conf', DASH);
    setText('wa-flood-rain', DASH);
    setText('wa-flood-temp', DASH);
    setText('wa-flood-hum', DASH);
    setText('wa-flood-type', DASH);

    void loadExternal(regionId, region);

    // Refresh forecast visuals.
    void loadForecast(regionId);
    void loadFloodOutlook(regionId);
  }

  function initWeekCards() {
    const cards = Array.from(document.querySelectorAll('.wa-day-card'));
    if (cards.length === 0) return;
    cards.forEach((card) => {
      card.addEventListener('click', () => {
        cards.forEach((c) => c.classList.remove('active'));
        card.classList.add('active');
        const d = card.dataset.date;
        if (d) setSelectedDate(d);
      });
    });
  }

  function createForecastChart({ labels, temps }) {
    const canvas = $('wa-forecast-chart');
    if (!canvas || typeof window.Chart === 'undefined') return null;

    const ctx = canvas.getContext('2d');

    return new window.Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: `Temperature (${DEG}C)`,
          data: temps,
          borderColor: 'rgba(255, 138, 61, 0.95)',
          backgroundColor: 'rgba(255, 138, 61, 0.12)',
          pointBackgroundColor: 'rgba(255, 138, 61, 0.95)',
          pointBorderColor: 'rgba(0,0,0,0.0)',
          pointRadius: 4,
          pointHoverRadius: 6,
          tension: 0.35,
          fill: true
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: 'rgba(0,0,0,0.6)',
            borderColor: 'rgba(255,255,255,0.12)',
            borderWidth: 1,
            titleColor: 'rgba(255,255,255,0.9)',
            bodyColor: 'rgba(255,255,255,0.85)',
            displayColors: false
          }
        },
        scales: {
          x: {
            grid: { color: 'rgba(255,255,255,0.06)' },
            ticks: { color: 'rgba(255,255,255,0.55)', font: { size: 11, weight: '700' } },
            title: { display: true, text: 'Date', color: 'rgba(255,255,255,0.60)', font: { size: 12, weight: '700' } }
          },
          y: {
            suggestedMin: 26,
            suggestedMax: 29,
            grid: { color: 'rgba(255,255,255,0.06)' },
            ticks: { color: 'rgba(255,255,255,0.55)', font: { size: 11, weight: '700' }, callback: (v) => `${v}${DEG}C` },
            title: { display: true, text: `Temperature (${DEG}C)`, color: 'rgba(255,255,255,0.60)', font: { size: 12, weight: '700' } }
          }
        }
      }
    });
  }

  async function apiGetJson(path) {
    const res = await fetch(`${API_BASE}${path}`);
    const json = await res.json();
    if (!json || json.success === false) {
      throw new Error(json?.message || json?.error || 'Request failed');
    }
    return json;
  }

  function pickTopRegions(regions) {
    const byName = (name) => regions.find((r) => (r.region_name || '').toLowerCase() === name.toLowerCase());
    const preferred = ['Lusaka', 'Copperbelt', 'Central'];
    const picked = [];
    preferred.forEach((name) => {
      const r = byName(name);
      if (r) picked.push(r);
    });
    for (const r of regions) {
      if (picked.length >= 3) break;
      if (!picked.some((p) => p.region_id === r.region_id)) picked.push(r);
    }
    return picked.slice(0, 3);
  }

  function formatDayName(isoDate) {
    const d = new Date(isoDate);
    if (Number.isNaN(d.getTime())) return 'Day';
    try {
      return new Intl.DateTimeFormat(navigator.language || 'en-GB', { weekday: 'long' }).format(d);
    } catch (_) {
      return d.toDateString().split(' ')[0];
    }
  }

  function formatChartDayLabel(isoDate) {
    const d = new Date(isoDate);
    if (Number.isNaN(d.getTime())) return String(isoDate || '');
    try {
      return new Intl.DateTimeFormat(navigator.language || 'en-GB', { weekday: 'short', day: '2-digit' }).format(d);
    } catch (_) {
      return `${d.getMonth() + 1}/${d.getDate()}`;
    }
  }

  function iconForRain(mm) {
    const r = Number(mm);
    if (!Number.isFinite(r)) return '\u2601\uFE0F'; // ☁️
    if (r >= 10) return '\u26C8\uFE0F'; // ⛈️
    if (r >= 2) return '\uD83C\uDF27\uFE0F'; // 🌧️
    return '\u2601\uFE0F'; // ☁️
  }

  function renderWeekCards(days, tempForecast, rainForecast) {
    const cards = Array.from(document.querySelectorAll('.wa-day-card'));
    if (cards.length === 0) return;

    for (let i = 0; i < cards.length; i += 1) {
      const card = cards[i];
      const d = days[i];
      const t = tempForecast?.[i]?.value;
      const r = rainForecast?.[i]?.value;

      const iconEl = card.querySelector('.wa-day-icon');
      const nameEl = card.querySelector('.wa-day-name');
      const tempEl = card.querySelector('.wa-day-temp');
      if (iconEl) iconEl.textContent = iconForRain(r);
      if (nameEl) nameEl.textContent = d ? formatDayName(d) : DASH;
      if (tempEl) tempEl.textContent = Number.isFinite(Number(t)) ? formatC(t, 1) : DASH;
    }
  }

  function renderRainChances(forecast) {
    // Convert rainfall (mm) into a relative "chance" (0-100) for a replica UI.
    const rows = Array.isArray(forecast) ? forecast : [];
    const values = rows.map((r) => Number(r.value)).filter(Number.isFinite);
    const max = values.length ? Math.max(...values) : 0;
    const scale = max > 0 ? max : 1;

    const out = rows.map((r) => {
      const v = Number(r.value);
      const pct = Math.max(0, Math.min(100, Math.round((Number.isFinite(v) ? v : 0) / scale * 100)));
      return { day: formatDayName(r.date), chance: pct };
    });
    renderRainList(out);
  }

  async function loadForecast(regionId) {
    try {
      // Prefer accurate OpenWeather POP forecast when available (5 days).
      let daily = null;
      try {
        const ext = await apiGetJson(`/external/forecast?region_id=${encodeURIComponent(regionId)}&days=5`);
        daily = ext?.data?.daily || null;
      } catch (_) {}

      if (Array.isArray(daily) && daily.length) {
        state.externalDaily = daily;
        if (forecastTitleEl) forecastTitleEl.textContent = 'Weather Forecast';
        if (rainTitleEl) rainTitleEl.textContent = 'Chances of Rain';

        const labels = daily.map((d) => formatChartDayLabel(d.date));
        const temps = daily.map((d) => Number(d.temp_avg_c));
        const rainRows = daily.map((d) => ({ day: formatDayName(d.date), chance: Math.round(Math.max(0, Math.min(1, Number(d.pop_max) || 0)) * 100) }));
        renderRainList(rainRows);

        if (state.chart) {
          state.chart.data.labels = labels;
          state.chart.data.datasets[0].data = temps;
          styleForecastChart(state.chart);
          state.chart.update();
        } else {
          state.chart = createForecastChart({ labels, temps });
          styleForecastChart(state.chart);
          state.chart?.update?.();
        }

        // Make week cards clickable and tied to dates.
        const cards = Array.from(document.querySelectorAll('.wa-day-card'));
        cards.forEach((card, idx) => {
          const row = daily[idx];
          if (!row) {
            card.style.display = 'none';
            return;
          }
          card.style.display = '';
          card.dataset.date = row.date;
          const nameEl = card.querySelector('.wa-day-name');
          const tempEl = card.querySelector('.wa-day-temp');
          const iconEl = card.querySelector('.wa-day-icon');
          if (nameEl) nameEl.textContent = formatDayName(row.date);
          if (tempEl) tempEl.textContent = Number.isFinite(Number(row.temp_avg_c)) ? formatC(row.temp_avg_c, 1) : DASH;
          if (iconEl) iconEl.textContent = iconForRain(row.rain_mm_sum);
        });

        // Click behavior: update selected date details.
        document.querySelectorAll('.wa-day-card').forEach((card) => {
          card.onclick = () => {
            document.querySelectorAll('.wa-day-card').forEach((c) => c.classList.remove('active'));
            card.classList.add('active');
            const d = card.dataset.date;
            if (d) setSelectedDate(d);
          };
        });

        // Default selected date
        const first = daily[0]?.date;
        if (first) setSelectedDate(first);
        return;
      }

      // Fallback: use risk outlook (includes per-day predicted_conditions).
      if (forecastTitleEl) forecastTitleEl.textContent = 'Weather Forecast (estimated)';
      if (rainTitleEl) rainTitleEl.textContent = 'Chances of Rain (estimated)';

      const outlook = await apiGetJson(`/risk/outlook?region_id=${encodeURIComponent(regionId)}&days=7&method=arima`);
      const rows = outlook?.outlook || [];
      const days = rows.map((r) => r.date);

      const labels = days.map((d) => formatChartDayLabel(d));
      const temps = rows.map((r) => Number(r?.predicted_conditions?.temperature));
      const rainfall = rows.map((r) => Number(r?.predicted_conditions?.rainfall || 0));

      // Render week chips (7)
      const cards = Array.from(document.querySelectorAll('.wa-day-card'));
      cards.forEach((card, idx) => {
        const d = days[idx];
        const t = temps[idx];
        const r = rainfall[idx];
        if (!d) { card.style.display = 'none'; return; }
        card.style.display = '';
        card.dataset.date = d;
        const nameEl = card.querySelector('.wa-day-name');
        const tempEl = card.querySelector('.wa-day-temp');
        const iconEl = card.querySelector('.wa-day-icon');
        if (nameEl) nameEl.textContent = formatDayName(d);
        if (tempEl) tempEl.textContent = Number.isFinite(t) ? formatC(t, 1) : DASH;
        if (iconEl) iconEl.textContent = iconForRain(r);
      });

      document.querySelectorAll('.wa-day-card').forEach((card) => {
        card.onclick = () => {
          document.querySelectorAll('.wa-day-card').forEach((c) => c.classList.remove('active'));
          card.classList.add('active');
          const d = card.dataset.date;
          if (d) setSelectedDate(d);
        };
      });

      // Rain "chance" approximation from rainfall (mm/day): 0mm -> 0%, 12mm+ -> 100%
      const rainRows = rows.map((r) => {
        const mm = Number(r?.predicted_conditions?.rainfall || 0);
        const pct = Math.max(0, Math.min(100, Math.round((mm / 12) * 100)));
        return { day: formatDayName(r.date), chance: pct };
      });
      renderRainList(rainRows);

      state.externalDaily = rows.map((r, idx) => ({
        date: r.date,
        temp_avg_c: Number.isFinite(temps[idx]) ? temps[idx] : null,
        pop_max: null,
        rain_mm_sum: Number.isFinite(rainfall[idx]) ? rainfall[idx] : 0
      }));

      if (state.chart) {
        state.chart.data.labels = labels;
        state.chart.data.datasets[0].data = temps;
        styleForecastChart(state.chart);
        state.chart.update();
      } else {
        state.chart = createForecastChart({ labels, temps });
        styleForecastChart(state.chart);
        state.chart?.update?.();
      }

      const first = days[0];
      if (first) setSelectedDate(first);
    } catch (e) {
      // Keep UI intact even if forecast isn't available.
      console.error('Forecast load failed:', e);
      if (forecastTitleEl) forecastTitleEl.textContent = 'Weather Forecast (unavailable)';
      if (rainTitleEl) rainTitleEl.textContent = 'Chances of Rain (unavailable)';
    }
  }

  async function loadWeather() {
    const json = await apiGetJson('/weather');
    const regions = Array.isArray(json.data) ? json.data : [];
    state.regions = regions;

    const top = pickTopRegions(regions);
    const tabs = Array.from(document.querySelectorAll('.wa-city-tab'));
    for (let i = 0; i < tabs.length; i += 1) {
      const tab = tabs[i];
      const region = top[i];
      if (!region) {
        tab.style.display = 'none';
        continue;
      }
      tab.style.display = '';
      tab.dataset.regionId = String(region.region_id);
      tab.dataset.city = region.region_name || '';
      const nameEl = tab.querySelector('.wa-city-name');
      const tempEl = tab.querySelector('.wa-city-temp');
      if (nameEl) nameEl.textContent = region.region_name || DASH;
      if (tempEl) tempEl.textContent = formatC(region.temperature, 1);
    }

    if (!state.selectedRegionId && top[0]) {
      state.selectedRegionId = top[0].region_id;
    }
  }

  function toIsoDateLocal(date) {
    const d = new Date(date);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  function setSelectedDate(isoDate) {
    state.selectedDate = isoDate;
    updateSelectedDayUI();
  }

  function updateSelectedDayUI() {
    const region = getSelectedRegion();
    const daily = state.externalDaily;
    const selected = state.selectedDate;
    const today = toIsoDateLocal(new Date());

    if (Array.isArray(daily) && daily.length > 0 && selected) {
      const row = daily.find((d) => d.date === selected);
      if (row) {
        if (Number.isFinite(Number(row.temp_avg_c))) setText('wa-temp', Number(row.temp_avg_c).toFixed(1));
        setText('wa-precip', `${Number(row.rain_mm_sum || 0).toFixed(2)} mm`);

        const pop = Number(row.pop_max);
        const rainMm = Number(row.rain_mm_sum);
        if (Number.isFinite(pop)) {
          if (pop >= 0.7) setText('wa-desc', 'Rain likely');
          else if (pop >= 0.35) setText('wa-desc', 'Chance of rain');
          else setText('wa-desc', 'Low chance of rain');
        } else if (Number.isFinite(rainMm)) {
          if (rainMm >= 10) setText('wa-desc', 'Storm with rain');
          else if (rainMm >= 2) setText('wa-desc', 'Rain');
          else setText('wa-desc', 'Mostly dry');
        }

        const uviMax = Number(row.uvi_max);
        if (Number.isFinite(uviMax)) {
          setText('wa-uv', String(uviMax.toFixed(1)));
        } else if (selected !== today) {
          setText('wa-uv', DASH);
        }

        if (row.sunrise_utc && row.sunset_utc) {
          setText('wa-sunrise', formatTime(new Date(row.sunrise_utc)));
          setText('wa-sunset', formatTime(new Date(row.sunset_utc)));
        } else if (region && Number.isFinite(Number(region.latitude)) && Number.isFinite(Number(region.longitude))) {
          const sun = calcSunTimes(new Date(selected), Number(region.latitude), Number(region.longitude));
          setText('wa-sunrise', `${formatTime(sun.sunrise)} (approx)`);
          setText('wa-sunset', `${formatTime(sun.sunset)} (approx)`);
        }
      }
    } else if (region && Number.isFinite(Number(region.latitude)) && Number.isFinite(Number(region.longitude)) && selected) {
      const sun = calcSunTimes(new Date(selected), Number(region.latitude), Number(region.longitude));
      setText('wa-sunrise', `${formatTime(sun.sunrise)} (approx)`);
      setText('wa-sunset', `${formatTime(sun.sunset)} (approx)`);
    }

    if (state.floodOutlook && selected) {
      const r = state.floodOutlook.find((x) => x.date === selected);
      if (r) renderFloodRisk(r);
    }
  }

  function renderFloodRisk(row) {
    const lvl = String(row.risk_level || 'low').toLowerCase();
    const conf = Number(row.confidence_score);
    const cc = row.predicted_conditions || {};
    const riskPct = Math.round((() => {
      const base = { low: 0.15, medium: 0.35, high: 0.60, critical: 0.85 }[lvl] ?? 0.15;
      const c = Number.isFinite(conf) ? Math.max(0.35, Math.min(0.95, conf)) : 0.6;
      return Math.max(0.05, Math.min(0.98, base * (0.75 + c * 0.35)));
    })() * 100);

    setText('wa-aqi-label', lvl.charAt(0).toUpperCase() + lvl.slice(1));
    setText('wa-aqi-value', String(riskPct));
    renderAqiRing(riskPct);

    setText('wa-flood-risk', lvl.toUpperCase());
    setText('wa-flood-conf', Number.isFinite(conf) ? conf.toFixed(2) : DASH);
    setText('wa-flood-rain', Number.isFinite(Number(cc.rainfall)) ? `${Number(cc.rainfall).toFixed(1)}mm` : DASH);
    setText('wa-flood-temp', Number.isFinite(Number(cc.temperature)) ? `${Number(cc.temperature).toFixed(1)}${DEG}` : DASH);
    setText('wa-flood-hum', Number.isFinite(Number(cc.humidity)) ? `${Number(cc.humidity).toFixed(0)}%` : DASH);
    setText('wa-flood-type', String(row.disaster_type || DASH).replace('_', ' '));
  }

  async function loadFloodOutlook(regionId) {
    try {
      const res = await apiGetJson(`/risk/outlook?region_id=${encodeURIComponent(regionId)}&days=7&method=arima`);
      const rows = res.outlook || [];
      state.floodOutlook = rows;
      if (!state.selectedDate && rows.length) {
        state.selectedDate = rows[0].date;
      }
      if (state.selectedDate) {
        const row = rows.find((r) => r.date === state.selectedDate) || rows[0];
        if (row) renderFloodRisk(row);
      }
    } catch (e) {
      console.error('Flood outlook load failed:', e);
      setText('wa-aqi-label', 'No data');
      setText('wa-aqi-value', DASH);
      renderAqiRing(0);
    }
  }

  function clampNumber(value, min, max, fallback) {
    const n = Number(value);
    if (!Number.isFinite(n)) return fallback;
    return Math.max(min, Math.min(max, n));
  }

  function getLiveConfig() {
    const params = new URLSearchParams(window.location.search);
    const weatherSec = clampNumber(params.get('liveWeatherSec'), 5, 300, 30);
    const externalMin = clampNumber(params.get('liveExternalMin'), 1, 60, 10);
    return { weatherMs: Math.round(weatherSec * 1000), externalMs: Math.round(externalMin * 60 * 1000) };
  }

  function stopLiveUpdates() {
    if (state.weatherTimer) {
      clearInterval(state.weatherTimer);
      state.weatherTimer = null;
    }
    if (state.externalTimer) {
      clearInterval(state.externalTimer);
      state.externalTimer = null;
    }
  }

  async function refreshWeatherTick() {
    try {
      await loadWeather();
      const region = getSelectedRegion();
      if (region) renderCurrentRegion(region);
      setText('wa-updated', `Live - ${formatUpdatedWithTime(new Date())}`);
    } catch (e) {
      console.warn('Live weather refresh failed:', e);
    }
  }

  async function refreshExternalTick(force = false) {
    const { externalMs } = getLiveConfig();
    const now = Date.now();
    if (!force && state.lastExternalRefreshAt && (now - state.lastExternalRefreshAt) < externalMs) return;
    if (!state.selectedRegionId) return;

    try {
      state.lastExternalRefreshAt = now;
      const region = getSelectedRegion();
      await Promise.allSettled([
        loadForecast(state.selectedRegionId),
        loadFloodOutlook(state.selectedRegionId),
        loadExternal(state.selectedRegionId, region)
      ]);
      updateSelectedDayUI();
    } catch (e) {
      console.warn('Live external refresh failed:', e);
    }
  }

  function startLiveUpdates() {
    stopLiveUpdates();
    const { weatherMs, externalMs } = getLiveConfig();

    // Kick once immediately, then poll.
    void refreshWeatherTick();
    void refreshExternalTick(true);

    state.weatherTimer = setInterval(() => {
      if (document.visibilityState !== 'visible') return;
      void refreshWeatherTick();
    }, weatherMs);

    state.externalTimer = setInterval(() => {
      if (document.visibilityState !== 'visible') return;
      void refreshExternalTick(false);
    }, externalMs);

    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') {
        void refreshWeatherTick();
        void refreshExternalTick(false);
      }
    });

    window.addEventListener('beforeunload', stopLiveUpdates);
  }

  async function init() {
    initLogout();

    initCityTabs();
    initWeekCards();

    setText('wa-updated', `Last Updated, ${formatUpdated(new Date())}`);
    renderRainList(Array.from({ length: 7 }, () => ({ day: DASH, chance: 0 })));

    try {
      await loadWeather();
      if (state.selectedRegionId) setRegion(state.selectedRegionId);
      startLiveUpdates();
    } catch (e) {
      console.error('Weather load failed:', e);
      setText('wa-desc', 'Failed to load weather data');
    }
  }

  document.addEventListener('DOMContentLoaded', init);
})();
