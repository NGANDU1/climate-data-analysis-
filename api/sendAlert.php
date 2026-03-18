<?php
/**
 * API Endpoint: Send Alert
 * Creates and stores alert notifications in database
 * Simulates SMS/Email sending
 */

require_once '../config/config.php';
require_once '../config/database.php';

// Handle preflight OPTIONS request
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

// Only accept POST requests
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Method not allowed. Use POST.']);
    exit();
}

try {
    // Get JSON input
    $input = json_decode(file_get_contents('php://input'), true);
    
    if (!$input) {
        http_response_code(400);
        echo json_encode([
            'success' => false,
            'error' => 'Invalid JSON data'
        ]);
        exit();
    }
    
    $db = new Database();
    
    // Validate required fields
    $requiredFields = ['message', 'risk_level'];
    foreach ($requiredFields as $field) {
        if (empty($input[$field])) {
            http_response_code(400);
            echo json_encode([
                'success' => false,
                'error' => "Missing required field: {$field}"
            ]);
            exit();
        }
    }
    
    // Validate risk level
    $validRiskLevels = [RISK_LOW, RISK_MEDIUM, RISK_HIGH, RISK_CRITICAL];
    if (!in_array($input['risk_level'], $validRiskLevels)) {
        http_response_code(400);
        echo json_encode([
            'success' => false,
            'error' => 'Invalid risk level'
        ]);
        exit();
    }
    
    // Sanitize inputs
    $message = htmlspecialchars(strip_tags(trim($input['message'])));
    $riskLevel = $input['risk_level'];
    $disasterType = isset($input['disaster_type']) ? $input['disaster_type'] : 'general';
    $regionId = isset($input['region_id']) ? intval($input['region_id']) : null;
    $isManual = isset($input['is_manual']) ? (bool)$input['is_manual'] : false;
    
    // Insert alert into database
    $sql = "INSERT INTO alerts (message, risk_level, disaster_type, region_id, is_manual, is_sent, sent_count, created_at) 
            VALUES (:message, :risk_level, :disaster_type, :region_id, :is_manual, TRUE, 0, NOW())";
    
    $params = [
        'message' => $message,
        'risk_level' => $riskLevel,
        'disaster_type' => $disasterType,
        'region_id' => $regionId,
        'is_manual' => $is_manual ? 1 : 0
    ];
    
    $result = $db->execute($sql, $params);
    
    if ($result) {
        $alertId = $db->getLastInsertId();
        
        // Simulate sending SMS/Email to subscribed users
        $notificationResult = sendNotifications($db, $alertId, $message, $riskLevel);
        
        // Update sent count
        $updateSql = "UPDATE alerts SET sent_count = :count WHERE id = :id";
        $db->execute($updateSql, [
            'count' => $notificationResult['sent_count'],
            'id' => $alertId
        ]);
        
        http_response_code(201);
        echo json_encode([
            'success' => true,
            'message' => 'Alert created and notifications sent',
            'alert_id' => $alertId,
            'notifications' => [
                'sms_sent' => $notificationResult['sms_sent'],
                'email_sent' => $notificationResult['email_sent'],
                'total_sent' => $notificationResult['sent_count'],
                'failed' => $notificationResult['failed']
            ]
        ]);
    } else {
        http_response_code(500);
        echo json_encode([
            'success' => false,
            'error' => 'Failed to create alert'
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
 * Send notifications to subscribed users
 * Simulates SMS/Email API calls
 */
function sendNotifications($db, $alertId, $message, $riskLevel) {
    $result = [
        'sms_sent' => 0,
        'email_sent' => 0,
        'sent_count' => 0,
        'failed' => 0
    ];
    
    // Get all active subscribers
    $usersSql = "SELECT * FROM users WHERE is_active = TRUE";
    $users = $db->query($usersSql);
    
    if (!$users || empty($users)) {
        return $result; // No users to notify
    }
    
    // Prepare alert message
    $riskEmoji = [
        RISK_LOW => 'ℹ️',
        RISK_MEDIUM => '⚠️',
        RISK_HIGH => '🚨',
        RISK_CRITICAL => '🆘'
    ];
    
    $subject = "[CLIMATE ALERT] {$riskEmoji[$riskLevel]} {$riskLevel} Risk Level - Zambia EWS";
    
    foreach ($users as $user) {
        $sent = false;
        
        // Send SMS
        if (in_array($user['subscription_type'], ['sms', 'both']) && !empty($user['phone'])) {
            $smsMessage = "ZAMBIA EWS: {$message}";
            // SIMULATE SMS API CALL (In production, integrate with Twilio/Africa's Talking, etc.)
            // $smsResult = sendSMSViaAPI($user['phone'], $smsMessage);
            
            // For demo purposes, assume success
            $result['sms_sent']++;
            $sent = true;
            
            // Log simulated SMS (in production, log actual API response)
            error_log("SIMULATED SMS to {$user['phone']}: {$smsMessage}");
        }
        
        // Send Email
        if (in_array($user['subscription_type'], ['email', 'both']) && !empty($user['email'])) {
            $emailBody = generateEmailBody($user['name'], $message, $riskLevel);
            // SIMULATE EMAIL API CALL (In production, integrate with SendGrid/Mailgun, etc.)
            // $emailResult = sendEmailViaAPI($user['email'], $subject, $emailBody);
            
            // For demo purposes, assume success
            $result['email_sent']++;
            $sent = true;
            
            // Log simulated email
            error_log("SIMULATED EMAIL to {$user['email']}: {$subject}");
        }
        
        if ($sent) {
            $result['sent_count']++;
        } else {
            $result['failed']++;
        }
    }
    
    return $result;
}

/**
 * Generate HTML email body
 */
function generateEmailBody($userName, $message, $riskLevel) {
    $colors = [
        RISK_LOW => '#28a745',
        RISK_MEDIUM => '#ffc107',
        RISK_HIGH => '#dc3545',
        RISK_CRITICAL => '#721c24'
    ];
    
    $color = $colors[$riskLevel] ?? '#6c757d';
    
    return "
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; }
            .container { max-width: 600px; margin: 0 auto; padding: 20px; }
            .header { background: {$color}; color: white; padding: 20px; text-align: center; }
            .content { padding: 20px; background: #f9f9f9; }
            .footer { padding: 20px; text-align: center; font-size: 12px; color: #666; }
        </style>
    </head>
    <body>
        <div class='container'>
            <div class='header'>
                <h1>🌦️ Climate Early Warning System</h1>
                <h2>Risk Level: " . strtoupper($riskLevel) . "</h2>
            </div>
            <div class='content'>
                <p>Dear {$userName},</p>
                <p><strong>Important Weather Alert:</strong></p>
                <p style='background: white; padding: 15px; border-left: 4px solid {$color};'>{$message}</p>
                <p>Please take necessary precautions and stay safe.</p>
                <p>For more information, visit our dashboard or contact emergency services.</p>
            </div>
            <div class='footer'>
                <p>This is an automated message from Zambia Climate Early Warning System.</p>
                <p>© " . date('Y') . " Climate EWS Zambia</p>
            </div>
        </div>
    </body>
    </html>
    ";
}
?>
