"""
Self-Learning Calibration System.

Tracks prediction accuracy over time and auto-adjusts model weights
to improve future predictions. Learns from every match result.
"""

import json
from datetime import datetime, date
from pathlib import Path

import numpy as np

from utils.logger import logger
from config.settings import settings


class PredictionCalibrator:
    """Self-learning system that calibrates model weights based on accuracy."""

    def __init__(self):
        self.calibration_file = settings.data_dir / "calibration.json"
        self.history_file = settings.data_dir / "prediction_history.json"
        self._calibration = self._load_calibration()
        self._history = self._load_history()

    def _load_calibration(self) -> dict:
        """Load calibration data."""
        if self.calibration_file.exists():
            return json.loads(self.calibration_file.read_text())
        return {
            "model_accuracy": {},
            "weight_adjustments": {},
            "total_predictions": 0,
            "correct_predictions": 0,
            "last_updated": None,
        }

    def _load_history(self) -> list[dict]:
        """Load prediction history."""
        if self.history_file.exists():
            return json.loads(self.history_file.read_text())
        return []

    def _save_calibration(self):
        """Save calibration data."""
        self.calibration_file.write_text(json.dumps(self._calibration, indent=2, default=str))

    def _save_history(self):
        """Save prediction history."""
        self.history_file.write_text(json.dumps(self._history, indent=2, default=str))

    def record_prediction(self, prediction: dict):
        """Record a prediction for later evaluation."""
        record = {
            "date": str(date.today()),
            "timestamp": datetime.now().isoformat(),
            "team1": prediction.get("team1"),
            "team2": prediction.get("team2"),
            "predicted_winner": prediction.get("predicted_winner"),
            "team1_win_prob": prediction.get("team1_win_prob"),
            "team2_win_prob": prediction.get("team2_win_prob"),
            "confidence": prediction.get("confidence"),
            "model_predictions": prediction.get("model_predictions", {}),
            "actual_winner": None,  # filled in later
            "correct": None,
        }
        self._history.append(record)
        self._save_history()

    def record_result(self, team1: str, team2: str, actual_winner: str):
        """Record actual match result and evaluate prediction accuracy."""
        # Find matching prediction
        for record in reversed(self._history):
            if record["actual_winner"] is not None:
                continue
            if (record["team1"] == team1 and record["team2"] == team2) or \
               (record["team1"] == team2 and record["team2"] == team1):
                record["actual_winner"] = actual_winner
                record["correct"] = record["predicted_winner"] == actual_winner

                # Update accuracy stats
                self._calibration["total_predictions"] += 1
                if record["correct"]:
                    self._calibration["correct_predictions"] += 1

                # Update per-model accuracy
                self._update_model_accuracy(record)

                # Recalibrate weights
                self._recalibrate_weights()

                self._calibration["last_updated"] = datetime.now().isoformat()
                self._save_calibration()
                self._save_history()

                accuracy = self.get_overall_accuracy()
                logger.info(
                    f"Result recorded: {actual_winner} won | "
                    f"Prediction {'CORRECT' if record['correct'] else 'WRONG'} | "
                    f"Overall accuracy: {accuracy:.1%}"
                )
                return record

        logger.warning(f"No matching prediction found for {team1} vs {team2}")
        return None

    def _update_model_accuracy(self, record: dict):
        """Update accuracy tracking for individual models."""
        model_preds = record.get("model_predictions", {})
        actual = record["actual_winner"]
        team1 = record["team1"]

        for model_name, prob in model_preds.items():
            if model_name not in self._calibration["model_accuracy"]:
                self._calibration["model_accuracy"][model_name] = {
                    "correct": 0, "total": 0, "brier_sum": 0.0,
                }

            stats = self._calibration["model_accuracy"][model_name]
            stats["total"] += 1

            # Did this model predict correctly?
            model_predicted_t1 = prob > 0.5
            actual_is_t1 = actual == team1
            if model_predicted_t1 == actual_is_t1:
                stats["correct"] += 1

            # Brier score (lower is better)
            actual_prob = 1.0 if actual_is_t1 else 0.0
            stats["brier_sum"] += (prob - actual_prob) ** 2

    def _recalibrate_weights(self):
        """Recalibrate model weights based on accumulated accuracy data."""
        model_acc = self._calibration["model_accuracy"]

        if not model_acc or self._calibration["total_predictions"] < 3:
            return  # Need minimum data before adjusting

        # Calculate performance score for each model
        scores = {}
        for model, stats in model_acc.items():
            if stats["total"] < 2:
                continue
            accuracy = stats["correct"] / stats["total"]
            brier = stats["brier_sum"] / stats["total"]
            # Combined score: accuracy weighted more than calibration
            scores[model] = accuracy * 0.7 + (1 - brier) * 0.3

        if not scores:
            return

        # Normalize to weights
        total = sum(scores.values())
        if total == 0:
            return

        new_weights = {model: round(score / total, 4) for model, score in scores.items()}
        self._calibration["weight_adjustments"] = new_weights

        logger.info(f"Recalibrated weights: {new_weights}")

    def get_adjusted_weights(self) -> dict:
        """Get calibrated model weights (blended with defaults)."""
        adjustments = self._calibration.get("weight_adjustments", {})

        if not adjustments or self._calibration["total_predictions"] < 5:
            return {}  # Not enough data, use defaults

        return adjustments

    def get_overall_accuracy(self) -> float:
        """Get overall prediction accuracy."""
        total = self._calibration["total_predictions"]
        if total == 0:
            return 0.0
        return self._calibration["correct_predictions"] / total

    def get_model_leaderboard(self) -> list[dict]:
        """Get ranked model performance."""
        leaderboard = []
        for model, stats in self._calibration["model_accuracy"].items():
            if stats["total"] == 0:
                continue
            leaderboard.append({
                "model": model,
                "accuracy": round(stats["correct"] / stats["total"], 3),
                "brier_score": round(stats["brier_sum"] / stats["total"], 4),
                "predictions": stats["total"],
            })
        return sorted(leaderboard, key=lambda x: x["accuracy"], reverse=True)

    def get_calibration_report(self) -> dict:
        """Get full calibration report."""
        return {
            "overall_accuracy": round(self.get_overall_accuracy(), 3),
            "total_predictions": self._calibration["total_predictions"],
            "correct_predictions": self._calibration["correct_predictions"],
            "model_leaderboard": self.get_model_leaderboard(),
            "adjusted_weights": self.get_adjusted_weights(),
            "last_updated": self._calibration.get("last_updated"),
        }

    def get_confidence_calibration(self) -> dict:
        """Check if confidence scores are well-calibrated."""
        evaluated = [r for r in self._history if r.get("correct") is not None]

        if len(evaluated) < 5:
            return {"status": "insufficient_data", "matches_needed": 5 - len(evaluated)}

        # Bin predictions by confidence
        bins = {"low": [], "medium": [], "high": []}
        for r in evaluated:
            conf = r.get("confidence", 0.5)
            if conf < 0.55:
                bins["low"].append(r["correct"])
            elif conf < 0.70:
                bins["medium"].append(r["correct"])
            else:
                bins["high"].append(r["correct"])

        calibration = {}
        for level, results in bins.items():
            if results:
                calibration[level] = {
                    "count": len(results),
                    "accuracy": round(sum(results) / len(results), 3),
                }

        return {"status": "ok", "bins": calibration}
