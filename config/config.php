<?php
/**
 * Climate Early Warning System - Configuration
 * Zambia Climate Monitoring System
 */

// Database Configuration
define('DB_HOST', 'localhost');
define('DB_NAME', 'climate_ews_zambia');
define('DB_USER', 'root');
define('DB_PASS', ''); // Default XAMPP password is empty
define('DB_CHARSET', 'utf8mb4');

// Application Configuration
define('APP_NAME', 'Climate Early Warning System - Zambia');
define('APP_VERSION', '1.0.0');
define('APP_URL', 'http://localhost/project/frontend');

// API Configuration
define('API_URL', 'http://localhost/project/api');

// Alert Thresholds
define('FLOOD_RAINFALL_THRESHOLD', 100); // mm
define('DROUGHT_TEMP_THRESHOLD', 35); // °C
define('DROUGHT_RAINFALL_THRESHOLD', 10); // mm
define('EXTREME_TEMP_MIN', 5); // °C
define('EXTREME_TEMP_MAX', 40); // °C

// Risk Levels
define('RISK_LOW', 'low');
define('RISK_MEDIUM', 'medium');
define('RISK_HIGH', 'high');
define('RISK_CRITICAL', 'critical');

// Timezone
date_default_timezone_set('Africa/Lusaka');

// Error Reporting (Disable in production)
error_reporting(E_ALL);
ini_set('display_errors', 1);

// CORS Headers (for API calls)
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type, Authorization");
header("Content-Type: application/json; charset=UTF-8");

?>
