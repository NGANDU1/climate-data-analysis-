<?php
/**
 * Database Connection Class
 * PDO-based database connection for Climate EWS
 */

class Database {
    private $host = DB_HOST;
    private $db_name = DB_NAME;
    private $username = DB_USER;
    private $password = DB_PASS;
    private $charset = DB_CHARSET;
    
    private $conn;
    
    /**
     * Get database connection
     */
    public function getConnection() {
        $this->conn = null;
        
        try {
            $dsn = "mysql:host={$this->host};dbname={$this->db_name};charset={$this->charset}";
            $options = [
                PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                PDO::ATTR_EMULATE_PREPARES => false,
                PDO::MYSQL_ATTR_INIT_COMMAND => "SET NAMES utf8mb4"
            ];
            
            $this->conn = new PDO($dsn, $this->username, $this->password, $options);
            
        } catch(PDOException $e) {
            // Log error in production, display in development
            if (getenv('APP_ENV') === 'production') {
                http_response_code(500);
                echo json_encode(['error' => 'Database connection failed']);
            } else {
                http_response_code(500);
                echo json_encode([
                    'error' => 'Database connection failed',
                    'message' => $e->getMessage()
                ]);
            }
        }
        
        return $this->conn;
    }
    
    /**
     * Execute a query and return results
     */
    public function query($sql, $params = []) {
        try {
            $stmt = $this->getConnection()->prepare($sql);
            $stmt->execute($params);
            return $stmt->fetchAll();
        } catch(PDOException $e) {
            error_log("Query error: " . $e->getMessage());
            return false;
        }
    }
    
    /**
     * Execute insert/update/delete and return affected rows
     */
    public function execute($sql, $params = []) {
        try {
            $stmt = $this->getConnection()->prepare($sql);
            $stmt->execute($params);
            return $stmt->rowCount();
        } catch(PDOException $e) {
            error_log("Execute error: " . $e->getMessage());
            return false;
        }
    }
    
    /**
     * Get last inserted ID
     */
    public function getLastInsertId() {
        return $this->getConnection()->lastInsertId();
    }
}
?>
