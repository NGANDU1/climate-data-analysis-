<?php
/**
 * API Endpoint: Get All Alerts
 * Returns all alerts for admin panel
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
    $limit = isset($_GET['limit']) ? intval($_GET['limit']) : 50;
    $riskLevel = isset($_GET['risk_level']) ? $_GET['risk_level'] : null;
    $disasterType = isset($_GET['disaster_type']) ? $_GET['disaster_type'] : null;
    $regionId = isset($_GET['region_id']) ? intval($_GET['region_id']) : null;
    
    // Build query
    $sql = "SELECT 
                a.*,
                r.name as region_name,
                CASE 
                    WHEN a.created_at > DATE_SUB(NOW(), INTERVAL 1 HOUR) THEN 'Very Recent'
                    WHEN a.created_at > DATE_SUB(NOW(), INTERVAL 24 HOUR) THEN 'Recent'
                    ELSE 'Older'
                END as recency_status
            FROM alerts a
            LEFT JOIN regions r ON a.region_id = r.id
            WHERE 1=1";
    
    $params = [];
    
    // Apply filters
    if ($riskLevel) {
        $sql .= " AND a.risk_level = :risk_level";
        $params['risk_level'] = $riskLevel;
    }
    
    if ($disasterType) {
        $sql .= " AND a.disaster_type = :disaster_type";
        $params['disaster_type'] = $disasterType;
    }
    
    if ($regionId) {
        $sql .= " AND a.region_id = :region_id";
        $params['region_id'] = $regionId;
    }
    
    $sql .= " ORDER BY a.created_at DESC LIMIT :limit";
    $params['limit'] = $limit;
    
    $alerts = $db->query($sql, $params);
    
    // Get statistics
    $statsSql = "SELECT 
                    COUNT(*) as total_alerts,
                    SUM(CASE WHEN risk_level = 'critical' THEN 1 ELSE 0 END) as critical_count,
                    SUM(CASE WHEN risk_level = 'high' THEN 1 ELSE 0 END) as high_count,
                    SUM(CASE WHEN risk_level = 'medium' THEN 1 ELSE 0 END) as medium_count,
                    SUM(CASE WHEN risk_level = 'low' THEN 1 ELSE 0 END) as low_count,
                    SUM(CASE WHEN is_manual = 1 THEN 1 ELSE 0 END) as manual_count
                 FROM alerts";
    
    $stats = $db->query($statsSql);
    
    if ($alerts !== false) {
        http_response_code(200);
        echo json_encode([
            'success' => true,
            'data' => $alerts,
            'statistics' => $stats[0] ?? [],
            'count' => count($alerts),
            'timestamp' => date('Y-m-d H:i:s')
        ]);
    } else {
        http_response_code(404);
        echo json_encode([
            'success' => false,
            'message' => 'No alerts found'
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
