<?php
/**
 * API Endpoint: Predict Risk
 * Analyzes weather data and predicts disaster risks
 * Returns risk assessment for floods, droughts, and extreme temperatures
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
    
    // Get latest weather data for all regions
    $sql = "SELECT 
                r.id as region_id,
                r.name as region_name,
                AVG(w.temperature) as temperature,
                AVG(w.humidity) as humidity,
                SUM(w.rainfall) as total_rainfall,
                AVG(w.wind_speed) as wind_speed,
                -- Get rainfall trend (compare recent vs older data)
                (SELECT AVG(rainfall) FROM weather_data 
                 WHERE region_id = r.id AND timestamp > DATE_SUB(NOW(), INTERVAL 1 DAY)) as recent_rainfall,
                (SELECT AVG(rainfall) FROM weather_data 
                 WHERE region_id = r.id AND timestamp BETWEEN DATE_SUB(NOW(), INTERVAL 3 DAY) AND DATE_SUB(NOW(), INTERVAL 1 DAY)) as older_rainfall
            FROM regions r
            LEFT JOIN weather_data w ON r.id = w.region_id
            WHERE w.timestamp > DATE_SUB(NOW(), INTERVAL 1 DAY)
            GROUP BY r.id, r.name";
    
    $regionsData = $db->query($sql);
    
    $predictions = [];
    
    foreach ($regionsData as $region) {
        $riskLevel = RISK_LOW;
        $disasterType = 'general';
        $alerts = [];
        $confidenceScore = 0;
        
        $temperature = floatval($region['temperature']);
        $rainfall = floatval($region['total_rainfall']);
        $humidity = floatval($region['humidity']);
        $recentRainfall = floatval($region['recent_rainfall']);
        $olderRainfall = floatval($region['older_rainfall']);
        
        // ===== FLOOD RISK ASSESSMENT =====
        if ($rainfall >= FLOOD_RAINFALL_THRESHOLD) {
            $riskLevel = RISK_HIGH;
            $disasterType = 'flood';
            $confidenceScore = min(95, 60 + (($rainfall - FLOOD_RAINFALL_THRESHOLD) * 0.5));
            $alerts[] = "Heavy rainfall detected (" . round($rainfall, 1) . "mm). High flood risk in low-lying areas.";
            
            // Escalate to critical if rainfall is extremely high
            if ($rainfall >= 200) {
                $riskLevel = RISK_CRITICAL;
                $confidenceScore = min(98, $confidenceScore + 10);
                $alerts[] = "CRITICAL: Extreme rainfall levels. Immediate evacuation may be necessary.";
            }
        }
        
        // ===== DROUGHT RISK ASSESSMENT =====
        if ($temperature >= DROUGHT_TEMP_THRESHOLD && $rainfall < DROUGHT_RAINFALL_THRESHOLD) {
            $currentRisk = $riskLevel;
            $riskLevel = RISK_HIGH;
            $disasterType = 'drought';
            $confidenceScore = max($confidenceScore, min(95, 60 + (($temperature - DROUGHT_TEMP_THRESHOLD) * 2)));
            $alerts[] = "Extended dry period with high temperatures (" . round($temperature, 1) . "°C). Drought conditions developing.";
            
            // If already had a flood alert, this overrides (can't have both)
            if ($currentRisk === RISK_HIGH && $disasterType === 'flood') {
                // Keep the more severe threat
                if ($confidenceScore < 70) {
                    $riskLevel = RISK_HIGH;
                    $disasterType = 'drought';
                }
            }
        }
        
        // ===== EXTREME TEMPERATURE ASSESSMENT =====
        if ($temperature <= EXTREME_TEMP_MIN || $temperature >= EXTREME_TEMP_MAX) {
            if ($riskLevel === RISK_LOW) {
                $riskLevel = RISK_MEDIUM;
                $disasterType = 'extreme_temperature';
                $confidenceScore = max($confidenceScore, 75);
                
                if ($temperature <= EXTREME_TEMP_MIN) {
                    $alerts[] = "Extremely low temperature detected (" . round($temperature, 1) . "°C). Frost warning for agricultural areas.";
                } else {
                    $alerts[] = "Dangerously high temperature (" . round($temperature, 1) . "°C). Heat stroke risk. Stay hydrated.";
                }
            }
        }
        
        // ===== RAINFALL TREND ANALYSIS =====
        if ($recentRainfall > 0 && $olderRainfall > 0) {
            $rainfallTrend = (($recentRainfall - $olderRainfall) / $olderRainfall) * 100;
            
            if ($rainfallTrend > 50) { // 50% increase in rainfall
                if ($riskLevel === RISK_LOW || $riskLevel === RISK_MEDIUM) {
                    $riskLevel = RISK_MEDIUM;
                    $confidenceScore = max($confidenceScore, 65);
                    $alerts[] = "Rainfall increasing rapidly (" . round($rainfallTrend, 1) . "% trend). Monitor situation closely.";
                } elseif ($riskLevel === RISK_HIGH) {
                    $confidenceScore = min(98, $confidenceScore + 5);
                    $alerts[] = "Continued rainfall escalation. Situation worsening.";
                }
            }
        }
        
        // ===== HUMIDITY FACTOR =====
        if ($humidity >= 85 && $rainfall > 50) {
            $confidenceScore = min(98, $confidenceScore + 5);
            $alerts[] = "Very high humidity levels increase flood probability.";
        }
        
        // If no specific alerts, set default message
        if (empty($alerts)) {
            $alerts[] = "Normal weather conditions. No immediate threats detected.";
            $confidenceScore = 90;
        }
        
        $predictions[] = [
            'region_id' => $region['region_id'],
            'region_name' => $region['region_name'],
            'risk_level' => $riskLevel,
            'disaster_type' => $disasterType,
            'confidence_score' => round($confidenceScore, 2),
            'current_conditions' => [
                'temperature' => round($temperature, 1),
                'humidity' => round($humidity, 1),
                'rainfall' => round($rainfall, 1),
                'wind_speed' => round($region['wind_speed'], 1)
            ],
            'alerts' => $alerts,
            'recommendations' => getRecommendations($riskLevel, $disasterType)
        ];
    }
    
    // Generate summary
    $summary = generateRiskSummary($predictions);
    
    http_response_code(200);
    echo json_encode([
        'success' => true,
        'predictions' => $predictions,
        'summary' => $summary,
        'timestamp' => date('Y-m-d H:i:s'),
        'thresholds' => [
            'flood_rainfall_mm' => FLOOD_RAINFALL_THRESHOLD,
            'drought_temp_celsius' => DROUGHT_TEMP_THRESHOLD,
            'drought_rainfall_mm' => DROUGHT_RAINFALL_THRESHOLD,
            'extreme_temp_min' => EXTREME_TEMP_MIN,
            'extreme_temp_max' => EXTREME_TEMP_MAX
        ]
    ]);
    
} catch(Exception $e) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Prediction failed',
        'message' => $e->getMessage()
    ]);
}

/**
 * Get recommendations based on risk level and disaster type
 */
