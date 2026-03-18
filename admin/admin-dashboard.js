/**
 * Admin Dashboard JavaScript
 * Climate Early Warning System - Zambia
 */

(function() {
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

    // Check authentication
    function checkAuth() {
        const token = sessionStorage.getItem('adminToken');
        if (!token) {
            window.location.href = 'index.html';
            return false;
        }
        
        const user = JSON.parse(sessionStorage.getItem('adminUser') || '{}');
        if (user.username) {
            document.getElementById('admin-name').textContent = user.username;
            document.getElementById('admin-avatar').textContent = user.username.substring(0, 2).toUpperCase();
        }
        return true;
    }

    // Initialize dashboard
    async function initDashboard() {
        if (!checkAuth()) return;
        
        try {
            await Promise.all([
                loadAlerts(),
                loadUsers()
            ]);
            
            setupEventListeners();
        } catch (error) {
            console.error('Error initializing dashboard:', error);
        }
    }

    // Load alerts statistics
    async function loadAlerts() {
        try {
            const response = await fetch(`${API_BASE}/alerts?limit=20`);
            const result = await response.json();
            
            if (result.success && result.statistics) {
                const stats = result.statistics;
                
                // Update stat cards
                document.getElementById('total-alerts').textContent = (stats.total_alerts || 0).toLocaleString();
                document.getElementById('critical-alerts').textContent = ((stats.critical_count || 0) + (stats.high_count || 0)).toLocaleString();
                document.getElementById('manual-alerts').textContent = (stats.manual_count || 0).toLocaleString();
                
                document.getElementById('alerts-trend').innerHTML = `
                    ${stats.critical_count > 0 ? '⚠️ ' : ''}${stats.critical_count} Critical, ${stats.high_count} High
                `;
                
                // Update table
                updateAlertsTable(result.data);
            }
        } catch (error) {
            console.error('Error loading alerts:', error);
        }
    }

    // Load users statistics
    async function loadUsers() {
        try {
            const response = await fetch(`${API_BASE}/users?limit=100`);
            const result = await response.json();
            
            if (result.success && result.statistics) {
                const stats = result.statistics;
                
                document.getElementById('total-users').textContent = (stats.total_users || 0).toLocaleString();
                document.getElementById('users-trend').innerHTML = `${stats.active_users || 0} Active • ${stats.new_users_week || 0} New this week`;
            }
        } catch (error) {
            console.error('Error loading users:', error);
        }
    }

    // Update alerts table
    function updateAlertsTable(alerts) {
        const tbody = document.getElementById('alerts-table-body');
        
        if (!alerts || alerts.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 40px; color: var(--text-muted);">No alerts found</td></tr>';
            return;
        }
        
        tbody.innerHTML = alerts.map(alert => `
            <tr>
                <td><span class="risk-badge ${alert.risk_level}">${alert.risk_level}</span></td>
                <td style="max-width: 300px;">${truncateText(alert.message, 60)}</td>
                <td>${alert.region_name || 'National'}</td>
                <td>${formatDisasterType(alert.disaster_type)}</td>
                <td>${formatDate(alert.created_at)}</td>
                <td>${alert.is_sent ? '✓ Yes (' + alert.sent_count + ')' : '✗ No'}</td>
            </tr>
        `).join('');
    }

    // Setup event listeners
    function setupEventListeners() {
        document.getElementById('manual-alert-form').addEventListener('submit', handleManualAlert);
        
        document.getElementById('refresh-data').addEventListener('click', () => {
            initDashboard();
            showNotification('Data refreshed', 'success');
        });
    }

    // Handle manual alert submission
    async function handleManualAlert(e) {
        e.preventDefault();
        
        const data = {
            risk_level: document.getElementById('alert-risk-level').value,
            disaster_type: document.getElementById('alert-disaster-type').value,
            region_id: document.getElementById('alert-region').value || null,
            message: document.getElementById('alert-message').value,
            is_manual: true
        };
        
        try {
            const response = await fetch(`${API_BASE}/alerts/send`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (result.success) {
                const sentCount = (result.notification_result && (result.notification_result.sent_count ?? result.notification_result.total_recipients)) || 0;
                showNotification(`Alert sent successfully! Notified ${sentCount} users.`, 'success');
                e.target.reset();
                loadAlerts();
            } else {
                showNotification('Failed to send alert: ' + (result.error || 'Unknown error'), 'error');
            }
        } catch (error) {
            console.error('Error sending alert:', error);
            showNotification('Failed to connect to server', 'error');
        }
    }

    // Utility functions
    function truncateText(text, maxLength) {
        return text.length <= maxLength ? text : text.substring(0, maxLength) + '...';
    }

    function formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
    }

    function formatDisasterType(type) {
        return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }

    function showNotification(message, type = 'info') {
        alert(message);
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initDashboard);
    } else {
        initDashboard();
    }

})();
