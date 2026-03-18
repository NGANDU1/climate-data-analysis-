"""
Machine Learning Models for Climate Disaster Prediction
Implements Random Forest, XGBoost, LSTM, and Ensemble methods
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import joblib
import os


class DisasterPredictionModel:
    """Base class for disaster prediction models"""
    
    def __init__(self, model_path: str = 'models/saved/'):
        """Initialize model"""
        self.model_path = model_path
        self.model = None
        self.is_trained = False
    
    def train(self, X: np.ndarray, y: np.ndarray):
        """Train the model"""
        raise NotImplementedError
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions"""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        return self.model.predict(X)
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Get prediction probabilities"""
        if hasattr(self.model, 'predict_proba'):
            return self.model.predict_proba(X)
        return None
    
    def save(self, filename: str):
        """Save model to disk"""
        if not os.path.exists(self.model_path):
            os.makedirs(self.model_path)
        
        filepath = os.path.join(self.model_path, filename)
        joblib.dump(self.model, filepath)
        print(f"Model saved to {filepath}")
    
    def load(self, filename: str):
        """Load model from disk"""
        filepath = os.path.join(self.model_path, filename)
        if os.path.exists(filepath):
            self.model = joblib.load(filepath)
            self.is_trained = True
            print(f"Model loaded from {filepath}")
        else:
            raise FileNotFoundError(f"Model file not found: {filepath}")


class RandomForestClassifier(DisasterPredictionModel):
    """Random Forest classifier for disaster prediction"""
    
    def __init__(self, n_estimators: int = 100, max_depth: int = 10,
                 model_path: str = 'models/saved/'):
        """
        Initialize Random Forest model
        
        Args:
            n_estimators: Number of trees in the forest
            max_depth: Maximum depth of each tree
        """
        super().__init__(model_path)
        from sklearn.ensemble import RandomForestClassifier as SKLearnRFC
        
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.model = SKLearnRFC(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=42,
            class_weight='balanced',
            n_jobs=-1
        )
    
    def train(self, X: np.ndarray, y: np.ndarray, 
             validation_split: float = 0.2) -> Dict:
        """
        Train Random Forest model
        
        Args:
            X: Feature matrix
            y: Target labels
            validation_split: Fraction of data to use for validation
            
        Returns:
            Training metrics
        """
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
        
        # Split data
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=validation_split, random_state=42, stratify=y
        )
        
        # Train model
        print(f"Training Random Forest with {len(X_train)} samples...")
        self.model.fit(X_train, y_train)
        self.is_trained = True
        
        # Evaluate
        y_pred_train = self.model.predict(X_train)
        y_pred_val = self.model.predict(X_val)
        
        train_acc = accuracy_score(y_train, y_pred_train)
        val_acc = accuracy_score(y_val, y_pred_val)
        
        metrics = {
            'train_accuracy': train_acc,
            'val_accuracy': val_acc,
            'classification_report': classification_report(y_val, y_pred_val),
            'confusion_matrix': confusion_matrix(y_val, y_pred_val).tolist(),
            'feature_importances': self.model.feature_importances_.tolist()
        }
        
        print(f"\nTraining Complete:")
        print(f"  Train Accuracy: {train_acc:.4f}")
        print(f"  Validation Accuracy: {val_acc:.4f}")
        print(f"\nClassification Report:\n{metrics['classification_report']}")
        
        return metrics


class XGBoostClassifier(DisasterPredictionModel):
    """XGBoost classifier for improved disaster prediction"""
    
    def __init__(self, n_estimators: int = 1000, learning_rate: float = 0.01,
                 max_depth: int = 6, model_path: str = 'models/saved/'):
        """
        Initialize XGBoost model
        
        Args:
            n_estimators: Number of boosting rounds
            learning_rate: Step size shrinkage
            max_depth: Maximum tree depth
        """
        super().__init__(model_path)
        import xgboost as xgb
        
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        
        self.model = xgb.XGBClassifier(
            n_estimators=n_estimators,
            learning_rate=learning_rate,
            max_depth=max_depth,
            random_state=42,
            eval_metric='mlogloss',
            use_label_encoder=False
        )
    
    def train(self, X: np.ndarray, y: np.ndarray,
             validation_split: float = 0.2) -> Dict:
        """
        Train XGBoost model
        
        Args:
            X: Feature matrix
            y: Target labels
            validation_split: Validation data fraction
            
        Returns:
            Training metrics
        """
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score, classification_report
        
        # Split data
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=validation_split, random_state=42, stratify=y
        )
        
        # Train with early stopping
        print(f"Training XGBoost with {len(X_train)} samples...")
        
        eval_set = [(X_train, y_train), (X_val, y_val)]
        self.model.fit(
            X_train, y_train,
            eval_set=eval_set,
            verbose=True
        )
        
        self.is_trained = True
        
        # Evaluate
        y_pred_train = self.model.predict(X_train)
        y_pred_val = self.model.predict(X_val)
        
        train_acc = accuracy_score(y_train, y_pred_train)
        val_acc = accuracy_score(y_val, y_pred_val)
        
        metrics = {
            'train_accuracy': train_acc,
            'val_accuracy': val_acc,
            'classification_report': classification_report(y_val, y_pred_val),
            'feature_importances': self.model.feature_importances_.tolist()
        }
        
        print(f"\nTraining Complete:")
        print(f"  Train Accuracy: {train_acc:.4f}")
        print(f"  Validation Accuracy: {val_acc:.4f}")
        
        return metrics


class LSTMForecaster(DisasterPredictionModel):
    """LSTM neural network for time-series weather forecasting"""
    
    def __init__(self, lookback_days: int = 7, forecast_days: int = 3,
                 model_path: str = 'models/saved/'):
        """
        Initialize LSTM model
        
        Args:
            lookback_days: Number of past days to use for prediction
            forecast_days: Number of days to forecast ahead
        """
        super().__init__(model_path)
        self.lookback_days = lookback_days
        self.forecast_days = forecast_days
        self.model = None
        self.scaler = None
    
    def create_sequences(self, data: np.ndarray, target_col: int = 0) -> Tuple:
        """
        Create sequences for LSTM training
        
        Args:
            data: Time series data
            target_col: Column index to predict
            
        Returns:
            X, y sequences
        """
        X, y = [], []
        
        for i in range(len(data) - self.lookback_days):
            X.append(data[i:i+self.lookback_days])
            y.append(data[i+self.lookback_days, target_col])
        
        return np.array(X), np.array(y)
    
    def build_model(self, input_shape: Tuple) -> 'tf.keras.Model':
        """
        Build LSTM neural network architecture
        
        Args:
            input_shape: Shape of input data
            
        Returns:
            Compiled Keras model
        """
        try:
            from tensorflow.keras.models import Sequential
            from tensorflow.keras.layers import LSTM, Dense, Dropout
            from tensorflow.keras.optimizers import Adam
        except ImportError:
            raise ImportError("TensorFlow not installed. Run: pip install tensorflow")
        
        model = Sequential([
            LSTM(128, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            LSTM(64, return_sequences=True),
            Dropout(0.2),
            LSTM(32),
            Dropout(0.2),
            Dense(64, activation='relu'),
            Dense(32, activation='relu'),
            Dense(1)  # Output layer
        ])
        
        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae']
        )
        
        return model
    
    def train(self, data: np.ndarray, epochs: int = 50,
             batch_size: int = 32, validation_split: float = 0.2) -> Dict:
        """
        Train LSTM model on time series data
        
        Args:
            data: Time series data (samples, features)
            epochs: Number of training epochs
            batch_size: Batch size
            validation_split: Validation data fraction
            
        Returns:
            Training history
        """
        from sklearn.preprocessing import MinMaxScaler
        from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
        import tensorflow as tf
        
        # Scale data
        self.scaler = MinMaxScaler()
        scaled_data = self.scaler.fit_transform(data)
        
        # Create sequences
        X, y = self.create_sequences(scaled_data)
        
        # Reshape for LSTM [samples, time steps, features]
        X = X.reshape((X.shape[0], X.shape[1], X.shape[2]))
        
        # Split data
        split_idx = int(len(X) * (1 - validation_split))
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        # Build model
        print(f"Building LSTM model with input shape: {X_train.shape[1:]}...")
        self.model = self.build_model(X_train.shape[1:])
        
        # Callbacks
        callbacks = [
            EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True),
            ModelCheckpoint(
                os.path.join(self.model_path, 'lstm_best.h5'),
                monitor='val_loss',
                save_best_only=True
            )
        ]
        
        # Train
        print(f"Training LSTM with {len(X_train)} sequences...")
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callbacks,
            verbose=1
        )
        
        self.is_trained = True
        
        # Evaluate
        train_loss = self.model.evaluate(X_train, y_train, verbose=0)
        val_loss = self.model.evaluate(X_val, y_val, verbose=0)
        
        metrics = {
            'train_loss': train_loss[0],
            'val_loss': val_loss[0],
            'train_mae': train_loss[1],
            'val_mae': val_loss[1],
            'history': history.history
        }
        
        print(f"\nTraining Complete:")
        print(f"  Train Loss: {train_loss[0]:.4f}, MAE: {train_loss[1]:.4f}")
        print(f"  Val Loss: {val_loss[0]:.4f}, MAE: {val_loss[1]:.4f}")
        
        return metrics
    
    def forecast(self, recent_data: np.ndarray) -> np.ndarray:
        """
        Forecast future values
        
        Args:
           recent_data: Recent weather data (lookback_days, features)
            
        Returns:
            Forecasted values
        """
        if not self.is_trained:
            raise ValueError("Model must be trained first")
        
        # Scale data
        scaled_recent = self.scaler.transform(recent_data.reshape(-1, recent_data.shape[-1]))
        scaled_recent = scaled_recent.reshape(1, self.lookback_days, -1)
        
        # Predict
        forecast = self.model.predict(scaled_recent, verbose=0)
        
        return forecast
    
    def save(self, filename: str = 'lstm_model.h5'):
        """Save LSTM model"""
        if not os.path.exists(self.model_path):
            os.makedirs(self.model_path)
        
        filepath = os.path.join(self.model_path, filename)
        self.model.save(filepath)
        
        # Save scaler
        joblib.dump(self.scaler, os.path.join(self.model_path, 'scaler.pkl'))
        
        print(f"LSTM model saved to {filepath}")
    
    def load(self, filename: str = 'lstm_model.h5'):
        """Load LSTM model"""
        from tensorflow.keras.models import load_model
        
        filepath = os.path.join(self.model_path, filename)
        if os.path.exists(filepath):
            self.model = load_model(filepath)
            
            # Load scaler
            scaler_path = os.path.join(self.model_path, 'scaler.pkl')
            if os.path.exists(scaler_path):
                self.scaler = joblib.load(scaler_path)
            
            self.is_trained = True
            print(f"LSTM model loaded from {filepath}")
        else:
            raise FileNotFoundError(f"Model file not found: {filepath}")


class EnsemblePredictor:
    """Ensemble model combining RF, XGBoost, and LSTM"""
    
    def __init__(self, model_path: str = 'models/saved/'):
        """Initialize ensemble predictor"""
        self.model_path = model_path
        self.rf_model = RandomForestClassifier(model_path=model_path)
        self.xgb_model = XGBoostClassifier(model_path=model_path)
        self.lstm_model = LSTMForecaster(model_path=model_path)
        
        self.weights = {
            'rf': 0.4,
            'xgb': 0.4,
            'lstm': 0.2
        }
    
    def set_weights(self, rf_weight: float, xgb_weight: float, lstm_weight: float):
        """
        Set ensemble weights
        
        Args:
            rf_weight: Random Forest weight
            xgb_weight: XGBoost weight
            lstm_weight: LSTM weight
        """
        total = rf_weight + xgb_weight + lstm_weight
        self.weights = {
            'rf': rf_weight / total,
            'xgb': xgb_weight / total,
            'lstm': lstm_weight / total
        }
    
    def predict(self, X_rf: np.ndarray, X_xgb: np.ndarray, 
                 X_lstm: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Make ensemble prediction
        
        Args:
            X_rf: Features for Random Forest
            X_xgb: Features for XGBoost
            X_lstm: Sequences for LSTM
            
        Returns:
            (prediction, confidence)
        """
        predictions = []
        confidences = []
        
        # Get individual predictions
        if self.rf_model.is_trained:
            rf_pred = self.rf_model.predict(X_rf)
            rf_proba = self.rf_model.predict_proba(X_rf)
            predictions.append((rf_pred, rf_weight := self.weights['rf']))
            if rf_proba is not None:
                confidences.append((np.max(rf_proba, axis=1), rf_weight))
        
        if self.xgb_model.is_trained:
            xgb_pred = self.xgb_model.predict(X_xgb)
            xgb_proba = self.xgb_model.predict_proba(X_xgb)
            predictions.append((xgb_pred, self.weights['xgb']))
            if xgb_proba is not None:
                confidences.append((np.max(xgb_proba, axis=1), self.weights['xgb']))
        
        if self.lstm_model.is_trained:
            lstm_pred = self.lstm_model.forecast(X_lstm)
            # Normalize LSTM output for classification
            lstm_pred_norm = (lstm_pred - lstm_pred.min()) / (lstm_pred.max() - lstm_pred.min() + 1e-8)
            predictions.append((lstm_pred_norm.flatten(), self.weights['lstm']))
            confidences.append((lstm_pred_norm.flatten(), self.weights['lstm']))
        
        if not predictions:
            raise ValueError("No models are trained")
        
        # Weighted average of predictions
        weighted_predictions = np.zeros_like(predictions[0][0], dtype=float)
        total_weight = 0
        
        for pred, weight in predictions:
            weighted_predictions += pred * weight
            total_weight += weight
        
        final_prediction = weighted_predictions / total_weight
        
        # Calculate confidence
        if confidences:
            weighted_confidence = sum(conf * w for conf, w in confidences) / total_weight
            confidence = np.mean(weighted_confidence)
        else:
            confidence = 0.5
        
        return final_prediction, confidence
    
    def save_all(self):
        """Save all models"""
        self.rf_model.save('random_forest_model.pkl')
        self.xgb_model.save('xgboost_model.pkl')
        self.lstm_model.save('lstm_model.h5')
        print("All ensemble models saved")
    
    def load_all(self):
        """Load all models"""
        try:
            self.rf_model.load('random_forest_model.pkl')
            self.xgb_model.load('xgboost_model.pkl')
            self.lstm_model.load('lstm_model.h5')
            print("All ensemble models loaded")
        except Exception as e:
            print(f"Error loading models: {e}")
            raise
