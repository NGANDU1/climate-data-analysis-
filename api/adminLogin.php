<?php
/**
 * API Endpoint: Admin Login
 * Handles administrator authentication
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
    if (empty($input['username']) || empty($input['password'])) {
        http_response_code(400);
        echo json_encode([
            'success' => false,
            'error' => 'Username and password are required'
        ]);
        exit();
    }
    
    $username = htmlspecialchars(strip_tags(trim($input['username'])));
    $password = $input['password'];
    
    // Get admin user
    $sql = "SELECT id, username, password FROM admin WHERE username = :username LIMIT 1";
    $admin = $db->query($sql, ['username' => $username]);
    
    if ($admin && !empty($admin)) {
        $adminUser = $admin[0];
        
        // Verify password (using password_verify for hashed passwords)
        // Default password: admin123 (hashed in database)
        if (password_verify($password, $adminUser['password'])) {
            // Generate simple session token (in production, use proper JWT or session management)
            $token = bin2hex(random_bytes(32));
            
            // Store token in a real application (database/cache)
            // For demo purposes, we'll just return it
            
            http_response_code(200);
            echo json_encode([
                'success' => true,
                'message' => 'Login successful',
                'data' => [
                    'admin_id' => $adminUser['id'],
                    'username' => $adminUser['username'],
                    'token' => $token,
                    'expires_in' => 3600 // 1 hour
                ]
            ]);
        } else {
            http_response_code(401);
            echo json_encode([
                'success' => false,
                'error' => 'Invalid credentials'
            ]);
        }
    } else {
        http_response_code(401);
        echo json_encode([
            'success' => false,
            'error' => 'Invalid credentials'
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
