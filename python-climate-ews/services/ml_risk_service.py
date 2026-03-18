"""
ML-Powered Risk Calculator
Uses trained machine learning models for disaster prediction
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from services.ml_models import (
    RandomForestClassifier,
    XGBoostClassifier,
    LSTMForecaster,
    EnsemblePredictor
)


class MLRiskCalculator:
    """Machine Learning-based risk calculation"""

    def __init__(self, model_path: str = "models/saved/"):
        self.model_path = model_path
        self.ensemble = EnsemblePredictor(model_path=model_path)
        self.models_loaded = False

    def load_models(self):
        """Load trained models"""
        try:
            self.ensemble.load_all()
            self.models_loaded = True
            print("✓ All ML models loaded successfully")
        except Exception as e:
            print(f"⚠ Could not load models: {e}")
            self.models_loaded = False

    def prepare_features(
        self,
        weather_data: Dict,
        historical_data: Optional[pd.DataFrame] = None
    ) -> Dict:

        temperature = weather_data.get("temperature", 25)
        humidity = weather_data.get("humidity", 60)
        rainfall = weather_data.get("rainfall", 0)
        wind_speed = weather_data.get("wind_speed", 10)
        pressure = weather_data.get("pressure", 1013)

        features = np.array([[
            temperature,
            humidity,
            rainfall,
            wind_speed,
            pressure,
            self._calculate_heat_index(temperature, humidity),
            self._calculate_wind_chill(temperature, wind_speed),
            self._calculate_dew_point(temperature, humidity)
        ]])

        lstm_input = None
        if historical_data is not None and len(historical_data) >= 7:
            recent_data = historical_data.tail(7)[[
                "temperature", "humidity", "rainfall", "wind_speed", "pressure"
            ]].values
            lstm_input = recent_data

        return {
            "rf_features": features,
            "xgb_features": features,
            "lstm_sequences": lstm_input
        }

    def predict_risk(
        self,
        weather_data: Dict,
        historical_data: Optional[pd.DataFrame] = None
    ) -> Dict:

        if not self.models_loaded:
            self.load_models()

        features = self.prepare_features(weather_data, historical_data)

        if not self.models_loaded:
            return self._fallback_rule_based_prediction(weather_data)

        try:
            prediction, confidence = self.ensemble.predict(
                features["rf_features"],
                features["xgb_features"],
                features["lstm_sequences"]
                if features["lstm_sequences"] is not None
                else features["rf_features"]
            )

            risk_level, disaster_type = self._interpret_prediction(prediction)

            alerts, recommendations = self._generate_advisories(
                risk_level, disaster_type, weather_data
            )

            return {
                "risk_level": risk_level,
                "disaster_type": disaster_type,
                "confidence_score": round(float(confidence), 2),
                "ml_prediction": True,
                "alerts": alerts,
                "recommendations": recommendations,
                "timestamp": datetime.utcnow().isoformat(),
                "raw_prediction": float(prediction)
            }

        except Exception as e:
            print(f"ML prediction error: {e}")
            return self._fallback_rule_based_prediction(weather_data)

    def _interpret_prediction(self, prediction: float) -> Tuple[str, str]:

        if prediction >= 0.8:
            return "critical", "flood"
        elif prediction >= 0.6:
            return "high", "flood"
        elif prediction >= 0.4:
            return "medium", "drought"
        else:
            return "low", "general"

    def _generate_advisories(
        self,
        risk_level: str,
        disaster_type: str,
        weather_data: Dict
    ) -> Tuple[List[str], List[str]]:

        alerts = []
        recommendations = []

        temp = weather_data.get("temperature", 25)
        if temp > 35:
            alerts.append(f"High temperature alert: {temp:.1f}°C")
            recommendations.append(
                "Stay hydrated and avoid prolonged sun exposure"
            )

        rainfall = weather_data.get("rainfall", 0)
        if rainfall > 50:
            alerts.append(f"Heavy rainfall detected: {rainfall:.1f}mm")

            if rainfall > 100:
                recommendations.append(
                    "Evacuate low-lying areas immediately"
                )
                recommendations.append("Prepare emergency shelters")
            else:
                recommendations.append("Monitor water levels closely")

        wind_speed = weather_data.get("wind_speed", 0)
        if wind_speed > 50:
            alerts.append(f"High wind warning: {wind_speed:.1f} km/h")
            recommendations.append("Secure loose outdoor items")

        if risk_level == "critical":
            recommendations.append("Activate emergency response protocols")

        elif risk_level == "high":
            recommendations.append("Increase monitoring frequency")

        return alerts, recommendations

    def _fallback_rule_based_prediction(self, weather_data: Dict) -> Dict:
        from services.risk_calculator import RiskCalculator
        return RiskCalculator.predict_risk(weather_data)

    def _calculate_heat_index(self, temp: float, humidity: float) -> float:
        return temp + 0.55 * ((1 - humidity / 100) * (temp - 14.5))

    def _calculate_wind_chill(self, temp: float, wind_speed: float) -> float:
        if temp > 10 or wind_speed < 4.8:
            return temp
        return (
            13.12
            + 0.6215 * temp
            - 11.37 * (wind_speed ** 0.16)
            + 0.3965 * temp * (wind_speed ** 0.16)
        )

    def _calculate_dew_point(self, temp: float, humidity: float) -> float:
        a = np.log(humidity / 100) + (17.27 * temp) / (237.3 + temp)
        return (237.3 * a) / (17.27 - a)