<?php
/**
 * API Endpoint: Subscribe User
 * Handles user subscriptions for weather alerts
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
    if (empty($input['name'])) {
        http_response_code(400);
        echo json_encode([
            'success' => false,
            'error' => 'Name is required'
        ]);
        exit();
    }
    
    // Validate at least phone or email is provided
    if (empty($input['phone']) && empty($input['email'])) {
        http_response_code(400);
        echo json_encode([
            'success' => false,
            'error' => 'At least phone number or email is required'
        ]);
        exit();
    }
    
    // Sanitize inputs
    $name = htmlspecialchars(strip_tags(trim($input['name'])));
    $phone = isset($input['phone']) ? preg_replace('/[^0-9+]/', '', trim($input['phone'])) : null;
    $email = isset($input['email']) ? filter_var(trim($input['email']), FILTER_SANITIZE_EMAIL) : null;
    $location = isset($input['location']) ? htmlspecialchars(strip_tags(trim($input['location']))) : null;
    $subscriptionType = isset($input['subscription_type']) ? $input['subscription_type'] : 'email';
    
    // Validate email format if provided
    if ($email && !filter_var($email, FILTER_VALIDATE_EMAIL)) {
        http_response_code(400);
        echo json_encode([
            'success' => false,
            'error' => 'Invalid email format'
        ]);
        exit();
    }
    
    // Validate subscription type
    $validTypes = ['sms', 'email', 'both'];
    if (!in_array($subscriptionType, $validTypes)) {
        http_response_code(400);
        echo json_encode([
            'success' => false,
            'error' => 'Invalid subscription type'
        ]);
        exit();
    }
    
    // Check if user already exists (by email or phone)
    $checkSql = "SELECT id, is_active FROM users 
                 WHERE email = :email OR phone = :phone 
                 LIMIT 1";
    
    $existingUser = $db->query($checkSql, [
        'email' => $email ?: '',
        'phone' => $phone ?: ''
    ]);
    
    if ($existingUser && !empty($existingUser)) {
        // User exists - reactivate if inactive
        $userId = $existingUser[0]['id'];
        $isActive = $existingUser[0]['is_active'];
        
        if (!$isActive) {
            $updateSql = "UPDATE users SET 
                         name = :name,
                         phone = :phone,
                         email = :email,
                         location = :location,
                         subscription_type = :subscription_type,
                         is_active = TRUE,
                         created_at = NOW()
                         WHERE id = :id";
            
            $db->execute($updateSql, [
                'name' => $name,
                'phone' => $phone,
                'email' => $email,
                'location' => $location,
                'subscription_type' => $subscriptionType,
                'id' => $userId
            ]);
            
            http_response_code(200);
            echo json_encode([
                'success' => true,
                'message' => 'Subscription reactivated successfully',
                'user_id' => $userId,
                'status' => 'updated'
            ]);
        } else {
            // Update existing active user
            $updateSql = "UPDATE users SET 
                         name = :name,
                         phone = COALESCE(:phone, phone),
                         email = COALESCE(:email, email),
                         location = COALESCE(:location, location),
                         subscription_type = :subscription_type
                         WHERE id = :id";
            
            $db->execute($updateSql, [
                'name' => $name,
                'phone' => $phone,
                'email' => $email,
                'location' => $location,
                'subscription_type' => $subscriptionType,
                'id' => $userId
            ]);
            
            http_response_code(200);
            echo json_encode([
                'success' => true,
                'message' => 'Subscription updated successfully',
                'user_id' => $userId,
                'status' => 'updated'
            ]);
        }
    } else {
        // New user - insert
        $insertSql = "INSERT INTO users (name, phone, email, location, subscription_type, is_active, created_at) 
                     VALUES (:name, :phone, :email, :location, :subscription_type, TRUE, NOW())";
        
        $result = $db->execute($insertSql, [
            'name' => $name,
            'phone' => $phone,
            'email' => $email,
            'location' => $location,
            'subscription_type' => $subscriptionType
        ]);
        
        if ($result) {
            $userId = $db->getLastInsertId();
            
            http_response_code(201);
            echo json_encode([
                'success' => true,
                'message' => 'Subscription successful! You will now receive weather alerts.',
                'user_id' => $userId,
                'status' => 'created',
                'welcome_message' => 'Welcome to Zambia Climate Early Warning System!'
            ]);
        } else {
            http_response_code(500);
            echo json_encode([
                'success' => false,
                'error' => 'Failed to create subscription'
            ]);
        }
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
