<?php
/**
 * API Endpoint: Get Weather Trends
 * Returns historical weather data for charts and analysis
 */

require_once '../config/config.php';
require_once '../config/database.php';

// Handle preflight OPTIONS request
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

try {
    $db = new Database();
    
    // Get query parameters
    $regionId = isset($_GET['region_id']) ? intval($_GET['region_id']) : null;
    $days = isset($_GET['days']) ? intval($_GET['days']) : 7;
    $interval = isset($_GET['interval']) ? $_GET['interval'] : 'hourly'; // hourly, daily
    
    // Build query based on interval
    if ($interval === 'daily') {
        $dateFormat = '%Y-%m-%d';
        $groupByClause = "DATE(w.timestamp)";
    } else {
        $dateFormat = '%Y-%m-%d %H:00';
        $groupByClause = "DATE_FORMAT(w.timestamp, '{$dateFormat}')";
    }
    
    if ($regionId) {
        // Single region trends
        $sql = "SELECT 
                    {$groupByClause} as period,
                    AVG(w.temperature) as avg_temperature,
                    MIN(w.temperature) as min_temperature,
                    MAX(w.temperature) as max_temperature,
                    AVG(w.humidity) as avg_humidity,
                    SUM(w.rainfall) as total_rainfall,
                    AVG(w.wind_speed) as avg_wind_speed,
                    COUNT(*) as data_points
                FROM weather_data w
                WHERE w.region_id = :region_id 
                  AND w.timestamp > DATE_SUB(NOW(), INTERVAL :days DAY)
                GROUP BY {$groupByClause}
                ORDER BY period ASC";
        
        $trends = $db->query($sql, [
            'region_id' => $regionId,
            'days' => $days
        ]);
        
    } else {
        // All regions summary
        $sql = "SELECT 
                    r.id as region_id,
                    r.name as region_name,
                    {$groupByClause} as period,
                    AVG(w.temperature) as avg_temperature,
                    AVG(w.humidity) as avg_humidity,
                    SUM(w.rainfall) as total_rainfall
                FROM regions r
                LEFT JOIN weather_data w ON r.id = w.region_id 
                  AND w.timestamp > DATE_SUB(NOW(), INTERVAL :days DAY)
                GROUP BY r.id, r.name, {$groupByClause}
                ORDER BY r.name, period ASC";
        
        $trends = $db->query($sql, ['days' => $days]);
    }
    
    if ($trends) {
        // Generate chart-ready data
        $chartData = prepareChartData($trends, $interval);
        
        http_response_code(200);
        echo json_encode([
            'success' => true,
            'data' => $trends,
            'chart_data' => $chartData,
            'parameters' => [
                'region_id' => $regionId,
                'days' => $days,
                'interval' => $interval
            ],
            'count' => count($trends),
            'timestamp' => date('Y-m-d H:i:s')
        ]);
    } else {
        http_response_code(404);
        echo json_encode([
            'success' => false,
            'message' => 'No trend data found'
        ]);
    }
    
} catch(Exception $e) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Server error',
        'message' => $e->getMessage()
    ]);
}

/**
 * Prepare data for Chart.js
 */
function prepareChartData($trends, $interval) {
    $labels = [];
    $temperature = [];
    $humidity = [];
    $rainfall = [];
    
    foreach ($trends as $row) {
        $labels[] = $row['period'];
        $temperature[] = floatval($row['avg_temperature'] ?? 0);
        $humidity[] = floatval($row['avg_humidity'] ?? 0);
        $rainfall[] = floatval($row['total_rainfall'] ?? 0);
    }
    
    return [
        'labels' => $labels,
        'datasets' => [
            'temperature' => [
                'label' => 'Temperature (°C)',
                'data' => $temperature,
                'borderColor' => '#dc2626',
                'backgroundColor' => 'rgba(220, 38, 38, 0.1)',
                'yAxisID' => 'y'
            ],
            'humidity' => [
                'label' => 'Humidity (%)',
                'data' => $humidity,
                'borderColor' => '#2563eb',
                'backgroundColor' => 'rgba(37, 99, 235, 0.1)',
                'yAxisID' => 'y'
            ],
            'rainfall' => [
                'label' => 'Rainfall (mm)',
                'data' => $rainfall,
                'borderColor' => '#059669',
                'backgroundColor' => 'rgba(5, 150, 105, 0.2)',
                'type' => 'bar',
                'yAxisID' => 'y1'
            ]
        ]
    ];
}
?>
