"""
OpenWeatherMap API Integration Service
Fetches real-time and historical weather data from OpenWeatherMap API
"""

import requests
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd


class OpenWeatherMapService:
    """Service for fetching weather data from OpenWeatherMap API"""
    
   def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenWeatherMap service
        
        Args:
            api_key: OpenWeatherMap API key (defaults to env variable)
        """
        self.api_key = api_key or os.getenv('OPENWEATHER_API_KEY')
        self.base_url = 'https://api.openweathermap.org/data/2.5'
        
        if not self.api_key:
            raise ValueError(
                "OpenWeatherMap API key not provided. "
                "Set OPENWEATHER_API_KEY environment variable or pass api_key parameter."
            )
    
   def get_current_weather(self, lat: float, lon: float) -> Dict:
        """
        Get current weather for coordinates
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Dictionary with current weather data
        """
        endpoint = f'{self.base_url}/weather'
        params = {
            'lat': lat,
            'lon': lon,
            'appid': self.api_key,
            'units': 'metric'  # Celsius
        }
        
       response = requests.get(endpoint, params=params)
       response.raise_for_status()
        
        data = response.json()
        
       return {
            'temperature': data['main']['temp'],
            'humidity': data['main']['humidity'],
            'pressure': data['main']['pressure'],
            'wind_speed': data['wind']['speed'],
            'description': data['weather'][0]['description'],
            'timestamp': datetime.utcnow()
        }
    
   def get_forecast(self, lat: float, lon: float, days: int = 5) -> List[Dict]:
        """
        Get weather forecast
        
        Args:
            lat: Latitude
            lon: Longitude
            days: Number of days (max 5)
            
        Returns:
            List of forecast data points
        """
        endpoint = f'{self.base_url}/forecast'
        params = {
            'lat': lat,
            'lon': lon,
            'appid': self.api_key,
            'units': 'metric'
        }
        
       response = requests.get(endpoint, params=params)
       response.raise_for_status()
        
        data = response.json()
        
        forecasts = []
        for item in data['list'][:days*8]:  # 3-hour intervals, 8 per day
            forecasts.append({
                'temperature': item['main']['temp'],
                'humidity': item['main']['humidity'],
                'pressure': item['main']['pressure'],
                'wind_speed': item['wind']['speed'],
                'description': item['weather'][0]['description'],
                'timestamp': datetime.strptime(item['dt_txt'], '%Y-%m-%d %H:%M:%S')
            })
        
       return forecasts
    
   def get_historical_data(self, lat: float, lon: float, 
                         start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Get historical weather data (requires One Call API 3.0)
        
        Args:
            lat: Latitude
            lon: Longitude
           start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with historical data
        """
        # Note: Historical data requires One Call API 3.0 subscription
        # Free tier only provides current and forecast
        
        endpoint = 'https://api.openweathermap.org/data/3.0/onecall/timemachine'
        
        all_data = []
        current_date = start_date
        
        while current_date <= end_date:
            params = {
                'lat': lat,
                'lon': lon,
                'dt': int(current_date.timestamp()),
                'appid': self.api_key,
                'units': 'metric'
            }
            
            try:
               response = requests.get(endpoint, params=params)
               response.raise_for_status()
                data = response.json()
                
                if 'data' in data:
                    for item in data['data']:
                        all_data.append({
                            'temperature': item['temp'],
                            'humidity': item.get('humidity', 0),
                            'pressure': item.get('pressure', 0),
                            'wind_speed': item.get('wind_speed', 0),
                            'timestamp': datetime.fromtimestamp(item['dt'])
                        })
            except Exception as e:
                print(f"Error fetching historical data for {current_date}: {e}")
            
            current_date += timedelta(days=1)
        
       return pd.DataFrame(all_data) if all_data else pd.DataFrame()
    
   def fetch_zambia_regions_data(self, regions: List[Dict]) -> Dict[str, Dict]:
        """
        Fetch current weather for all Zambian regions
        
        Args:
           regions: List of region dicts with name, latitude, longitude
            
        Returns:
            Dictionary mapping region names to weather data
        """
       results = {}
        
        for region in regions:
            try:
                weather = self.get_current_weather(
                   region['latitude'],
                   region['longitude']
                )
               results[region['name']] = weather
            except Exception as e:
                print(f"Error fetching data for {region['name']}: {e}")
               results[region['name']] = None
        
       return results


