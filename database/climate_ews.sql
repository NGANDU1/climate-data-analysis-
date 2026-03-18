-- ============================================
-- Climate Early Warning System Database
-- For Zambia Climate Monitoring
-- ============================================

CREATE DATABASE IF NOT EXISTS climate_ews_zambia;
USE climate_ews_zambia;

-- ============================================
-- Table: admin
-- Stores administrator credentials
-- ============================================
CREATE TABLE IF NOT EXISTS admin (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default admin user (username: admin, password: admin123)
INSERT INTO admin (username, password) VALUES 
('admin', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi');

-- ============================================
-- Table: users
-- Stores subscribed users for alerts
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(100),
    location VARCHAR(100),
    subscription_type ENUM('sms', 'email', 'both') DEFAULT 'email',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- Table: regions
-- Zambia provinces/regions for monitoring
-- ============================================
CREATE TABLE IF NOT EXISTS regions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    risk_level ENUM('low', 'medium', 'high', 'critical') DEFAULT 'low'
);

-- Insert Zambia provinces with approximate coordinates
INSERT INTO regions (name, latitude, longitude, risk_level) VALUES
('Lusaka', -15.3875, 28.3228, 'low'),
('Copperbelt', -12.9500, 28.6333, 'low'),
('Eastern', -13.8500, 32.7500, 'medium'),
('Northern', -10.4833, 32.0833, 'low'),
('Southern', -16.5000, 27.5000, 'medium'),
('Central', -14.5000, 28.0000, 'low'),
('North-Western', -12.0500, 26.0000, 'low'),
('Luapula', -11.2500, 29.0000, 'medium'),
('Muchinga', -10.5000, 32.5000, 'low'),
('Western', -15.5000, 23.0000, 'high');

-- ============================================
-- Table: weather_data
-- Stores historical and current weather data
-- ============================================
CREATE TABLE IF NOT EXISTS weather_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    region_id INT,
    temperature DECIMAL(5, 2),
    humidity DECIMAL(5, 2),
    rainfall DECIMAL(6, 2),
    wind_speed DECIMAL(5, 2),
    pressure DECIMAL(6, 2),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (region_id) REFERENCES regions(id) ON DELETE CASCADE
);

-- Insert sample weather data for all regions (realistic Zambia climate data)
INSERT INTO weather_data (region_id, temperature, humidity, rainfall, wind_speed, pressure) VALUES
-- Lusaka (Hot, moderate rainfall)
(1, 28.5, 65.0, 45.2, 12.5, 1013.2),
(1, 29.0, 68.0, 52.3, 10.2, 1012.8),
(1, 27.8, 70.0, 38.5, 11.0, 1013.5),

-- Copperbelt (Moderate temperature, good rainfall)
(2, 25.5, 72.0, 68.5, 8.5, 1015.0),
(2, 26.0, 75.0, 72.3, 9.0, 1014.5),
(2, 24.8, 70.0, 65.0, 7.8, 1015.2),

-- Eastern (Warm, variable rainfall)
(3, 30.2, 58.0, 25.5, 15.2, 1011.5),
(3, 31.5, 55.0, 18.2, 16.0, 1010.8),
(3, 32.0, 52.0, 12.5, 17.5, 1010.2),

-- Northern (Cooler, moderate rainfall)
(4, 22.5, 78.0, 85.2, 6.5, 1016.5),
(4, 23.0, 76.0, 78.5, 7.0, 1016.0),
(4, 21.8, 80.0, 92.0, 5.8, 1017.0),

-- Southern (Hot, low rainfall - drought prone)
(5, 33.5, 45.0, 8.5, 18.0, 1009.5),
(5, 34.2, 42.0, 5.2, 19.5, 1008.8),
(5, 35.0, 40.0, 3.5, 20.0, 1008.2),

-- Central (Moderate conditions)
(6, 26.5, 68.0, 55.2, 10.5, 1013.8),
(6, 27.0, 65.0, 48.5, 11.2, 1013.2),
(6, 25.8, 70.0, 62.0, 9.8, 1014.0),

