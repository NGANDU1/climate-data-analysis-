from datetime import datetime, timedelta
import math
import random

class DataSeeder:
    """Database seeding utilities"""
    
    @staticmethod
    def seed_regions():
        """Seed Zambia provinces/regions"""
        from models import db
        from models.region import Region
        
        zambia_regions = [
            {'name': 'Lusaka', 'latitude': -15.4167, 'longitude': 28.2833},
            {'name': 'Copperbelt', 'latitude': -12.9333, 'longitude': 28.6333},
            {'name': 'Central', 'latitude': -14.5000, 'longitude': 28.0000},
            {'name': 'Eastern', 'latitude': -13.5000, 'longitude': 32.0000},
            {'name': 'Luapula', 'latitude': -11.0000, 'longitude': 29.0000},
            {'name': 'Northern', 'latitude': -10.5000, 'longitude': 31.0000},
            {'name': 'North-Western', 'latitude': -13.0000, 'longitude': 25.0000},
            {'name': 'Southern', 'latitude': -16.5000, 'longitude': 27.5000},
            {'name': 'Western', 'latitude': -15.5000, 'longitude': 23.0000},
            {'name': 'Muchinga', 'latitude': -11.5000, 'longitude': 31.5000}
        ]
        
        seeded_regions = []
        
        for region_data in zambia_regions:
            region = Region.query.filter_by(name=region_data['name']).first()
            
            if not region:
                region = Region(
                    name=region_data['name'],
                    latitude=region_data['latitude'],
                    longitude=region_data['longitude'],
                    risk_level='low'
                )
                db.session.add(region)
                seeded_regions.append(region)
        
        db.session.commit()
        
        return seeded_regions if seeded_regions else Region.query.all()
    
    @staticmethod
    def seed_weather_data(regions=None, days_back=30):
        """
        Seed weather data for regions
        
        Args:
            regions: List of Region objects (defaults to all regions)
            days_back: Number of days to generate data for
            
        Returns:
            Number of readings created
        """
        from models import db
        from models.weather_data import WeatherData
        
        if not regions:
            from models.region import Region
            regions = Region.query.all()
        
        total_readings = 0
        
        for region in regions:
            # Check if data already exists
            existing = WeatherData.query.filter_by(region_id=region.id).count()
            
            if existing > 0:
                continue
            
            # Generate hourly readings for specified days
            readings_per_day = 24
            total_readings_for_region = days_back * readings_per_day
            
            base_time = datetime.utcnow()
            
            # Zambia weather characteristics by region
            region_factors = {
                'Lusaka': {'temp_mod': 0, 'rain_mod': 1.0},
                'Copperbelt': {'temp_mod': -2, 'rain_mod': 1.2},
                'Southern': {'temp_mod': 2, 'rain_mod': 0.8},
                'Northern': {'temp_mod': -3, 'rain_mod': 1.3},
            }
            
            factors = region_factors.get(region.name, {'temp_mod': 0, 'rain_mod': 1.0})
            
            for i in range(total_readings_for_region):
                hours_ago = total_readings_for_region - i
                timestamp = base_time - timedelta(hours=hours_ago)
                
                # Base values with some randomness and regional adjustment
                base_temp = 25 + factors['temp_mod']
                base_rainfall = 20 * factors['rain_mod']
                
                # Add time-based variation (cooler at night)
                hour_of_day = timestamp.hour
                temp_variation = -5 if hour_of_day < 6 or hour_of_day > 18 else 0
                
                # Add seasonal variation
                day_of_year = timestamp.timetuple().tm_yday
                seasonal_var = 3 * math.sin(2 * math.pi * day_of_year / 365)
                
                reading = WeatherData(
                    region_id=region.id,
                    temperature=base_temp + temp_variation + seasonal_var + random.uniform(-3, 3),
                    humidity=random.uniform(50, 85),
                    rainfall=max(0, base_rainfall + random.uniform(-15, 25)),
                    wind_speed=random.uniform(8, 25),
                    pressure=random.uniform(1012, 1018),
                    timestamp=timestamp
                )
                
                db.session.add(reading)
                total_readings += 1
        
        db.session.commit()
        
        return total_readings
    
    @staticmethod
    def seed_admin_user():
        """Seed default admin user"""
        from models import db
        from models.admin import Admin
        
        default_username = "admin@123"
        default_password = "admin123"

        # Prefer the new default username; if an old "admin" record exists, rename it.
        admin = Admin.query.filter_by(username=default_username).first()
        if admin:
            admin.set_password(default_password)
            db.session.commit()
            return admin, False

        legacy_admin = Admin.query.filter_by(username="admin").first()
        if legacy_admin:
            legacy_admin.username = default_username
            legacy_admin.set_password(default_password)
            db.session.commit()
            return legacy_admin, False

        admin = Admin(username=default_username)
        admin.set_password(default_password)
        db.session.add(admin)
        db.session.commit()

        return admin, True  # Return admin and flag that it was created
    
    @staticmethod
    def seed_sample_users(count=10):
        """Seed sample subscribed users"""
        from models import db
        from models.user import User
        
        sample_users = [
            {'name': 'John Phiri', 'phone': '+260977123456', 'email': 'john.phiri@example.com', 'location': 'Lusaka'},
            {'name': 'Mary Banda', 'phone': '+260966234567', 'email': 'mary.banda@example.com', 'location': 'Ndola'},
            {'name': 'Peter Chanda', 'phone': '+260955345678', 'email': 'peter.chanda@example.com', 'location': 'Kitwe'},
            {'name': 'Grace Mulenga', 'phone': '+260944456789', 'email': 'grace.mulenga@example.com', 'location': 'Livingstone'},
            {'name': 'Daniel Mwamba', 'phone': '+260933567890', 'email': 'daniel.mwamba@example.com', 'location': 'Kabwe'},
        ]
        
        created_count = 0
        
        for user_data in sample_users[:count]:
            existing = User.query.filter_by(email=user_data['email']).first()
            
            if not existing:
                user = User(
                    name=user_data['name'],
                    phone=user_data['phone'],
                    email=user_data['email'],
                    location=user_data['location'],
                    subscription_type=random.choice(['sms', 'email', 'both']),
                    is_active=True
                )
                db.session.add(user)
                created_count += 1
        
        db.session.commit()
        
        return created_count
    
    @staticmethod
    def seed_sample_alerts(regions=None):
        """Seed sample alerts"""
        from models import db
        from models.alert import Alert
        from models.region import Region
        
        if not regions:
            regions = Region.query.all()
        
        sample_alerts = []
        
        # Check if alerts already exist
        existing_count = Alert.query.count()
        if existing_count > 0:
            return sample_alerts
        
        alert_templates = [
            {'message': 'Heavy rainfall expected in your area', 'risk_level': 'high', 'disaster_type': 'flood'},
            {'message': 'High temperatures forecasted', 'risk_level': 'medium', 'disaster_type': 'drought'},
            {'message': 'Severe weather warning issued', 'risk_level': 'critical', 'disaster_type': 'storm'},
        ]
        
        for region in regions[:3]:  # Create alerts for first 3 regions
            template = random.choice(alert_templates)
            
            alert = Alert(
                message=f"{template['message']} - {region.name}",
                risk_level=template['risk_level'],
                disaster_type=template['disaster_type'],
                region_id=region.id,
                is_manual=False,
                is_sent=True,
                sent_count=5
            )
            
            db.session.add(alert)
            sample_alerts.append(alert)
        
        db.session.commit()
        
        return sample_alerts
    
    @staticmethod
    def seed_all():
        """Run complete database seeding"""
        print("Seeding regions...")
        regions = DataSeeder.seed_regions()
        print(f"Created/found {len(regions)} regions")
        
        print("Seeding weather data...")
        weather_count = DataSeeder.seed_weather_data(regions, days_back=7)
        print(f"Created {weather_count} weather readings")
        
        print("Seeding admin user...")
        admin, created = DataSeeder.seed_admin_user()
        print(f"Admin user: {admin.username} ({'created' if created else 'already exists'})")
        
        print("Seeding sample users...")
        user_count = DataSeeder.seed_sample_users(5)
        print(f"Created {user_count} sample users")
        
        print("Seeding sample alerts...")
        alerts = DataSeeder.seed_sample_alerts(regions)
        print(f"Created {len(alerts)} sample alerts")
        
        print("\n✅ Database seeding complete!")
        print("\nDefault admin credentials:")
        print("Username: admin@123")
        print("Password: admin123")
        print("\n⚠️  Change the default password in production!")
