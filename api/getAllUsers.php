<?php
/**
 * API Endpoint: Get All Users
 * Returns all subscribed users for admin panel
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
    $limit = isset($_GET['limit']) ? intval($_GET['limit']) : 100;
    $subscriptionType = isset($_GET['type']) ? $_GET['type'] : null;
    $activeOnly = isset($_GET['active']) ? ($_GET['active'] === 'true') : true;
    
    // Build query
    $sql = "SELECT 
                id,
                name,
                phone,
                email,
                location,
                subscription_type,
                is_active,
                created_at,
                CASE 
                    WHEN created_at > DATE_SUB(NOW(), INTERVAL 7 DAY) THEN 'New'
                    ELSE 'Existing'
                END as user_status
            FROM users
            WHERE 1=1";
    
    $params = [];
    
    // Apply filters
    if ($activeOnly) {
        $sql .= " AND is_active = TRUE";
    }
    
    if ($subscriptionType) {
        $sql .= " AND subscription_type = :type";
        $params['type'] = $subscriptionType;
    }
    
    $sql .= " ORDER BY created_at DESC LIMIT :limit";
    $params['limit'] = $limit;
    
    $users = $db->query($sql, $params);
    
    // Get statistics
    $statsSql = "SELECT 
                    COUNT(*) as total_users,
                    SUM(CASE WHEN is_active = TRUE THEN 1 ELSE 0 END) as active_users,
                    SUM(CASE WHEN subscription_type = 'sms' THEN 1 ELSE 0 END) as sms_only,
                    SUM(CASE WHEN subscription_type = 'email' THEN 1 ELSE 0 END) as email_only,
                    SUM(CASE WHEN subscription_type = 'both' THEN 1 ELSE 0 END) as both,
                    SUM(CASE WHEN created_at > DATE_SUB(NOW(), INTERVAL 7 DAY) THEN 1 ELSE 0 END) as new_users_week
                 FROM users";
    
    $stats = $db->query($statsSql);
    
    if ($users !== false) {
        http_response_code(200);
        echo json_encode([
            'success' => true,
            'data' => $users,
            'statistics' => $stats[0] ?? [],
            'count' => count($users),
            'timestamp' => date('Y-m-d H:i:s')
        ]);
    } else {
        http_response_code(404);
        echo json_encode([
            'success' => false,
            'message' => 'No users found'
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
