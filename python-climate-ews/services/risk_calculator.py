from datetime import datetime

class RiskCalculator:
    """Calculate disaster risk levels based on weather data"""
    
    @staticmethod
    def predict_risk(data):
        """
        Predict risk level based on weather parameters
        
        Args:
            data: dict containing temperature, humidity, rainfall, region_name
            
        Returns:
            dict with risk_level, disaster_type, confidence_score, alerts, recommendations
        """
        temp = data.get('temperature', 0)
        humidity = data.get('humidity', 0)
        rainfall = data.get('rainfall', 0)
        
        # Initialize risk assessment
        risk_level = 'low'
        disaster_type = 'general'
        confidence_score = 0.5
        alerts = []
        recommendations = []
        
        # Flood risk assessment
        if rainfall > 100:
            risk_level = 'critical'
            disaster_type = 'flood'
            confidence_score = min(0.9, rainfall / 200)
            alerts.append(f'Heavy rainfall detected: {rainfall:.1f}mm')
            recommendations.append('Evacuate low-lying areas immediately')
            recommendations.append('Prepare emergency shelters')
            
        elif rainfall > 50:
            risk_level = 'high'
            disaster_type = 'flood'
            confidence_score = min(0.8, rainfall / 100)
            alerts.append(f'Moderate to heavy rainfall: {rainfall:.1f}mm')
            recommendations.append('Monitor water levels closely')
            recommendations.append('Prepare drainage systems')
            
        # Drought risk assessment
        elif temp > 35 and rainfall < 10:
            risk_level = 'high'
            disaster_type = 'drought'
            confidence_score = min(0.85, temp / 45)
            alerts.append(f'High temperature with low rainfall: {temp:.1f}°C')
            recommendations.append('Conserve water resources')
            recommendations.append('Prepare for potential water rationing')
            
        elif temp > 30 and rainfall < 20:
            risk_level = 'medium'
            disaster_type = 'drought'
            confidence_score = 0.6
            alerts.append(f'Elevated temperature: {temp:.1f}°C')
            recommendations.append('Monitor soil moisture levels')
            
        # Extreme temperature assessment
        elif temp > 40:
            risk_level = 'high'
            disaster_type = 'extreme_heat'
            confidence_score = min(0.9, temp / 50)
            alerts.append(f'Extreme heat warning: {temp:.1f}°C')
            recommendations.append('Avoid outdoor activities during peak hours')
            recommendations.append('Stay hydrated and seek cool environments')
            
        elif temp < 5:
            risk_level = 'medium'
            disaster_type = 'extreme_cold'
            confidence_score = 0.7
            alerts.append(f'Low temperature alert: {temp:.1f}°C')
            recommendations.append('Prepare for cold weather conditions')
            
        # High wind assessment
        elif humidity > 80 and temp > 25:
            risk_level = 'medium'
            disaster_type = 'storm'
            confidence_score = 0.6
            alerts.append(f'High humidity and temperature may indicate storm formation')
            recommendations.append('Monitor weather forecasts closely')
            
        # Normal conditions
        else:
            risk_level = 'low'
            disaster_type = 'general'
            confidence_score = 0.5
            recommendations.append('Continue regular monitoring')
        
        return {
            'risk_level': risk_level,
            'disaster_type': disaster_type,
            'confidence_score': round(confidence_score, 2),
            'alerts': alerts,
            'recommendations': recommendations,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def predict_risk_for_region(region):
        """
        Predict risk for a specific region using recent weather data
        
        Args:
            region: Region object
            
        Returns:
            dict with risk prediction
        """
        from models import db
        from models.weather_data import WeatherData
        
        # Get recent weather data (last 3 readings)
        recent_weather = WeatherData.query.filter_by(
            region_id=region.id
        ).order_by(WeatherData.timestamp.desc()).limit(3).all()
        
        if not recent_weather:
            return {
                'risk_level': 'unknown',
                'disaster_type': 'general',
                'confidence_score': 0.0,
                'alerts': ['No weather data available'],
                'recommendations': ['Install weather monitoring equipment']
            }
        
        # Calculate averages
        avg_temp = sum(w.temperature for w in recent_weather) / len(recent_weather)
        avg_humidity = sum(w.humidity for w in recent_weather) / len(recent_weather)
        total_rainfall = sum(w.rainfall for w in recent_weather)
        
        # Predict risk
        prediction = RiskCalculator.predict_risk({
            'temperature': avg_temp,
            'humidity': avg_humidity,
            'rainfall': total_rainfall,
            'region_name': region.name
        })
        
        return prediction
    
    @staticmethod
    def calculate_aggregate_risk(regions_data):
        """
        Calculate aggregate risk across multiple regions
        
        Args:
            regions_data: list of region risk predictions
            
        Returns:
            dict with overall risk assessment
        """
        if not regions_data:
            return {'overall_risk': 'unknown', 'affected_regions': []}
        
        critical_count = sum(1 for r in regions_data if r['risk_level'] == 'critical')
        high_count = sum(1 for r in regions_data if r['risk_level'] == 'high')
        medium_count = sum(1 for r in regions_data if r['risk_level'] == 'medium')
        
        affected_regions = [
            r.get('region_name', 'Unknown') 
            for r in regions_data 
            if r['risk_level'] in ['critical', 'high']
        ]
        
        if critical_count > 0:
            overall_risk = 'critical'
        elif high_count > 0:
            overall_risk = 'high'
        elif medium_count > 0:
            overall_risk = 'medium'
        else:
            overall_risk = 'low'
        
        return {
            'overall_risk': overall_risk,
            'critical_regions': critical_count,
            'high_risk_regions': high_count,
            'medium_risk_regions': medium_count,
            'low_risk_regions': len(regions_data) - critical_count - high_count - medium_count,
            'affected_regions': affected_regions,
            'total_regions': len(regions_data)
        }
