"""
Reinforcement Learning Self-Correction System.

When a prediction goes WRONG:
  1. Analyze WHY it went wrong (feature importance shift)
  2. Adjust model weights using reward/penalty (RL)
  3. Fine-tune the model on the new match data
  4. Track correction history for continuous improvement

RL Approach:
  - State: match features (venue, form, h2h, weather, toss)
  - Action: predicted winner + confidence
  - Reward: +1 correct, -1 wrong, scaled by confidence
  - Policy: adjust ensemble weights + retrain weak models

Every match that completes → auto-train → auto-correct → improve.
"""

import json
import time
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, date

from utils.logger import logger
from config.settings import settings

RL_DIR = settings.data_dir / "rl"
RL_DIR.mkdir(parents=True, exist_ok=True)

HISTORY_FILE = RL_DIR / "match_history.json"
WEIGHTS_FILE = RL_DIR / "rl_weights.json"
REWARDS_FILE = RL_DIR / "reward_history.json"


class RLTrainer:
    """
    Reinforcement Learning trainer that auto-corrects predictions.

    After each match:
      1. Compare prediction vs actual result
      2. Calculate reward (+1 correct, -1 wrong, scaled by confidence)
      3. Update model weights using policy gradient
      4. Retrain models on new data
      5. Track improvement over time
    """

    # Default model weights
    DEFAULT_WEIGHTS = {
        "catboost": 0.20,
        "xgboost": 0.18,
        "lightgbm": 0.18,
        "random_forest": 0.12,
        "logistic_regression": 0.08,
        "bayesian": 0.12,
        "monte_carlo": 0.07,
        "neural_net": 0.05,
    }

    # RL hyperparameters
    LEARNING_RATE = 0.05       # How fast weights adjust
    DISCOUNT_FACTOR = 0.95     # Future reward discount
    EXPLORATION_RATE = 0.1     # Explore vs exploit
    MIN_WEIGHT = 0.02          # Minimum model weight
    MAX_WEIGHT = 0.40          # Maximum model weight

    def __init__(self):
        self.weights = self._load_weights()
        self.match_history = self._load_history()
        self.reward_history = self._load_rewards()

    # ── Core RL Loop ─────────────────────────────────────────────────

    def process_match_result(self, match_data: dict) -> dict:
        """
        Main RL loop — called after every completed match.

        match_data: {
            "team1": str, "team2": str, "winner": str,
            "predicted_winner": str, "confidence": float,
            "model_predictions": {model: prediction},
            "venue": str, "toss_winner": str, "toss_decision": str,
            "score_team1": int, "score_team2": int (optional)
        }

        Returns: {reward, weights_before, weights_after, models_corrected}
        """
        team1 = match_data["team1"]
        team2 = match_data["team2"]
        actual_winner = match_data["winner"]
        predicted_winner = match_data.get("predicted_winner", "")
        confidence = match_data.get("confidence", 0.5)
        model_preds = match_data.get("model_predictions", {})

        is_correct = predicted_winner == actual_winner
        logger.info(f"RL: {team1} vs {team2} — Predicted: {predicted_winner}, Actual: {actual_winner} — {'CORRECT' if is_correct else 'WRONG'}")

        # Step 1: Calculate reward
        reward = self._calculate_reward(is_correct, confidence)

        # Step 2: Save old weights
        weights_before = dict(self.weights)

        # Step 3: Update weights via RL policy gradient
        models_corrected = self._update_weights(model_preds, actual_winner, team1, team2, confidence)

        # Step 4: Save match to history
        match_record = {
            "date": datetime.now().isoformat(),
            "team1": team1,
            "team2": team2,
            "winner": actual_winner,
            "predicted_winner": predicted_winner,
            "confidence": confidence,
            "correct": is_correct,
            "reward": reward,
            "model_predictions": model_preds,
            "weights_before": weights_before,
            "weights_after": dict(self.weights),
        }
        self.match_history.append(match_record)
        self._save_history()

        # Step 5: Track reward
        self.reward_history.append({
            "date": datetime.now().isoformat(),
            "reward": reward,
            "cumulative": sum(r["reward"] for r in self.reward_history) + reward,
            "accuracy": self._get_rolling_accuracy(10),
        })
        self._save_rewards()

        # Step 6: Retrain if enough new data
        retrained = False
        if len(self.match_history) % 3 == 0:  # Retrain every 3 matches
            retrained = self._trigger_retrain()

        logger.info(f"RL: Reward={reward:.2f}, Models corrected={models_corrected}, Retrained={retrained}")

        return {
            "correct": is_correct,
            "reward": reward,
            "weights_before": weights_before,
            "weights_after": dict(self.weights),
            "models_corrected": models_corrected,
            "retrained": retrained,
            "total_matches": len(self.match_history),
            "rolling_accuracy": self._get_rolling_accuracy(10),
        }

    # ── Reward Function ──────────────────────────────────────────────

    def _calculate_reward(self, correct: bool, confidence: float) -> float:
        """
        RL reward function:
          - Correct + high confidence = big positive reward
          - Correct + low confidence = small positive reward
          - Wrong + high confidence = big negative penalty (overconfident)
          - Wrong + low confidence = small negative penalty
        """
        if correct:
            # Reward scales with confidence
            return 1.0 * confidence
        else:
            # Penalty scales MORE with confidence (punish overconfidence)
            return -1.5 * confidence

    # ── Weight Update (Policy Gradient) ──────────────────────────────

    def _update_weights(self, model_preds: dict, actual_winner: str,
                         team1: str, team2: str, confidence: float) -> list:
        """
        Update model weights based on which models got it right/wrong.

        Models that predicted correctly: increase weight
        Models that predicted wrong: decrease weight
        """
        corrected = []

        for model, pred in model_preds.items():
            if model not in self.weights:
                self.weights[model] = 0.10

            # Determine if this model was correct
            model_winner = None
            if isinstance(pred, dict):
                model_winner = pred.get("predicted_winner") or pred.get("winner")
                if not model_winner:
                    # Check probabilities
                    t1_prob = pred.get("team1_win_prob", pred.get("prob", 0.5))
                    model_winner = team1 if t1_prob > 0.5 else team2
            elif isinstance(pred, str):
                model_winner = pred
            elif isinstance(pred, (int, float)):
                model_winner = team1 if pred > 0.5 else team2

            if model_winner:
                model_correct = model_winner == actual_winner

                # Policy gradient update
                old_weight = self.weights[model]
                if model_correct:
                    # Reward: increase weight
                    delta = self.LEARNING_RATE * confidence * 0.5
                    self.weights[model] = min(old_weight + delta, self.MAX_WEIGHT)
                else:
                    # Penalty: decrease weight
                    delta = self.LEARNING_RATE * confidence * 0.8
                    self.weights[model] = max(old_weight - delta, self.MIN_WEIGHT)
                    corrected.append(model)

        # Normalize weights to sum to 1.0
        total = sum(self.weights.values())
        if total > 0:
            self.weights = {k: v / total for k, v in self.weights.items()}

        self._save_weights()
        return corrected

    # ── Auto Retrain ─────────────────────────────────────────────────

    def _trigger_retrain(self) -> bool:
        """Retrain models on updated data including new match results."""
        try:
            logger.info("RL: Triggering model retrain with new match data...")

            # Append new match results to training data
            self._append_new_matches_to_data()

            # Retrain
            from train import main as train_main
            train_main()

            logger.info("RL: Retrain complete!")
            return True
        except Exception as e:
            logger.warning(f"RL: Retrain failed: {e}")
            # Try lightweight retrain (just Bayesian update)
            try:
                from models.bayesian_model import BayesianPredictor
                bp = BayesianPredictor()
                bp.fit_from_data()
                for match in self.match_history[-5:]:
                    bp.update_with_result(match["team1"], match["team2"], match["winner"])
                bp.save()
                logger.info("RL: Bayesian update successful (lightweight retrain)")
                return True
            except Exception:
                pass
            return False

    def _append_new_matches_to_data(self):
        """Add recent match results to the processed data CSV."""
        csv_path = settings.processed_data_dir / "matches_processed.csv"
        if not csv_path.exists():
            return

        try:
            df = pd.read_csv(csv_path)
            existing_count = len(df)

            new_rows = []
            for match in self.match_history:
                # Check if already in data
                key = f"{match['team1']}_{match['team2']}_{match['date'][:10]}"
                if key not in df.get("match_key", pd.Series()).values:
                    new_rows.append({
                        "team1": match["team1"],
                        "team2": match["team2"],
                        "winner": match["winner"],
                        "date": match["date"][:10],
                        "season": 2026,
                        "venue": match.get("venue", ""),
                        "toss_winner": match.get("toss_winner", ""),
                        "toss_decision": match.get("toss_decision", ""),
                        "match_key": key,
                    })

            if new_rows:
                new_df = pd.DataFrame(new_rows)
                df = pd.concat([df, new_df], ignore_index=True)
                df.to_csv(csv_path, index=False)
                logger.info(f"RL: Added {len(new_rows)} new matches to training data ({existing_count} → {len(df)})")
        except Exception as e:
            logger.warning(f"RL: Could not append match data: {e}")

    # ── Analytics ─────────────────────────────────────────────────────

    def _get_rolling_accuracy(self, window: int = 10) -> float:
        """Get accuracy over last N matches."""
        if not self.match_history:
            return 0.0
        recent = self.match_history[-window:]
        correct = sum(1 for m in recent if m.get("correct", False))
        return round(correct / len(recent), 4)

    def get_rl_report(self) -> dict:
        """Get comprehensive RL performance report."""
        if not self.match_history:
            return {"status": "No matches processed yet", "total_matches": 0}

        total = len(self.match_history)
        correct = sum(1 for m in self.match_history if m.get("correct"))
        total_reward = sum(m.get("reward", 0) for m in self.match_history)

        return {
            "total_matches": total,
            "correct_predictions": correct,
            "wrong_predictions": total - correct,
            "overall_accuracy": round(correct / total, 4) if total > 0 else 0,
            "rolling_accuracy_10": self._get_rolling_accuracy(10),
            "rolling_accuracy_5": self._get_rolling_accuracy(5),
            "total_reward": round(total_reward, 2),
            "avg_reward": round(total_reward / total, 3) if total > 0 else 0,
            "current_weights": dict(self.weights),
            "retrains_done": total // 3,
            "last_match": self.match_history[-1] if self.match_history else None,
            "improvement_trend": self._get_improvement_trend(),
        }

    def _get_improvement_trend(self) -> str:
        """Check if model is improving over time."""
        if len(self.match_history) < 6:
            return "not_enough_data"
        first_half = self.match_history[:len(self.match_history) // 2]
        second_half = self.match_history[len(self.match_history) // 2:]
        acc1 = sum(1 for m in first_half if m.get("correct")) / len(first_half)
        acc2 = sum(1 for m in second_half if m.get("correct")) / len(second_half)
        if acc2 > acc1 + 0.05:
            return "improving"
        elif acc2 < acc1 - 0.05:
            return "declining"
        return "stable"

    def get_optimal_weights(self) -> dict:
        """Return RL-optimized weights for the ensemble."""
        return dict(self.weights)

    # ── Persistence ──────────────────────────────────────────────────

    def _load_weights(self) -> dict:
        if WEIGHTS_FILE.exists():
            return json.loads(WEIGHTS_FILE.read_text())
        return dict(self.DEFAULT_WEIGHTS)

    def _save_weights(self):
        WEIGHTS_FILE.write_text(json.dumps(self.weights, indent=2))

    def _load_history(self) -> list:
        if HISTORY_FILE.exists():
            return json.loads(HISTORY_FILE.read_text())
        return []

    def _save_history(self):
        HISTORY_FILE.write_text(json.dumps(self.match_history, indent=2, default=str))

    def _load_rewards(self) -> list:
        if REWARDS_FILE.exists():
            return json.loads(REWARDS_FILE.read_text())
        return []

    def _save_rewards(self):
        REWARDS_FILE.write_text(json.dumps(self.reward_history, indent=2, default=str))
