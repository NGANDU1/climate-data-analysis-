<?php
/**
 * API Endpoint: Get Weather Data
 * Returns current weather data for all regions or specific region
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
    
    // Check if region parameter is provided
    if (isset($_GET['region_id'])) {
        $region_id = intval($_GET['region_id']);
        
        // Get latest weather data for specific region
        $sql = "SELECT 
                    w.*,
                    r.name as region_name,
                    r.latitude,
                    r.longitude,
                    r.risk_level as region_risk
                FROM weather_data w
                JOIN regions r ON w.region_id = r.id
                WHERE w.region_id = :region_id
                ORDER BY w.timestamp DESC
                LIMIT 1";
        
        $weatherData = $db->query($sql, ['region_id' => $region_id]);
        
    } else {
        // Get latest weather data for all regions (average of last 3 readings)
        $sql = "SELECT 
                    r.id as region_id,
                    r.name as region_name,
                    r.latitude,
                    r.longitude,
                    r.risk_level as region_risk,
                    AVG(w.temperature) as temperature,
                    AVG(w.humidity) as humidity,
                    SUM(w.rainfall) as rainfall,
                    AVG(w.wind_speed) as wind_speed,
                    AVG(w.pressure) as pressure
                FROM regions r
                LEFT JOIN (
                    SELECT * FROM (
                        SELECT * FROM weather_data 
                        ORDER BY timestamp DESC 
                        LIMIT 30
                    ) AS recent_data
                ) w ON r.id = w.region_id
                GROUP BY r.id, r.name, r.latitude, r.longitude, r.risk_level
                ORDER BY r.name";
        
        $weatherData = $db->query($sql);
    }
    
    if ($weatherData) {
        http_response_code(200);
        echo json_encode([
            'success' => true,
            'data' => $weatherData,
            'timestamp' => date('Y-m-d H:i:s'),
            'count' => count($weatherData)
        ]);
    } else {
        http_response_code(404);
        echo json_encode([
            'success' => false,
            'message' => 'No weather data found'
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
?>
