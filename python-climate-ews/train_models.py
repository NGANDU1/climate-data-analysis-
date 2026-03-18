#!/usr/bin/env python3
"""
Model Training Pipeline
Train ML models on historical weather data for disaster prediction
"""

import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime
import warnings

warnings.filterwarnings("ignore")

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models.weather_data import WeatherData
from services.ml_models import (
    RandomForestClassifier,
    XGBoostClassifier,
    LSTMForecaster,
    EnsemblePredictor,
)


class ModelTrainer:
    """Training pipeline for ML models"""

    def __init__(self):
        """Initialize trainer"""

        self.app = create_app("development")

        self.model_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "models", "saved"
        )

        if not os.path.exists(self.model_path):
            os.makedirs(self.model_path)

        print(f"Models will be saved to: {self.model_path}")

    def load_training_data(self, min_samples=1000, dataset_id: int | None = None, sources: list[str] | None = None):
        """Load training data from database"""

        with self.app.app_context():

            print("Loading weather data from database...")

            q = WeatherData.query
            if dataset_id is not None:
                q = q.filter(WeatherData.dataset_id == int(dataset_id))
            if sources:
                q = q.filter(WeatherData.source.in_(sources))

            weather_records = q.all()

            if len(weather_records) < min_samples:
                raise ValueError(
                    f"Insufficient training data. Need {min_samples} samples, "
                    f"found {len(weather_records)}"
                )

            data = []

            for record in weather_records:
                data.append(
                    {
                        "region_id": record.region_id,
                        "temperature": record.temperature,
                        "humidity": record.humidity,
                        "rainfall": record.rainfall,
                        "wind_speed": record.wind_speed,
                        "pressure": record.pressure,
                        "timestamp": record.timestamp,
                    }
                )

            df = pd.DataFrame(data)
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
            df = df.dropna(subset=["timestamp"])

            print(f"Loaded {len(df)} weather records")

            return df

    def create_target_variable(self, df):
        """Create classification target labels"""

        targets = []

        for _, row in df.iterrows():

            rainfall = row["rainfall"]
            temp = row["temperature"]
            humidity = row["humidity"]

            if rainfall > 100:
                label = 3
            elif rainfall > 50:
                label = 2
            elif temp > 35 and rainfall < 10:
                label = 2
            elif temp > 40:
                label = 2
            elif humidity > 80 and temp > 25:
                label = 1
            elif temp > 30 and rainfall < 20:
                label = 1
            else:
                label = 0

            targets.append(label)

        return np.array(targets)

    def prepare_features(self, df):
        """Prepare ML features"""

        df = df.copy()

        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["timestamp"])

        df["hour"] = df["timestamp"].dt.hour
        df["month"] = df["timestamp"].dt.month
        df["day_of_year"] = df["timestamp"].dt.dayofyear

        df["heat_index"] = df["temperature"] + 0.55 * (
            (1 - df["humidity"] / 100) * (df["temperature"] - 14.5)
        )

        df["dew_point"] = (
            237.3 * np.log(df["humidity"] / 100)
            + (17.27 * df["temperature"]) / (237.3 + df["temperature"])
        )

        feature_columns = [
            "temperature",
            "humidity",
            "rainfall",
            "wind_speed",
            "pressure",
            "heat_index",
            "dew_point",
            "hour",
            "month",
        ]

        return df[feature_columns].values

    def train_random_forest(self, X, y):

        print("\n" + "=" * 60)
        print("Training Random Forest")
        print("=" * 60)

        model = RandomForestClassifier(
            n_estimators=200, max_depth=15, model_path=self.model_path
        )

        metrics = model.train(X, y, validation_split=0.2)

        model.save("random_forest_model.pkl")

        return metrics

    def train_xgboost(self, X, y):

        print("\n" + "=" * 60)
        print("Training XGBoost")
        print("=" * 60)

        try:
            model = XGBoostClassifier(
                n_estimators=500,
                learning_rate=0.01,
                max_depth=8,
                model_path=self.model_path,
            )

            metrics = model.train(X, y, validation_split=0.2)
            model.save("xgboost_model.pkl")
            return metrics
        except Exception as e:
            print(f"⚠ XGBoost skipped: {e}")
            return {"skipped": True, "reason": str(e)}

    def train_lstm(self, df):

        print("\n" + "=" * 60)
        print("Training LSTM Model")
        print("=" * 60)

        try:
            lstm_model = LSTMForecaster(
                lookback_days=7, forecast_days=3, model_path=self.model_path
            )
        except Exception as e:
            print(f"⚠ LSTM skipped: {e}")
            return {"skipped": True, "reason": str(e)}

        regions = df["region_id"].unique()

        sequences = []

        for region_id in regions:

            region_data = df[df["region_id"] == region_id].sort_values("timestamp")

            if len(region_data) >= 14:

                features = region_data[
                    ["temperature", "humidity", "rainfall", "wind_speed", "pressure"]
                ].values

                sequences.append(features)

        if not sequences:
            print("⚠ Not enough data for LSTM")
            return {}

        combined = np.vstack(sequences)

        try:
            metrics = lstm_model.train(combined, epochs=50, batch_size=32)
            lstm_model.save("lstm_model.h5")
            return metrics
        except Exception as e:
            print(f"⚠ LSTM training failed/skipped: {e}")
            return {"skipped": True, "reason": str(e)}

    def train_all_models(self, dataset_id: int | None = None, sources: list[str] | None = None, min_samples: int | None = None):

        print("\n" + "=" * 60)
        print("CLIMATE EWS - ML MODEL TRAINING")
        print("=" * 60)

        if min_samples is None:
            try:
                min_samples = int(os.environ.get("TRAIN_MIN_SAMPLES", "50"))
            except Exception:
                min_samples = 50

        df = self.load_training_data(min_samples=min_samples, dataset_id=dataset_id, sources=sources)

        print("\nPreparing features...")

        X = self.prepare_features(df)
        y = self.create_target_variable(df)

        print("Training models...")

        rf_metrics = self.train_random_forest(X, y)
        xgb_metrics = self.train_xgboost(X, y)
        lstm_metrics = self.train_lstm(df)

        print("\nTraining Summary")

        if isinstance(rf_metrics, dict) and "val_accuracy" in rf_metrics:
            print(f"Random Forest Accuracy: {rf_metrics['val_accuracy']:.4f}")
        if isinstance(xgb_metrics, dict) and "val_accuracy" in xgb_metrics:
            print(f"XGBoost Accuracy: {xgb_metrics['val_accuracy']:.4f}")

        if lstm_metrics:
            print(f"LSTM Validation Loss: {lstm_metrics['val_loss']:.4f}")

        print("\n✓ Models trained successfully")

        return {
            "random_forest": rf_metrics,
            "xgboost": xgb_metrics,
            "lstm": lstm_metrics,
            "filters": {"dataset_id": dataset_id, "sources": sources, "min_samples": min_samples},
            "trained_at": datetime.utcnow().isoformat(),
        }

    def evaluate_models(self, test_data):

        print("\nModel Evaluation")

        ensemble = EnsemblePredictor(model_path=self.model_path)

        ensemble.load_all()

        X_test = self.prepare_features(test_data)
        y_test = self.create_target_variable(test_data)

        predictions, confidences = ensemble.predict(X_test, X_test, X_test)

        from sklearn.metrics import accuracy_score, classification_report

        pred_labels = (
            np.argmax(predictions, axis=1)
            if len(predictions.shape) > 1
            else predictions
        )

        accuracy = accuracy_score(y_test, pred_labels)

        print(f"\nAccuracy: {accuracy:.4f}")
        print(classification_report(y_test, pred_labels))


def main():

    print("=" * 70)
    print("CLIMATE EARLY WARNING SYSTEM - ML TRAINING")
    print("=" * 70)

    trainer = ModelTrainer()

    try:

        trainer.train_all_models()

        print("\nNext Steps:")
        print("1. Run Flask: flask run")
        print("2. Test API: http://localhost:5000/api/risk/predict")

        return 0

    except Exception as e:

        print(f"\nTraining failed: {e}")

        return 1


if __name__ == "__main__":
    exit(main())