-- North-Western (Good rainfall)
(7, 24.5, 75.0, 95.5, 7.5, 1015.5),
(7, 25.0, 73.0, 88.2, 8.0, 1015.0),
(7, 23.8, 77.0, 102.5, 6.8, 1016.0),

-- Luapula (High rainfall area)
(8, 23.5, 80.0, 125.5, 5.5, 1016.8),
(8, 24.0, 78.0, 118.2, 6.0, 1016.2),
(8, 22.8, 82.0, 135.0, 4.8, 1017.5),

-- Muchinga (Moderate rainfall)
(9, 25.5, 70.0, 62.5, 9.5, 1014.5),
(9, 26.0, 68.0, 58.2, 10.0, 1014.0),
(9, 24.8, 72.0, 68.0, 8.8, 1015.0),

-- Western (Flood prone - high rainfall)
(10, 28.5, 85.0, 185.5, 12.5, 1010.5),
(10, 29.0, 88.0, 195.2, 13.0, 1009.8),
(10, 27.8, 90.0, 210.0, 11.8, 1009.2);

-- ============================================
-- Table: alerts
-- Stores all generated alerts
-- ============================================
CREATE TABLE IF NOT EXISTS alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message TEXT NOT NULL,
    risk_level ENUM('low', 'medium', 'high', 'critical') NOT NULL,
    disaster_type ENUM('flood', 'drought', 'extreme_temperature', 'storm', 'general') DEFAULT 'general',
    region_id INT,
    is_manual BOOLEAN DEFAULT FALSE,
    is_sent BOOLEAN DEFAULT FALSE,
    sent_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (region_id) REFERENCES regions(id) ON DELETE CASCADE
);

-- Insert some sample alerts
INSERT INTO alerts (message, risk_level, disaster_type, region_id, is_manual) VALUES
('Heavy rainfall detected in Western Province. Risk of flooding in low-lying areas.', 'high', 'flood', 10, FALSE),
('Extended dry period in Southern Province. Drought conditions developing.', 'high', 'drought', 5, FALSE),
('Extreme temperatures expected in Eastern Province. Temperatures may exceed 35°C.', 'medium', 'extreme_temperature', 3, FALSE),
('Normal weather conditions in Lusaka. No immediate threats.', 'low', 'general', 1, FALSE);

-- ============================================
-- Table: risk_predictions
-- Stores AI/ML model predictions (future use)
-- ============================================
CREATE TABLE IF NOT EXISTS risk_predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    region_id INT,
    predicted_risk_level ENUM('low', 'medium', 'high', 'critical'),
    confidence_score DECIMAL(5, 2),
    prediction_date DATE,
    actual_outcome TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (region_id) REFERENCES regions(id) ON DELETE CASCADE
);

-- ============================================
-- View: Current Weather Summary
-- ============================================
CREATE OR REPLACE VIEW current_weather_summary AS
SELECT 
    r.name as region_name,
    AVG(w.temperature) as avg_temperature,
    AVG(w.humidity) as avg_humidity,
    SUM(w.rainfall) as total_rainfall,
    r.risk_level
FROM regions r
LEFT JOIN weather_data w ON r.id = w.region_id
GROUP BY r.id, r.name, r.risk_level;

-- ============================================
-- Indexes for performance
-- ============================================
CREATE INDEX idx_weather_timestamp ON weather_data(timestamp);
CREATE INDEX idx_alerts_created ON alerts(created_at);
CREATE INDEX idx_alerts_risk ON alerts(risk_level);
CREATE INDEX idx_regions_risk ON regions(risk_level);

-- ============================================
-- Sample Queries (for reference)
-- ============================================
-- Get latest weather for all regions
-- SELECT * FROM current_weather_summary;

-- Get recent alerts
-- SELECT a.*, r.name as region_name FROM alerts a 
-- LEFT JOIN regions r ON a.region_id = r.id 
-- ORDER BY a.created_at DESC LIMIT 10;

-- Get weather trends for a region
-- SELECT * FROM weather_data WHERE region_id = 1 
-- ORDER BY timestamp DESC LIMIT 24;
