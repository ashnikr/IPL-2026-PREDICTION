"""
Machine Learning Models for IPL Match Prediction.

Trains and evaluates: Logistic Regression, Random Forest, XGBoost, LightGBM, CatBoost.
"""

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, classification_report, confusion_matrix,
    log_loss,
)
from sklearn.impute import SimpleImputer

from utils.logger import logger
from config.settings import settings

try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

try:
    from lightgbm import LGBMClassifier
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False

try:
    from catboost import CatBoostClassifier
    HAS_CATBOOST = True
except ImportError:
    HAS_CATBOOST = False


class MLModelTrainer:
    """Train and evaluate multiple ML models."""

    def __init__(self):
        self.model_dir = settings.model_dir
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.models = {}
        self.results = {}
        self.scaler = StandardScaler()
        self.imputer = SimpleImputer(strategy="median")
        self.feature_columns = []

    def prepare_data(
        self, df: pd.DataFrame, feature_columns: list[str], target: str = "team1_win"
    ) -> tuple:
        """Prepare training and test data."""
        logger.info(f"Preparing data with {len(feature_columns)} features...")

        # Filter valid rows
        valid = df[df[target].notna()].copy()
        logger.info(f"Valid rows: {len(valid)}")

        X = valid[feature_columns].copy()
        y = valid[target].astype(int)

        # Replace inf with nan
        X = X.replace([np.inf, -np.inf], np.nan)

        # Impute missing values
        X_imputed = pd.DataFrame(
            self.imputer.fit_transform(X),
            columns=feature_columns,
            index=X.index,
        )

        # Scale features
        X_scaled = pd.DataFrame(
            self.scaler.fit_transform(X_imputed),
            columns=feature_columns,
            index=X.index,
        )

        # Train-test split (time-based: last 20% as test)
        split_idx = int(len(X_scaled) * (1 - settings.test_size))
        X_train = X_scaled.iloc[:split_idx]
        X_test = X_scaled.iloc[split_idx:]
        y_train = y.iloc[:split_idx]
        y_test = y.iloc[split_idx:]

        self.feature_columns = feature_columns
        logger.info(f"Train: {len(X_train)}, Test: {len(X_test)}")

        return X_train, X_test, y_train, y_test

    def _build_models(self) -> dict:
        """Initialize all models."""
        models = {
            "logistic_regression": LogisticRegression(
                C=1.0, max_iter=1000, random_state=settings.random_state,
                class_weight="balanced",
            ),
            "random_forest": RandomForestClassifier(
                n_estimators=200, max_depth=12, min_samples_split=5,
                min_samples_leaf=2, random_state=settings.random_state,
                class_weight="balanced", n_jobs=-1,
            ),
        }

        if HAS_XGBOOST:
            models["xgboost"] = XGBClassifier(
                n_estimators=300, max_depth=6, learning_rate=0.05,
                subsample=0.8, colsample_bytree=0.8, reg_alpha=0.1,
                reg_lambda=1.0, random_state=settings.random_state,
                eval_metric="logloss", use_label_encoder=False,
            )

        if HAS_LIGHTGBM:
            models["lightgbm"] = LGBMClassifier(
                n_estimators=300, max_depth=8, learning_rate=0.05,
                subsample=0.8, colsample_bytree=0.8, reg_alpha=0.1,
                reg_lambda=1.0, random_state=settings.random_state,
                verbose=-1,
            )

        if HAS_CATBOOST:
            models["catboost"] = CatBoostClassifier(
                iterations=300, depth=6, learning_rate=0.05,
                l2_leaf_reg=3, random_seed=settings.random_state,
                verbose=0,
            )

        return models

    def train_all(
        self, df: pd.DataFrame, feature_columns: list[str], target: str = "team1_win"
    ) -> dict:
        """Train all models and return results."""
        X_train, X_test, y_train, y_test = self.prepare_data(df, feature_columns, target)
        models = self._build_models()
        results = {}

        for name, model in models.items():
            logger.info(f"Training {name}...")
            try:
                model.fit(X_train, y_train)

                # Predictions
                y_pred = model.predict(X_test)
                y_prob = model.predict_proba(X_test)[:, 1]

                # Metrics
                metrics = {
                    "accuracy": accuracy_score(y_test, y_pred),
                    "precision": precision_score(y_test, y_pred, zero_division=0),
                    "recall": recall_score(y_test, y_pred, zero_division=0),
                    "f1": f1_score(y_test, y_pred, zero_division=0),
                    "roc_auc": roc_auc_score(y_test, y_prob),
                    "log_loss": log_loss(y_test, y_prob),
                }

                # Cross-validation
                cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=settings.random_state)
                X_all = pd.concat([X_train, X_test])
                y_all = pd.concat([y_train, y_test])
                cv_scores = cross_val_score(model, X_all, y_all, cv=cv, scoring="accuracy")
                metrics["cv_accuracy_mean"] = cv_scores.mean()
                metrics["cv_accuracy_std"] = cv_scores.std()

                results[name] = metrics
                self.models[name] = model

                # Save model
                model_path = self.model_dir / f"{name}.pkl"
                with open(model_path, "wb") as f:
                    pickle.dump(model, f)

                logger.info(
                    f"{name}: accuracy={metrics['accuracy']:.4f}, "
                    f"AUC={metrics['roc_auc']:.4f}, "
                    f"CV={metrics['cv_accuracy_mean']:.4f}+/-{metrics['cv_accuracy_std']:.4f}"
                )

            except Exception as e:
                logger.error(f"Failed to train {name}: {e}")
                results[name] = {"error": str(e)}

        # Save scaler and imputer
        with open(self.model_dir / "scaler.pkl", "wb") as f:
            pickle.dump(self.scaler, f)
        with open(self.model_dir / "imputer.pkl", "wb") as f:
            pickle.dump(self.imputer, f)
        with open(self.model_dir / "feature_columns.pkl", "wb") as f:
            pickle.dump(self.feature_columns, f)

        self.results = results
        return results

    def predict(self, X: pd.DataFrame, model_name: str = None) -> dict:
        """Make predictions using trained models."""
        if not self.models:
            self._load_models()

        X = X.copy()
        X = X.replace([np.inf, -np.inf], np.nan)

        # Ensure same features
        for col in self.feature_columns:
            if col not in X.columns:
                X[col] = 0

        X = X[self.feature_columns]
        X_imputed = pd.DataFrame(
            self.imputer.transform(X),
            columns=self.feature_columns,
        )
        X_scaled = pd.DataFrame(
            self.scaler.transform(X_imputed),
            columns=self.feature_columns,
        )

        predictions = {}

        if model_name and model_name in self.models:
            model = self.models[model_name]
            prob = model.predict_proba(X_scaled)[:, 1]
            predictions[model_name] = prob
        else:
            for name, model in self.models.items():
                try:
                    prob = model.predict_proba(X_scaled)[:, 1]
                    predictions[name] = prob
                except Exception as e:
                    logger.warning(f"Prediction failed for {name}: {e}")

        return predictions

    def _load_models(self):
        """Load saved models from disk."""
        for model_file in self.model_dir.glob("*.pkl"):
            name = model_file.stem
            if name in ("scaler", "imputer", "feature_columns", "bayesian_strengths"):
                continue
            try:
                with open(model_file, "rb") as f:
                    self.models[name] = pickle.load(f)
                logger.info(f"Loaded model: {name}")
            except Exception as e:
                logger.warning(f"Failed to load {name}: {e}")

        # Load scaler, imputer, feature_columns
        try:
            with open(self.model_dir / "scaler.pkl", "rb") as f:
                self.scaler = pickle.load(f)
            with open(self.model_dir / "imputer.pkl", "rb") as f:
                self.imputer = pickle.load(f)
            with open(self.model_dir / "feature_columns.pkl", "rb") as f:
                self.feature_columns = pickle.load(f)
        except FileNotFoundError:
            logger.warning("Scaler/imputer/feature_columns not found")

    def get_feature_importance(self, model_name: str = "xgboost") -> pd.DataFrame:
        """Get feature importances from a model."""
        if model_name not in self.models:
            if not self.models:
                self._load_models()
            if model_name not in self.models:
                return pd.DataFrame()

        model = self.models[model_name]

        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
        elif hasattr(model, "coef_"):
            importances = np.abs(model.coef_[0])
        else:
            return pd.DataFrame()

        fi = pd.DataFrame({
            "feature": self.feature_columns,
            "importance": importances,
        }).sort_values("importance", ascending=False)

        return fi

    def get_best_model(self) -> tuple[str, object]:
        """Return the best performing model based on AUC."""
        if not self.results:
            return None, None

        best_name = max(
            self.results,
            key=lambda k: self.results[k].get("roc_auc", 0),
        )
        return best_name, self.models.get(best_name)
