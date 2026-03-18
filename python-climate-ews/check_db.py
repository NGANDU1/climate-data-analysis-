from app import create_app
from models import db
from models.region import Region
from models.weather_data import WeatherData

app = create_app()

with app.app_context():
    regions_count = Region.query.count()
    weather_count = WeatherData.query.count()
    
    print(f"✓ Database Status:")
    print(f"  - Regions: {regions_count}")
    print(f"  - Weather Records: {weather_count}")
    
   if regions_count > 0:
        print(f"\n✓ Sample Regions:")
       for region in Region.query.limit(5).all():
            print(f"  - {region.name} (Province: {region.province})")
    else:
        print("\n✗ No regions found! Run: py seed_database.py")
    
   if weather_count > 0:
        print(f"\n✓ Weather data available")
    else:
        print("\n✗ No weather data! Check OpenWeatherMap API key")