function getRecommendations($riskLevel, $disasterType) {
    $recommendations = [];
    
    switch($disasterType) {
        case 'flood':
            $recommendations[] = "Move to higher ground immediately";
            $recommendations[] = "Avoid crossing flooded roads or bridges";
            $recommendations[] = "Prepare emergency supplies and documents";
            $recommendations[] = "Stay tuned to local radio for updates";
            if ($riskLevel === RISK_CRITICAL) {
                $recommendations[] = "EVACUATE NOW - Follow official evacuation routes";
            }
            break;
            
        case 'drought':
            $recommendations[] = "Conserve water resources";
            $recommendations[] = "Limit outdoor activities during peak heat";
            $recommendations[] = "Ensure adequate hydration";
            $recommendations[] = "Protect livestock and crops";
            break;
            
        case 'extreme_temperature':
            $recommendations[] = "Stay indoors during extreme hours";
            $recommendations[] = "Keep windows covered during day, open at night";
            $recommendations[] = "Check on elderly and vulnerable neighbors";
            break;
            
        default:
            $recommendations[] = "Continue monitoring weather updates";
            $recommendations[] = "Prepare emergency contact numbers";
            break;
    }
    
    return $recommendations;
}

/**
 * Generate overall risk summary
 */
function generateRiskSummary($predictions) {
    $criticalCount = 0;
    $highCount = 0;
    $mediumCount = 0;
    $lowCount = 0;
    
    $affectedRegions = [];
    
    foreach ($predictions as $prediction) {
        switch($prediction['risk_level']) {
            case RISK_CRITICAL:
                $criticalCount++;
                $affectedRegions[] = $prediction['region_name'];
                break;
            case RISK_HIGH:
                $highCount++;
                $affectedRegions[] = $prediction['region_name'];
                break;
            case RISK_MEDIUM:
                $mediumCount++;
                break;
            default:
                $lowCount++;
                break;
        }
    }
    
    $overallRisk = RISK_LOW;
    if ($criticalCount > 0) {
        $overallRisk = RISK_CRITICAL;
    } elseif ($highCount > 0) {
        $overallRisk = RISK_HIGH;
    } elseif ($mediumCount > 0) {
        $overallRisk = RISK_MEDIUM;
    }
    
    return [
        'overall_risk_level' => $overallRisk,
        'critical_regions' => $criticalCount,
        'high_risk_regions' => $highCount,
        'medium_risk_regions' => $mediumCount,
        'low_risk_regions' => $lowCount,
        'total_regions_monitored' => count($predictions),
        'affected_region_names' => array_unique($affectedRegions)
    ];
}
?>
