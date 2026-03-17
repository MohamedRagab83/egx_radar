"""Machine learning predictions for price movements."""

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pickle
from pathlib import Path


class MLPricePredictor:
    """Machine learning-based price movement predictor."""
    
    def __init__(self, model_type: str = 'gradient_boost'):
        """Initialize ML predictor.
        
        Args:
            model_type: Type of model ('random_forest', 'gradient_boost', 'svm', 'logistic')
        """
        self.model_type = model_type
        self.model = self._create_model()
        self.scaler = StandardScaler()
        self.feature_names = [
            'rsi', 'macd', 'bb_position', 'momentum',
            'sma_5_10_crossover', 'volume_ratio', 'volatility'
        ]
        self.is_trained = False
    
    def _create_model(self):
        """Create ML model based on type."""
        if self.model_type == 'random_forest':
            return RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        elif self.model_type == 'gradient_boost':
            return GradientBoostingClassifier(n_estimators=100, random_state=42)
        elif self.model_type == 'svm':
            return SVC(kernel='rbf', probability=True, random_state=42)
        else:  # logistic
            return LogisticRegression(random_state=42, max_iter=1000)
    
    def extract_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Extract features from OHLCV data.
        
        Args:
            data: OHLCV dataframe
            
        Returns:
            Dataframe with calculated features
        """
        features = pd.DataFrame(index=data.index)
        
        # RSI
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        features['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema_12 = data['Close'].ewm(span=12).mean()
        ema_26 = data['Close'].ewm(span=26).mean()
        features['macd'] = ema_12 - ema_26
        
        # Bollinger Bands position
        sma = data['Close'].rolling(20).mean()
        std = data['Close'].rolling(20).std()
        upper = sma + (2 * std)
        lower = sma - (2 * std)
        band_range = upper - lower
        features['bb_position'] = 2 * (data['Close'] - lower) / band_range - 1
        
        # Momentum
        features['momentum'] = (data['Close'] - data['Close'].shift(10)) / data['Close'].shift(10) * 100
        
        # SMA crossover
        sma_5 = data['Close'].rolling(5).mean()
        sma_10 = data['Close'].rolling(10).mean()
        features['sma_5_10_crossover'] = (sma_5 > sma_10).astype(float)
        
        # Volume ratio
        features['volume_ratio'] = data['Volume'] / data['Volume'].rolling(20).mean()
        
        # Volatility (rolling std of returns)
        returns = data['Close'].pct_change()
        features['volatility'] = returns.rolling(20).std() * 100
        
        return features.dropna()
    
    def train(self, data: pd.DataFrame, lookahead_days: int = 5) -> None:
        """Train the ML model.
        
        Args:
            data: OHLCV dataframe
            lookahead_days: Days ahead to predict
        """
        # Extract features
        features = self.extract_features(data).copy()
        
        # Create target: 1 if price goes up, 0 if down
        target = (data['Close'].shift(-lookahead_days) > data['Close']).astype(int)
        target = target[features.index]
        
        # Align
        common_index = features.index.intersection(target.index)
        X = features.loc[common_index]
        y = target.loc[common_index]
        
        if len(X) < 20:
            print("Not enough data to train")
            return
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        self.model.fit(X_scaled, y)
        self.is_trained = True
        
        # Calculate accuracy
        accuracy = self.model.score(X_scaled, y)
        print(f"{self.model_type} model trained. Accuracy: {accuracy:.2%}")
    
    def predict(self, data: pd.DataFrame) -> Optional[Dict]:
        """Predict price movement for the next period.
        
        Args:
            data: OHLCV dataframe
            
        Returns:
            Prediction dict with probabilities and signals
        """
        if not self.is_trained:
            return None
        
        features = self.extract_features(data).copy()
        if features.empty:
            return None
        
        # Get latest features
        latest_features = features.iloc[-1:].copy()
        
        # Scale
        X_scaled = self.scaler.transform(latest_features)
        
        # Predict
        prediction = self.model.predict(X_scaled)[0]
        
        # Get probabilities
        try:
            probabilities = self.model.predict_proba(X_scaled)[0]
            prob_down = float(probabilities[0])
            prob_up = float(probabilities[1])
        except:
            prob_down = 0.5
            prob_up = 0.5
        
        # Determine signal
        if prob_up > 0.65:
            signal = 'strong_buy'
        elif prob_up > 0.55:
            signal = 'buy'
        elif prob_down > 0.65:
            signal = 'strong_sell'
        elif prob_down > 0.55:
            signal = 'sell'
        else:
            signal = 'hold'
        
        return {
            'timestamp': datetime.now().isoformat(),
            'signal': signal,
            'prob_up': prob_up,
            'prob_down': prob_down,
            'confidence': max(prob_up, prob_down),
            'prediction': 'up' if prediction == 1 else 'down',
            'model_type': self.model_type,
            'latest_features': latest_features.to_dict(orient='records')[0]
        }
    
    def save_model(self, filepath: str) -> None:
        """Save trained model to file.
        
        Args:
            filepath: Path to save model
        """
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'scaler': self.scaler,
                'is_trained': self.is_trained,
                'model_type': self.model_type,
                'feature_names': self.feature_names
            }, f)
    
    def load_model(self, filepath: str) -> None:
        """Load trained model from file.
        
        Args:
            filepath: Path to model file
        """
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
            self.model = data['model']
            self.scaler = data['scaler']
            self.is_trained = data['is_trained']
            self.model_type = data['model_type']
            self.feature_names = data['feature_names']


class EnsemblePredictor:
    """Ensemble of multiple ML models for robust predictions."""
    
    def __init__(self, models: Optional[List[str]] = None):
        """Initialize ensemble.
        
        Args:
            models: List of model types to include
        """
        if models is None:
            models = ['gradient_boost', 'random_forest', 'svm']
        
        self.predictors = {
            name: MLPricePredictor(model_type=name)
            for name in models
        }
    
    def train(self, data: pd.DataFrame, lookahead_days: int = 5) -> None:
        """Train all models.
        
        Args:
            data: OHLCV dataframe
            lookahead_days: Days ahead to predict
        """
        for name, predictor in self.predictors.items():
            print(f"Training {name}...")
            predictor.train(data, lookahead_days=lookahead_days)
    
    def predict(self, data: pd.DataFrame) -> Dict:
        """Get ensemble prediction.
        
        Args:
            data: OHLCV dataframe
            
        Returns:
            Ensemble prediction
        """
        predictions = {}
        valid_predictions = []
        
        for name, predictor in self.predictors.items():
            pred = predictor.predict(data)
            if pred:
                predictions[name] = pred
                valid_predictions.append(pred)
        
        if not valid_predictions:
            return {}
        
        # Average probabilities
        avg_prob_up = np.mean([p['prob_up'] for p in valid_predictions])
        avg_prob_down = np.mean([p['prob_down'] for p in valid_predictions])
        
        # Determine ensemble signal
        if avg_prob_up > 0.65:
            signal = 'strong_buy'
        elif avg_prob_up > 0.55:
            signal = 'buy'
        elif avg_prob_down > 0.65:
            signal = 'strong_sell'
        elif avg_prob_down > 0.55:
            signal = 'sell'
        else:
            signal = 'hold'
        
        return {
            'timestamp': datetime.now().isoformat(),
            'signal': signal,
            'prob_up': float(avg_prob_up),
            'prob_down': float(avg_prob_down),
            'confidence': float(max(avg_prob_up, avg_prob_down)),
            'model_count': len(valid_predictions),
            'individual_predictions': predictions,
            'model_agreement': self._calculate_agreement(valid_predictions)
        }
    
    @staticmethod
    def _calculate_agreement(predictions: List[Dict]) -> float:
        """Calculate how much models agree (0-1).
        
        Args:
            predictions: List of predictions
            
        Returns:
            Agreement score
        """
        if not predictions:
            return 0.0
        
        signals = [p['signal'].replace('_', '') for p in predictions]
        most_common = max(set(signals), key=signals.count)
        agreement = signals.count(most_common) / len(signals)
        return float(agreement)


# Global instance
_ensemble_predictor: Optional[EnsemblePredictor] = None


def get_ensemble_predictor() -> EnsemblePredictor:
    """Get or create global ensemble predictor."""
    global _ensemble_predictor
    if _ensemble_predictor is None:
        _ensemble_predictor = EnsemblePredictor()
    return _ensemble_predictor
