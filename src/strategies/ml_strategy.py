"""ML strategy using XGBoost/LightGBM on engineered features."""

import pandas as pd
import numpy as np
from typing import Optional
from pathlib import Path
from .base import Strategy


class MLStrategy(Strategy):
    """Signal generation using gradient-boosted tree models.
    
    Trains on engineered features to predict probability of positive
    5-day forward returns. Generates long signals when probability > threshold.
    Supports weekly retraining with expanding window.
    """
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.ml_config = config["strategy"]["ml"]
        self.model = None
        self.feature_columns = None
        self.last_train_date: Optional[str] = None
        self._load_or_train()
    
    def _load_or_train(self):
        """Load existing model or train a new one."""
        model_dir = Path("models")
        model_path = model_dir / "ml_strategy_model.json"
        
        if model_path.exists():
            self._load_model(str(model_path))
        # Training happens on first generate_signals call with enough data
    
    def _load_model(self, path: str):
        """Load model from file."""
        try:
            import xgboost as xgb
            self.model = xgb.XGBClassifier()
            self.model.load_model(path)
        except ImportError:
            pass
    
    def _save_model(self, path: str):
        """Save model to file."""
        if self.model is not None:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            self.model.save_model(path)
    
    def _train(self, X: pd.DataFrame, y: pd.Series):
        """Train XGBoost model on features."""
        try:
            import xgboost as xgb
            
            self.model = xgb.XGBClassifier(
                n_estimators=200,
                max_depth=5,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                objective="binary:logistic",
                eval_metric="logloss",
                random_state=42,
            )
            
            self.model.fit(X, y)
            
        except ImportError:
            # Fallback: use sklearn RandomForest if xgboost unavailable
            from sklearn.ensemble import RandomForestClassifier
            self.model = RandomForestClassifier(
                n_estimators=200,
                max_depth=5,
                random_state=42,
            )
            self.model.fit(X, y)
    
    def generate_signals(self, features: pd.DataFrame) -> pd.Series:
        """Generate ML-based trading signals."""
        if features.empty:
            return pd.Series(dtype=float)
        
        # Get feature columns (all numeric columns except target)
        target_col = "target_5d"
        exclude_cols = {target_col, "open", "high", "low", "close", "volume", 
                       "dollar_volume", "symbol"}
        
        self.feature_columns = [c for c in features.columns 
                               if c not in exclude_cols 
                               and features[c].dtype in (np.float64, np.float32, np.int64)]
        
        # If we need to train
        is_new_model = self.model is None
        if is_new_model and target_col in features.columns:
            X = features[self.feature_columns].dropna()
            y = (features[target_col] > 0).astype(int).loc[X.index]
            
            if len(y) > 100:  # Minimum samples to train
                self._train(X, y)
                self._save_model("models/ml_strategy_model.json")
        
        # If still no model, return empty
        if self.model is None:
            return pd.Series(0.0, index=features.index.get_level_values("symbol").unique())
        
        # Generate predictions on latest data
        latest = features.groupby("symbol").last()
        X_pred = latest[self.feature_columns].dropna()
        
        if X_pred.empty:
            return pd.Series(0.0, index=features.index.get_level_values("symbol").unique())
        
        try:
            probabilities = self.model.predict_proba(X_pred)[:, 1]  # P(up)
        except Exception:
            return pd.Series(0.0, index=X_pred.index)
        
        prob_series = pd.Series(probabilities, index=X_pred.index)
        
        # Apply thresholds
        threshold_long = self.ml_config["probability_threshold_long"]
        threshold_short = self.ml_config["probability_threshold_short"]
        
        signals = pd.Series(0.0, index=prob_series.index)
        signals[prob_series >= threshold_long] = 1.0
        signals[prob_series <= threshold_short] = -1.0
        
        return signals
