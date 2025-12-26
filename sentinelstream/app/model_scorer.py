"""ML Model scorer for fraud detection"""
import pickle
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional
from sklearn.ensemble import IsolationForest
from app.config import settings


class FraudModelScorer:
    """ML model scorer for fraud detection using Isolation Forest"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or settings.ML_MODEL_PATH
        self.model: Optional[IsolationForest] = None
        self.feature_names = [
            "amount",
            "hour_of_day",
            "day_of_week",
            "amount_deviation",
            "location_different",
            "transaction_frequency"
        ]
    
    def load_model(self):
        """Load pre-trained model from file"""
        model_file = Path(self.model_path)
        if model_file.exists():
            with open(model_file, 'rb') as f:
                self.model = pickle.load(f)
        else:
            # Create a default model if none exists
            self.create_default_model()
    
    def create_default_model(self):
        """Create a default Isolation Forest model for demonstration"""
        # Default Isolation Forest with contamination=0.1 (10% outliers)
        self.model = IsolationForest(
            n_estimators=100,
            contamination=0.1,
            random_state=42,
            n_jobs=-1
        )
        # Train on dummy data
        dummy_data = np.random.randn(1000, len(self.feature_names))
        self.model.fit(dummy_data)
        
        # Save the model
        Path(self.model_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.model_path, 'wb') as f:
            pickle.dump(self.model, f)
    
    def extract_features(self, transaction: Dict[str, Any], user_profile: Optional[Dict[str, Any]] = None) -> np.ndarray:
        """Extract features from transaction for ML model"""
        features = []
        
        # Amount
        amount = transaction.get("amount", 0.0)
        features.append(float(amount))
        
        # Hour of day (0-23)
        from datetime import datetime
        hour = datetime.now().hour
        features.append(float(hour))
        
        # Day of week (0=Monday, 6=Sunday)
        day_of_week = datetime.now().weekday()
        features.append(float(day_of_week))
        
        # Amount deviation from user's average
        if user_profile:
            avg_amount = user_profile.get("average_transaction_amount", amount)
            if avg_amount > 0:
                deviation = abs(amount - avg_amount) / avg_amount
            else:
                deviation = 1.0
        else:
            deviation = 1.0
        features.append(deviation)
        
        # Location different from home (binary)
        if user_profile:
            home_location = user_profile.get("home_location")
            transaction_location = transaction.get("location")
            location_different = 1.0 if home_location and transaction_location != home_location else 0.0
        else:
            location_different = 0.0
        features.append(location_different)
        
        # Transaction frequency (normalized)
        if user_profile:
            tx_count = user_profile.get("transaction_count", 0)
            # Normalize to 0-1 range (assuming max 1000 transactions)
            frequency = min(tx_count / 1000.0, 1.0)
        else:
            frequency = 0.0
        features.append(frequency)
        
        return np.array(features).reshape(1, -1)
    
    def score_transaction(
        self,
        transaction: Dict[str, Any],
        user_profile: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Score transaction for fraud risk.
        Returns a score between 0.0 (normal) and 1.0 (anomaly/fraud).
        """
        if self.model is None:
            self.load_model()
        
        # Extract features
        features = self.extract_features(transaction, user_profile)
        
        # Predict anomaly score
        # Isolation Forest returns -1 for outliers, 1 for inliers
        anomaly_score = self.model.predict(features)[0]
        decision_score = self.model.decision_function(features)[0]
        
        # Convert to 0-1 risk score
        # decision_score: negative = outlier, positive = inlier
        # Normalize to 0-1 where 1 = high risk
        risk_score = 1.0 / (1.0 + np.exp(decision_score))  # Sigmoid normalization
        
        return float(risk_score)

