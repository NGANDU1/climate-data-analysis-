/**
 * Climate Early Warning System - Dashboard JavaScript
 * Zambia Climate Monitoring System
 */

(function() {
    'use strict';

    // API Base URL
    // - When served by Flask (recommended): use same-origin `/api`
    // - When served by a static dev server on localhost (e.g. :8080): fall back to Flask on :5000
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
    
    // Chart instance
    let weatherChart = null;
    
    // Map instance
    let map = null;
    let regionMarkers = [];
    
    // Data cache
    let currentWeatherData = null;
    let riskPredictions = null;
    let lastRegionQuery = '';

    // Canonical Zambia provinces (baseline markers so search always works)
    // Approximate coordinates (province capital / centroid).
    const ZAMBIA_PROVINCES = [
        { name: 'Central', latitude: -14.4500, longitude: 28.4500 },
        { name: 'Copperbelt', latitude: -12.8000, longitude: 28.2000 },
        { name: 'Eastern', latitude: -13.5500, longitude: 32.6500 },
        { name: 'Luapula', latitude: -11.9000, longitude: 29.6500 },
        { name: 'Lusaka', latitude: -15.4167, longitude: 28.2833 },
        { name: 'Muchinga', latitude: -10.9500, longitude: 32.1500 },
        { name: 'Northern', latitude: -10.2500, longitude: 31.1500 },
        { name: 'North-Western', latitude: -12.5500, longitude: 25.8500 },
        { name: 'Southern', latitude: -16.8000, longitude: 26.9500 },
        { name: 'Western', latitude: -14.8000, longitude: 23.2500 }
    ];

    // ============================================
    // Initialize Dashboard
    // ============================================
    function hasAdminSession() {
        try {
            return !!window.sessionStorage.getItem('adminToken');
        } catch (_) {
            return false;
        }
    }

    function requireViewerSession() {
        const userSession = window.localStorage.getItem('userSession');
        if (!userSession && !hasAdminSession()) {
            window.location.href = 'login.html';
            return false;
        }
        return true;
    }

    function attachLogout() {
        const logoutLink = document.getElementById('logout-link');
        if (!logoutLink) return;

        logoutLink.addEventListener('click', (e) => {
            e.preventDefault();
            try {
                window.localStorage.removeItem('userSession');
            } catch (_) {}
            window.location.href = 'home.html';
        });
    }

    async function initDashboard() {
        try {
            console.log('Initializing Climate EWS Dashboard...');

            if (!requireViewerSession()) return;
            attachLogout();
            
            // Load all data (don't fail the whole UI if one endpoint fails)
            await Promise.allSettled([
                loadWeatherData(),
                loadRiskPredictions(),
                loadAlerts(),
                loadWeatherTrends()
            ]);
            
            // Initialize map after data is loaded
            try {
                initMap();
            } catch (err) {
                console.error('Map failed to initialize:', err);
            }
            
            // Setup event listeners
            setupEventListeners();
            
            // Auto-refresh every 60 seconds
            setInterval(refreshData, 60000);
            
        } catch (error) {
            console.error('Error initializing dashboard:', error);
            showNotification('Failed to load dashboard data', 'error');
        }
    }

    // ============================================
    // Load Weather Data
    // ============================================
    async function loadWeatherData() {
        try {
            const response = await fetch(`${API_BASE}/weather`);
            const result = await response.json();
            
            if (result.success && result.data) {
                currentWeatherData = result.data;
                updateWeatherStats(result.data);
                updateMapMarkers(result.data);
            }
        } catch (error) {
            console.error('Error loading weather data:', error);
        }
    }

    // ============================================
    // Load Risk Predictions
    // ============================================
    async function loadRiskPredictions() {
        try {
            const response = await fetch(`${API_BASE}/risk/predict`);
            const result = await response.json();
            
            if (result.success) {
                riskPredictions = result;
                updateRiskSummary(result.summary);
                updateRegionRiskLevels(result.predictions);
            }
        } catch (error) {
            console.error('Error loading risk predictions:', error);
        }
    }

    // ============================================
    // Load Alerts
    // ============================================
    async function loadAlerts() {
        try {
            const response = await fetch(`${API_BASE}/alerts`);
            const result = await response.json();
            
            if (result.success && result.data) {
                displayAlerts(result.data);
                updateActiveAlertsCount(result.statistics);
            }
        } catch (error) {
            console.error('Error loading alerts:', error);
        }
    }

    // ============================================
    // Load Weather Trends
    // ============================================
    async function loadWeatherTrends() {
        try {
            const response = await fetch(`${API_BASE}/admin/weather-trends?days=7`);
            const result = await response.json();
            
            if (result.success && result.chart_data) {
                renderWeatherChart(result.chart_data);
            }
        } catch (error) {
            console.error('Error loading weather trends:', error);
        }
    }

    // ============================================
    // Update Weather Statistics
    // ============================================
    function updateWeatherStats(data) {
        if (!data || data.length === 0) return;
        
        // Calculate averages
        const totalTemp = data.reduce((sum, row) => sum + parseFloat(row.temperature || 0), 0);
        const totalHumidity = data.reduce((sum, row) => sum + parseFloat(row.humidity || 0), 0);
        const totalRainfall = data.reduce((sum, row) => sum + parseFloat(row.rainfall || 0), 0);
        
        const avgTemp = (totalTemp / data.length).toFixed(1);
        const avgHumidity = (totalHumidity / data.length).toFixed(1);
        const sumRainfall = totalRainfall.toFixed(1);
        
        // Animate counters
        animateValue('avg-temp', avgTemp + '°C');
        animateValue('avg-humidity', avgHumidity + '%');
        animateValue('total-rainfall', sumRainfall + 'mm');
        
        // Update trends
        document.getElementById('temp-trend').innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="4"/>
            </svg>
            National Average
        `;
        
        document.getElementById('humidity-trend').innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/>
            </svg>
            Moderate
        `;
        
        document.getElementById('rainfall-trend').innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242"/>
            </svg>
            ${sumRainfall > 100 ? 'High' : 'Normal'} Levels
        `;
    }

    // ============================================
    // Update Risk Summary
    // ============================================
    function updateRiskSummary(summary) {
        if (!summary) return;
        
        const badge = document.getElementById('overall-risk-badge');
        const summaryText = document.getElementById('risk-summary-text');
        
        const riskLevel = summary.overall_risk_level;
        const criticalCount = summary.critical_regions;
        const highCount = summary.high_risk_regions;
        
        badge.innerHTML = `<span class="risk-badge ${riskLevel}">${riskLevel} Risk</span>`;
        
        let message = '';
        if (criticalCount > 0) {
            message = `⚠️ CRITICAL: ${criticalCount} region(s) in emergency state. ${highCount} additional high-risk areas.`;
        } else if (highCount > 0) {
            message = `⚠️ WARNING: ${highCount} region(s) at high risk. Monitor conditions closely.`;
        } else if (summary.medium_risk_regions > 0) {
            message = `ℹ️ CAUTION: ${summary.medium_risk_regions} region(s) showing elevated risk levels.`;
        } else {
            message = `✓ All ${summary.total_regions_monitored} regions reporting normal conditions.`;
        }
        
        summaryText.textContent = message;
    }

    // ============================================
    // Display Alerts
    // ============================================
    function displayAlerts(alerts) {
        const container = document.getElementById('alerts-feed');
        
        if (!alerts || alerts.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; padding: 40px; color: var(--text-muted);">
                    <p>No active alerts</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = alerts.map(alert => {
            const icon = getAlertIcon(alert.risk_level);
            const timeAgo = getTimeAgo(new Date(alert.created_at));
            
            return `
                <div class="activity-item alert-notification">
                    <div class="activity-avatar" style="background: linear-gradient(135deg, ${getRiskColor(alert.risk_level)}, rgba(0,0,0,0.2));">
                        ${icon}
                    </div>
                    <div class="activity-content">
                        <p class="activity-text" style="color: var(--text-primary);">
                            <strong>${alert.region_name || 'National'}</strong>: ${truncateText(alert.message, 80)}
                        </p>
                        <span class="activity-time">
                            <span class="risk-badge ${alert.risk_level}" style="font-size: 10px; padding: 2px 8px; margin-right: 8px;">
                                ${alert.risk_level}
                            </span>
                            ${timeAgo} • ${alert.disaster_type.replace('_', ' ')}
                        </span>
                    </div>
                </div>
            `;
        }).join('');
    }

    // ============================================
    // Initialize Map
    // ============================================
    function initMap() {
        if (typeof window.L === 'undefined') {
            throw new Error('Leaflet.js is not loaded (window.L is undefined)');
        }
        const mapEl = document.getElementById('zambia-map');
        if (!mapEl) return;

        // Center on Zambia
        const zambiaCoords = [-13.1339, 27.8493];
        
        map = L.map('zambia-map').setView(zambiaCoords, 6);
        
        // Add dark matter tile layer (works better with our theme)
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
            subdomains: 'abcd',
            maxZoom: 19
        }).addTo(map);
        
        // Add region markers
        if (currentWeatherData) {
            updateMapMarkers(currentWeatherData);
        } else {
            updateMapMarkers([]);
        }
    }

    // ============================================
    // Update Map Markers
    // ============================================
    function updateMapMarkers(weatherData) {
        if (!map) return;

        const normalizeRegionName = (name) => {
            return (name || '')
                .toString()
                .toLowerCase()
                .replace(/\bprovince\b/g, '')
                .replace(/north[\s-]*western/g, 'north-western')
                .replace(/[^a-z\s-]/g, ' ')
                .replace(/\s+/g, ' ')
                .trim();
        };

        const formatMaybeNumber = (value, decimals = 1) => {
            const n = Number(value);
            if (!Number.isFinite(n)) return '--';
            return n.toFixed(decimals);
        };

        const buildMarkerIcon = (riskColor) => {
            const safeColor = riskColor || '#6b7280';
            const markerHtml = `
                <div style="
                    background: ${safeColor};
                    border: 2px solid white;
                    border-radius: 50%;
                    width: 20px;
                    height: 20px;
                    box-shadow: 0 0 10px ${safeColor};
                "></div>
            `;

            return L.divIcon({
                html: markerHtml,
                className: 'custom-marker',
                iconSize: [20, 20]
            });
        };

        // Clear existing markers
        regionMarkers.forEach(marker => map.removeLayer(marker));
        regionMarkers = [];

        // Baseline: always render all provinces so search always finds something
        const provinceByKey = new Map();
        ZAMBIA_PROVINCES.forEach((province) => {
            const key = normalizeRegionName(province.name);
            const riskColor = getRiskColorHex('low');

            const marker = L.marker([province.latitude, province.longitude], {
                title: province.name,
                icon: buildMarkerIcon(riskColor)
            }).addTo(map);

            marker._regionName = province.name;
            marker._regionKey = key;

            marker.bindPopup(`
                <div style="min-width: 220px;">
                    <h3 style="margin-bottom: 8px; color: #333;">${province.name} Province</h3>
                    <p style="margin: 0; color: #6b7280;">No live data loaded for this region yet.</p>
                </div>
            `);

            provinceByKey.set(key, marker);
            regionMarkers.push(marker);
        });
        
        (weatherData || []).forEach((region) => {
            const regionName = region?.region_name || region?.name || '';
            const key = normalizeRegionName(regionName);
            const riskColor = getRiskColorHex(region?.region_risk || 'low');

            const popupHtml = `
                <div style="min-width: 220px;">
                    <h3 style="margin-bottom: 8px; color: #333;">${regionName || 'Region'}</h3>
                    <p><strong>Temperature:</strong> ${formatMaybeNumber(region?.temperature)}Â°C</p>
                    <p><strong>Humidity:</strong> ${formatMaybeNumber(region?.humidity)}%</p>
                    <p><strong>Rainfall:</strong> ${formatMaybeNumber(region?.rainfall)}mm</p>
                    <p><strong>Risk Level:</strong> <span style="color: ${riskColor}; font-weight: bold;">${(region?.region_risk || 'low').toString().toUpperCase()}</span></p>
                </div>
            `;

            const existing = key ? provinceByKey.get(key) : null;
            if (existing) {
                existing.setIcon(buildMarkerIcon(riskColor));
                existing._regionName = regionName || existing._regionName;
                existing.bindPopup(popupHtml);
                return;
            }

            if (region?.latitude && region?.longitude) {
                const marker = L.marker([region.latitude, region.longitude], {
                    title: regionName || '',
                    icon: buildMarkerIcon(riskColor)
                }).addTo(map);

                marker._regionName = regionName || '';
                marker._regionKey = key || '';
                marker.bindPopup(popupHtml);

                regionMarkers.push(marker);
            }

            // Always return here to avoid duplicating markers in the legacy block below.
            return;

            if (region.latitude && region.longitude) {
                const riskColor = getRiskColorHex(region.region_risk || 'low');
                
                // Create custom marker
                const markerHtml = `
                    <div style="
                        background: ${riskColor};
                        border: 2px solid white;
                        border-radius: 50%;
                        width: 20px;
                        height: 20px;
                        box-shadow: 0 0 10px ${riskColor};
                    "></div>
                `;
                
                const marker = L.marker([region.latitude, region.longitude], {
                    title: region.region_name || '',
                    icon: L.divIcon({
                        html: markerHtml,
                        className: 'custom-marker',
                        iconSize: [20, 20]
                    })
                }).addTo(map);

                marker._regionName = region.region_name || '';
                
                // Add popup
                marker.bindPopup(`
                    <div style="min-width: 200px;">
                        <h3 style="margin-bottom: 8px; color: #333;">${region.region_name}</h3>
                        <p><strong>Temperature:</strong> ${parseFloat(region.temperature).toFixed(1)}°C</p>
                        <p><strong>Humidity:</strong> ${parseFloat(region.humidity).toFixed(1)}%</p>
                        <p><strong>Rainfall:</strong> ${parseFloat(region.rainfall).toFixed(1)}mm</p>
                        <p><strong>Risk Level:</strong> <span style="color: ${riskColor}; font-weight: bold;">${(region.region_risk || 'low').toUpperCase()}</span></p>
                    </div>
                `);
                
                regionMarkers.push(marker);
            }
        });

        if (lastRegionQuery) {
            filterRegions(lastRegionQuery);
        }
    }

    // ============================================
    // Render Weather Chart
    // ============================================
    function renderWeatherChart(chartData) {
        const ctx = document.getElementById('weather-chart').getContext('2d');
        
        if (weatherChart) {
            weatherChart.destroy();
        }
        
        weatherChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: chartData.labels,
                datasets: [
                    {
                        label: 'Temperature (°C)',
                        data: chartData.datasets.temperature.data,
                        borderColor: '#dc2626',
                        backgroundColor: 'rgba(220, 38, 38, 0.1)',
                        yAxisID: 'y',
                        tension: 0.4
                    },
                    {
                        label: 'Humidity (%)',
                        data: chartData.datasets.humidity.data,
                        borderColor: '#2563eb',
                        backgroundColor: 'rgba(37, 99, 235, 0.1)',
                        yAxisID: 'y',
                        tension: 0.4
                    },
                    {
                        label: 'Rainfall (mm)',
                        data: chartData.datasets.rainfall.data,
                        backgroundColor: 'rgba(5, 150, 105, 0.2)',
                        borderColor: '#059669',
                        type: 'bar',
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            color: '#9ca3af'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: {
                            drawOnChartArea: false
                        },
                        ticks: {
                            color: '#9ca3af'
                        }
                    },
                    x: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)'
                        },
                        ticks: {
                            color: '#9ca3af',
                            maxRotation: 45,
                            minRotation: 45
                        }
                    }
                }
            }
        });
    }

    // ============================================
    // Event Listeners
    // ============================================
    function setupEventListeners() {
        // Refresh button
        const refreshBtn = document.getElementById('refresh-data');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', refreshData);
        }
        
        // Chart interval buttons
        document.querySelectorAll('.card-btn[data-interval]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.card-btn[data-interval]').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                loadWeatherTrendsForInterval(e.target.dataset.interval);
            });
        });
        
        // Subscription form
        const subscriptionForm = document.getElementById('subscription-form');
        if (subscriptionForm) {
            subscriptionForm.addEventListener('submit', handleSubscription);
        }
        
        // Region search
        const regionSearch = document.getElementById('region-search');
        if (regionSearch) {
            regionSearch.addEventListener('input', (e) => {
                filterRegions(e.target.value);
            });
        }

        // National Risk Summary click -> scroll to map
        const riskSummaryCard = document.getElementById('national-risk-summary');
        if (riskSummaryCard) {
            const goToMap = () => {
                const target = document.getElementById('regional-risk-map') || document.getElementById('zambia-map');
                if (!target) return;

                target.scrollIntoView({ behavior: 'smooth', block: 'start' });

                // Brief highlight so users notice where they landed
                try {
                    target.classList.add('pulse-highlight');
                    window.setTimeout(() => target.classList.remove('pulse-highlight'), 1200);
                } catch (_) {}
            };

            riskSummaryCard.addEventListener('click', goToMap);
            riskSummaryCard.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    goToMap();
                }
            });
        }
    }

    // ============================================
    // Handle Subscription
    // ============================================
    async function handleSubscription(e) {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        const data = {
            name: e.target.querySelector('input[type="text"]').value,
            phone: e.target.querySelector('input[type="tel"]').value,
            email: e.target.querySelector('input[type="email"]').value,
            location: e.target.querySelector('input[type="text"]:nth-of-type(2)').value,
            subscription_type: e.target.querySelector('select').value
        };
        
        try {
            const response = await fetch(`${API_BASE}/users/subscribe`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (result.success) {
                showNotification(result.message, 'success');
                e.target.reset();
            } else {
                showNotification(result.error || 'Subscription failed', 'error');
            }
        } catch (error) {
            console.error('Subscription error:', error);
            showNotification('Failed to connect to server', 'error');
        }
    }

    // ============================================
    // Refresh Data
    // ============================================
    function refreshData() {
        const btn = document.getElementById('refresh-data');
        btn.style.animation = 'spin 1s linear';
        
        setTimeout(() => {
            btn.style.animation = '';
            initDashboard();
            showNotification('Data refreshed successfully', 'success');
        }, 1000);
    }

    // ============================================
    // Utility Functions
    // ============================================
    function animateValue(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    }

    function getAlertIcon(riskLevel) {
        const icons = {
            low: 'ℹ️',
            medium: '⚠️',
            high: '🚨',
            critical: '🆘'
        };
        return icons[riskLevel] || 'ℹ️';
    }

    function getRiskColor(riskLevel) {
        const colors = {
            low: '#22c55e',
            medium: '#eab308',
            high: '#f97316',
            critical: '#dc2626'
        };
        return colors[riskLevel] || '#6b7280';
    }

    function getRiskColorHex(riskLevel) {
        return getRiskColor(riskLevel);
    }

    function truncateText(text, maxLength) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }

    function getTimeAgo(date) {
        const seconds = Math.floor((new Date() - date) / 1000);
        
        if (seconds < 60) return 'Just now';
        if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes ago`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`;
        return `${Math.floor(seconds / 86400)} days ago`;
    }

    function showNotification(message, type = 'info') {
        // Simple notification (can be enhanced with a proper notification library)
        console.log(`[${type.toUpperCase()}] ${message}`);
        alert(message); // Fallback for demo
    }

    function filterRegions(query) {
        lastRegionQuery = (query || '').toString();
        if (!map || !regionMarkers || regionMarkers.length === 0) return;

        const lowerQuery = lastRegionQuery.trim().toLowerCase();

        // Reset when empty
        if (!lowerQuery) {
            try { map.closePopup(); } catch (_) {}
            regionMarkers.forEach((marker) => {
                const el = marker.getElement && marker.getElement();
                if (el) el.style.opacity = '1';
            });
            return;
        }

        let firstMatch = null;

        regionMarkers.forEach((marker) => {
            const regionName = (marker._regionName || marker.options?.title || '').toString();
            const isMatch = regionName.toLowerCase().includes(lowerQuery);

            const el = marker.getElement && marker.getElement();
            if (el) el.style.opacity = isMatch ? '1' : '0.2';

            if (isMatch && !firstMatch) firstMatch = marker;
        });

        if (firstMatch) {
            try {
                const ll = firstMatch.getLatLng();
                map.flyTo(ll, Math.max(map.getZoom(), 7), { animate: true, duration: 0.6 });
                firstMatch.openPopup();
            } catch (_) {
                try { firstMatch.openPopup(); } catch (_) {}
            }
        }
    }

    function updateActiveAlertsCount(statistics) {
        const countElement = document.getElementById('active-alerts');
        const statusElement = document.getElementById('alerts-status');
        
        if (statistics) {
            const total = statistics.total_alerts || 0;
            const recent = (statistics.critical_count || 0) + (statistics.high_count || 0);
            
            animateValue('active-alerts', total);
            
            if (recent > 0) {
                statusElement.innerHTML = `
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#f97316" stroke-width="2">
                        <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>
                    </svg>
                    ${recent} critical/high
                `;
            } else {
                statusElement.innerHTML = `
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2">
                        <polyline points="20 6 9 17 4 12"/>
                    </svg>
                    All clear
                `;
            }
        }
    }

    function updateRegionRiskLevels(predictions) {
        if (!predictions || !map) return;
        
        // This would update the map with colored regions based on predictions
        // For now, we're using point markers
        console.log('Region risk levels updated:', predictions.length, 'regions');
    }

    async function loadWeatherTrendsForInterval(interval) {
        try {
            const response = await fetch(`${API_BASE}/admin/weather-trends?days=7&interval=${interval}`);
            const result = await response.json();
            
            if (result.success && result.chart_data) {
                renderWeatherChart(result.chart_data);
            }
        } catch (error) {
            console.error('Error loading weather trends:', error);
        }
    }

    // Add CSS animation for spin
    const style = document.createElement('style');
    style.textContent = `
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
    `;
    document.head.appendChild(style);

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initDashboard);
    } else {
        initDashboard();
    }

})();
