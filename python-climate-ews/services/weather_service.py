from datetime import datetime, timedelta
import random

class WeatherService:
    """Weather data processing and management"""
    
    @staticmethod
    def get_latest_weather(region_id=None):
        """
        Get latest weather data
        
        Args:
            region_id: Optional region ID filter
            
        Returns:
            Query results of latest weather data
        """
        from models.weather_data import WeatherData
        from models.region import Region
        
        if region_id:
            weather = WeatherData.query.filter_by(
                region_id=region_id
            ).order_by(WeatherData.timestamp.desc()).first()
            return weather
        else:
            # Get latest for each region
            latest = []
            regions = Region.query.all()
            
            for region in regions:
                weather = WeatherData.query.filter_by(
                    region_id=region.id
                ).order_by(WeatherData.timestamp.desc()).first()
                
                if weather:
                    latest.append(weather)
            
            return latest
    
    @staticmethod
    def get_weather_history(region_id, days=7):
        """
        Get weather history for a region
        
        Args:
            region_id: Region ID
            days: Number of days to retrieve
            
        Returns:
            List of weather data
        """
        from models.weather_data import WeatherData
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        weather_data = WeatherData.query.filter(
            WeatherData.region_id == region_id,
            WeatherData.timestamp >= cutoff_date
        ).order_by(WeatherData.timestamp.desc()).all()
        
        return weather_data
    
    @staticmethod
    def generate_sample_data(region_id, num_readings=24):
        """
        Generate sample weather data for testing
        
        Args:
            region_id: Region ID to generate data for
            num_readings: Number of readings to generate
            
        Returns:
            List of generated readings
        """
        from models import db
        from models.weather_data import WeatherData
        
        readings = []
        base_time = datetime.utcnow()
        
        # Zambia typical weather ranges
        temp_range = (15, 35)  # Celsius
        humidity_range = (40, 90)  # Percentage
        rainfall_range = (0, 150)  # mm
        wind_speed_range = (5, 30)  # km/h
        pressure_range = (1010, 1020)  # hPa
        
        for i in range(num_readings):
            # Create reading every hour
            timestamp = base_time - timedelta(hours=num_readings - i)
            
            reading = WeatherData(
                region_id=region_id,
                temperature=random.uniform(*temp_range),
                humidity=random.uniform(*humidity_range),
                rainfall=random.uniform(*rainfall_range),
                wind_speed=random.uniform(*wind_speed_range),
                pressure=random.uniform(*pressure_range),
                timestamp=timestamp
            )
            
            readings.append(reading)
        
        return readings
    
    @staticmethod
    def calculate_statistics(weather_data):
        """
        Calculate statistics from weather data
        
        Args:
            weather_data: List of WeatherData objects
            
        Returns:
            Dict with statistics
        """
        if not weather_data:
            return {
                'avg_temperature': 0,
                'max_temperature': 0,
                'min_temperature': 0,
                'avg_humidity': 0,
                'total_rainfall': 0,
                'avg_wind_speed': 0
            }
        
        temps = [w.temperature for w in weather_data]
        humidities = [w.humidity for w in weather_data]
        rainfalls = [w.rainfall for w in weather_data]
        winds = [w.wind_speed for w in weather_data]
        
        return {
            'avg_temperature': sum(temps) / len(temps),
            'max_temperature': max(temps),
            'min_temperature': min(temps),
            'avg_humidity': sum(humidities) / len(humidities),
            'total_rainfall': sum(rainfalls),
            'avg_wind_speed': sum(winds) / len(winds),
            'reading_count': len(weather_data)
        }
    
    @staticmethod
    def detect_anomalies(weather_data, threshold_std=2.0):
        """
        Detect anomalies in weather data
        
        Args:
            weather_data: List of WeatherData objects
            threshold_std: Standard deviations for anomaly detection
            
        Returns:
            List of anomalous readings
        """
        if len(weather_data) < 3:
            return []
        
        import numpy as np
        
        temps = np.array([w.temperature for w in weather_data])
        rainfalls = np.array([w.rainfall for w in weather_data])
        
        temp_mean = np.mean(temps)
        temp_std = np.std(temps)
        rainfall_mean = np.mean(rainfalls)
        rainfall_std = np.std(rainfalls)
        
        anomalies = []
        
        for reading in weather_data:
            is_anomaly = False
            reasons = []
            
            # Check temperature anomaly
            if abs(reading.temperature - temp_mean) > threshold_std * temp_std:
                is_anomaly = True
                reasons.append(f'Unusual temperature: {reading.temperature:.1f}°C')
            
            # Check rainfall anomaly
            if abs(reading.rainfall - rainfall_mean) > threshold_std * rainfall_std:
                is_anomaly = True
                reasons.append(f'Unusual rainfall: {reading.rainfall:.1f}mm')
            
            if is_anomaly:
                anomalies.append({
                    'reading': reading.to_dict(),
                    'reasons': reasons
                })
        
        return anomalies
