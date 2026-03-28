"""
Deep Learning Models for IPL Prediction.

Neural Network classifier and LSTM for player form sequences.
"""

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, roc_auc_score

from utils.logger import logger
from config.settings import settings

try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers, callbacks
    HAS_TF = True
except ImportError:
    HAS_TF = False
    logger.warning("TensorFlow not available. Deep learning models disabled.")


class NeuralNetPredictor:
    """Feed-forward Neural Network for match prediction."""

    def __init__(self):
        self.model = None
        self.model_path = settings.model_dir / "neural_net"
        self.history = None

    def build_model(self, input_dim: int) -> "keras.Model":
        if not HAS_TF:
            return None

        model = keras.Sequential([
            layers.Input(shape=(input_dim,)),
            layers.BatchNormalization(),
            layers.Dense(256, activation="relu"),
            layers.Dropout(0.3),
            layers.Dense(128, activation="relu"),
            layers.Dropout(0.3),
            layers.Dense(64, activation="relu"),
            layers.Dropout(0.2),
            layers.Dense(32, activation="relu"),
            layers.Dense(1, activation="sigmoid"),
        ])

        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss="binary_crossentropy",
            metrics=["accuracy", keras.metrics.AUC(name="auc")],
        )

        self.model = model
        return model

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        epochs: int = 100,
        batch_size: int = 32,
    ) -> dict:
        if not HAS_TF or self.model is None:
            return {"error": "TensorFlow not available"}

        early_stop = callbacks.EarlyStopping(
            monitor="val_auc", patience=15, restore_best_weights=True, mode="max"
        )
        reduce_lr = callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.5, patience=5, min_lr=1e-6
        )

        self.history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=[early_stop, reduce_lr],
            verbose=0,
        )

        # Evaluate
        y_prob = self.model.predict(X_val, verbose=0).flatten()
        y_pred = (y_prob > 0.5).astype(int)

        metrics = {
            "accuracy": accuracy_score(y_val, y_pred),
            "roc_auc": roc_auc_score(y_val, y_prob),
            "epochs_trained": len(self.history.history["loss"]),
        }

        # Save
        self.model.save(str(self.model_path))
        logger.info(f"Neural Net: accuracy={metrics['accuracy']:.4f}, AUC={metrics['roc_auc']:.4f}")

        return metrics

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not HAS_TF:
            return np.full(len(X), 0.5)

        if self.model is None:
            self.load()

        if self.model is None:
            return np.full(len(X), 0.5)

        return self.model.predict(X, verbose=0).flatten()

    def load(self):
        if not HAS_TF:
            return
        try:
            self.model = keras.models.load_model(str(self.model_path))
            logger.info("Neural network model loaded")
        except Exception as e:
            logger.warning(f"Failed to load neural net: {e}")


class LSTMFormPredictor:
    """LSTM model for predicting player/team form sequences."""

    def __init__(self, sequence_length: int = 10):
        self.sequence_length = sequence_length
        self.model = None
        self.model_path = settings.model_dir / "lstm_form"

    def build_model(self, n_features: int) -> "keras.Model":
        if not HAS_TF:
            return None

        model = keras.Sequential([
            layers.Input(shape=(self.sequence_length, n_features)),
            layers.LSTM(64, return_sequences=True),
            layers.Dropout(0.2),
            layers.LSTM(32),
            layers.Dropout(0.2),
            layers.Dense(16, activation="relu"),
            layers.Dense(1, activation="sigmoid"),
        ])

        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss="binary_crossentropy",
            metrics=["accuracy"],
        )

        self.model = model
        return model

    def prepare_sequences(
        self, df: pd.DataFrame, team: str, feature_cols: list[str], target: str = "team1_win"
    ) -> tuple[np.ndarray, np.ndarray]:
        """Create sequences of team performance for LSTM."""
        # Filter matches involving the team
        team_matches = df[(df["team1"] == team) | (df["team2"] == team)].copy()
        team_matches = team_matches.sort_values("date" if "date" in team_matches.columns else "match_id")

        # Adjust target: 1 if team won
        team_matches["team_won"] = (team_matches["winner"] == team).astype(int)

        features = team_matches[feature_cols].fillna(0).values
        targets = team_matches["team_won"].values

        X, y = [], []
        for i in range(self.sequence_length, len(features)):
            X.append(features[i - self.sequence_length:i])
            y.append(targets[i])

        return np.array(X) if X else np.array([]), np.array(y) if y else np.array([])

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        epochs: int = 50,
    ) -> dict:
        if not HAS_TF or self.model is None:
            return {"error": "TensorFlow not available"}

        if len(X_train) == 0:
            return {"error": "No training data"}

        early_stop = callbacks.EarlyStopping(
            monitor="val_loss", patience=10, restore_best_weights=True
        )

        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=16,
            callbacks=[early_stop],
            verbose=0,
        )

        y_prob = self.model.predict(X_val, verbose=0).flatten()
        y_pred = (y_prob > 0.5).astype(int)

        metrics = {
            "accuracy": accuracy_score(y_val, y_pred),
            "roc_auc": roc_auc_score(y_val, y_prob) if len(np.unique(y_val)) > 1 else 0.5,
        }

        self.model.save(str(self.model_path))
        logger.info(f"LSTM: accuracy={metrics['accuracy']:.4f}, AUC={metrics['roc_auc']:.4f}")

        return metrics

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not HAS_TF:
            return np.full(len(X) if len(X.shape) > 1 else 1, 0.5)

        if self.model is None:
            self.load()

        if self.model is None:
            return np.full(len(X) if len(X.shape) > 1 else 1, 0.5)

        return self.model.predict(X, verbose=0).flatten()

    def load(self):
        if not HAS_TF:
            return
        try:
            self.model = keras.models.load_model(str(self.model_path))
            logger.info("LSTM model loaded")
        except Exception as e:
            logger.warning(f"Failed to load LSTM: {e}")