class NOAADataLoader:
    """Load historical weather data from NOAA datasets"""
    
    @staticmethod
   def load_csv(file_path: str) -> pd.DataFrame:
        """
        Load NOAA CSV dataset
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            DataFrame with weather data
        """
        try:
            df = pd.read_csv(file_path)
            
            # Standardize column names
            column_mapping = {
                'DATE': 'timestamp',
                'TEMP': 'temperature',
                'PRCP': 'precipitation',
                'AWND': 'wind_speed',
                'PRES': 'pressure',
                'RH': 'humidity'
            }
            
            df = df.rename(columns=column_mapping)
            
            # Convert timestamp
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            
           return df
            
        except Exception as e:
            print(f"Error loading NOAA data: {e}")
           return pd.DataFrame()
    
    @staticmethod
   def load_kaggle_dataset(file_path: str) -> pd.DataFrame:
        """
        Load Kaggle weather dataset
        
        Args:
            file_path: Path to dataset file
            
        Returns:
            DataFrame with weather data
        """
        try:
            df = pd.read_csv(file_path)
            
            # Common Kaggle dataset columns
            expected_columns = [
                'Date', 'Temperature', 'Humidity', 
                'Rainfall', 'WindSpeed'
            ]
            
            # Check if all expected columns exist
            if all(col in df.columns for col in expected_columns):
                df = df.rename(columns={
                    'Date': 'timestamp',
                    'Temperature': 'temperature',
                    'Humidity': 'humidity',
                    'Rainfall': 'rainfall',
                    'WindSpeed': 'wind_speed'
                })
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            
           return df
            
        except Exception as e:
            print(f"Error loading Kaggle dataset: {e}")
           return pd.DataFrame()


class DataIngestionPipeline:
    """Pipeline for ingesting weather data from multiple sources"""
    
   def __init__(self, openweather_api_key: Optional[str] = None):
        """Initialize data ingestion pipeline"""
        self.openweather_service = OpenWeatherMapService(openweather_api_key)
    
   def ingest_real_time_data(self, regions: List[Dict]) -> pd.DataFrame:
        """
        Ingest real-time weather data for all regions
        
        Args:
           regions: List of region configurations
            
        Returns:
            DataFrame with all weather data
        """
        print("Fetching real-time weather data...")
        
        weather_data = self.openweather_service.fetch_zambia_regions_data(regions)
        
        # Convert to DataFrame
       records = []
        for region_name, data in weather_data.items():
            if data:
               record = data.copy()
               record['region'] = region_name
               records.append(record)
        
        df = pd.DataFrame(records)
        print(f"Ingested {len(df)} real-time records")
        
       return df
    
   def ingest_historical_data(self, source: str, file_path: str) -> pd.DataFrame:
        """
        Ingest historical weather data
        
        Args:
            source: Data source ('noaa' or 'kaggle')
            file_path: Path to data file
            
        Returns:
            DataFrame with historical data
        """
        print(f"Loading historical data from {source}...")
        
        if source.lower() == 'noaa':
            df = NOAADataLoader.load_csv(file_path)
        elif source.lower() == 'kaggle':
            df = NOAADataLoader.load_kaggle_dataset(file_path)
        else:
            raise ValueError(f"Unknown data source: {source}")
        
        print(f"Loaded {len(df)} historical records")
        
       return df
    
   def merge_datasets(self, real_time_df: pd.DataFrame, 
                      historical_df: pd.DataFrame) -> pd.DataFrame:
        """
        Merge real-time and historical datasets
        
        Args:
           real_time_df: Real-time weather data
            historical_df: Historical weather data
            
        Returns:
            Merged DataFrame
        """
        # Combine datasets
        merged = pd.concat([historical_df, real_time_df], ignore_index=True)
        
        # Sort by timestamp
        if 'timestamp' in merged.columns:
            merged = merged.sort_values('timestamp')
        
        # Remove duplicates
        merged = merged.drop_duplicates()
        
        print(f"Merged dataset contains {len(merged)} total records")
        
       return merged
    
   def save_to_database(self, df: pd.DataFrame, db_session):
        """
        Save ingested data to database
        
        Args:
            df: Weather data DataFrame
            db_session: SQLAlchemy database session
        """
        from models.weather_data import WeatherData
        from models.region import Region
        
        saved_count = 0
        
        for _, row in df.iterrows():
            # Find region
           region = Region.query.filter_by(name=row.get('region', '')).first()
            
            if not region:
                continue
            
            # Create weather data record
            weather = WeatherData(
               region_id=region.id,
                temperature=row.get('temperature'),
                humidity=row.get('humidity'),
                rainfall=row.get('rainfall', 0),
                wind_speed=row.get('wind_speed', 0),
                pressure=row.get('pressure', 0),
                timestamp=row.get('timestamp', datetime.utcnow())
            )
            
            db_session.add(weather)
            saved_count += 1
        
        db_session.commit()
        print(f"Saved {saved_count} records to database")


# Example usage
if __name__ == '__main__':
    # Example: Fetch real-time data for Zambia
    zambia_regions = [
        {'name': 'Lusaka', 'latitude': -15.4167, 'longitude': 28.2833},
        {'name': 'Copperbelt', 'latitude': -12.9333, 'longitude': 28.6333},
        {'name': 'Southern', 'latitude': -16.5000, 'longitude': 27.5000},
    ]
    
    # Requires API key
    # service = OpenWeatherMapService()
    # data = service.fetch_zambia_regions_data(zambia_regions)
    # print(data)
