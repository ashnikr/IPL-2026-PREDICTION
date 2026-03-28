"""
SHAP-based Model Explainability.

Explains predictions using SHAP values, feature importance,
and human-readable factor analysis.
"""

import pickle
import numpy as np
import pandas as pd
from pathlib import Path

from utils.logger import logger
from config.settings import settings

try:
    import shap
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False
    logger.warning("SHAP not installed. Install with: pip install shap")


class PredictionExplainer:
    """Explain match predictions using SHAP and feature analysis."""

    def __init__(self):
        self.model_dir = settings.model_dir
        self.explainer = None
        self.model = None
        self.feature_columns = []

    def load_model(self, model_name: str = "catboost"):
        """Load model and create SHAP explainer."""
        model_path = self.model_dir / f"{model_name}.pkl"
        fc_path = self.model_dir / "feature_columns.pkl"

        try:
            with open(model_path, "rb") as f:
                self.model = pickle.load(f)
            with open(fc_path, "rb") as f:
                self.feature_columns = pickle.load(f)

            if HAS_SHAP:
                self.explainer = shap.TreeExplainer(self.model)
                logger.info(f"SHAP explainer ready for {model_name}")
            else:
                logger.info(f"Model loaded but SHAP not available for {model_name}")

        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")

    def explain_prediction(
        self, features: pd.DataFrame, team1: str, team2: str
    ) -> dict:
        """Generate SHAP-based explanation for a prediction."""
        if self.model is None:
            self.load_model()

        if self.model is None:
            return {"error": "No model loaded"}

        # Ensure feature alignment
        for col in self.feature_columns:
            if col not in features.columns:
                features[col] = 0
        X = features[self.feature_columns].copy()
        X = X.replace([np.inf, -np.inf], np.nan).fillna(0)

        # Get prediction
        prob = self.model.predict_proba(X)[0][1]

        explanation = {
            "team1": team1,
            "team2": team2,
            "team1_win_prob": round(float(prob), 4),
            "team2_win_prob": round(float(1 - prob), 4),
        }

        # SHAP values
        if HAS_SHAP and self.explainer is not None:
            try:
                shap_values = self.explainer.shap_values(X)
                if isinstance(shap_values, list):
                    sv = shap_values[1][0]  # Class 1 (team1 wins)
                else:
                    sv = shap_values[0]

                # Top positive and negative factors
                feature_impacts = list(zip(self.feature_columns, sv))
                feature_impacts.sort(key=lambda x: abs(x[1]), reverse=True)

                top_factors = []
                for feat, impact in feature_impacts[:10]:
                    direction = "favors " + team1 if impact > 0 else "favors " + team2
                    val = X[feat].values[0]
                    top_factors.append({
                        "feature": feat,
                        "impact": round(float(impact), 4),
                        "value": round(float(val), 4) if pd.notna(val) else None,
                        "direction": direction,
                    })

                explanation["shap_factors"] = top_factors
                explanation["base_value"] = round(float(self.explainer.expected_value[1]
                    if isinstance(self.explainer.expected_value, (list, np.ndarray))
                    else self.explainer.expected_value), 4)

            except Exception as e:
                logger.warning(f"SHAP computation failed: {e}")
                explanation["shap_factors"] = []
        else:
            # Fallback: use feature importance
            explanation["shap_factors"] = self._fallback_importance(X)

        # Human-readable summary
        explanation["summary"] = self._generate_summary(explanation, team1, team2)

        return explanation

    def _fallback_importance(self, X: pd.DataFrame) -> list[dict]:
        """Use model feature importance as fallback when SHAP unavailable."""
        if not hasattr(self.model, "feature_importances_"):
            return []

        importances = self.model.feature_importances_
        impacts = []
        for feat, imp in sorted(zip(self.feature_columns, importances),
                                 key=lambda x: x[1], reverse=True)[:10]:
            val = X[feat].values[0] if feat in X.columns else 0
            impacts.append({
                "feature": feat,
                "importance": round(float(imp), 4),
                "value": round(float(val), 4) if pd.notna(val) else None,
            })
        return impacts

    def _generate_summary(self, explanation: dict, team1: str, team2: str) -> str:
        """Generate human-readable prediction summary."""
        prob = explanation["team1_win_prob"]
        winner = team1 if prob > 0.5 else team2
        win_pct = max(prob, 1 - prob) * 100

        lines = [f"Predicted winner: {winner} ({win_pct:.1f}% probability)"]

        factors = explanation.get("shap_factors", [])
        if factors:
            lines.append("\nKey influencing factors:")
            for i, f in enumerate(factors[:5], 1):
                feat_name = f["feature"].replace("_", " ").title()
                direction = f.get("direction", "")
                lines.append(f"  {i}. {feat_name} - {direction}")

        return "\n".join(lines)

    def get_global_feature_importance(self, n_top: int = 20) -> pd.DataFrame:
        """Get global feature importance across all predictions."""
        if self.model is None:
            self.load_model()

        if self.model is None:
            return pd.DataFrame()

        if hasattr(self.model, "feature_importances_"):
            fi = pd.DataFrame({
                "feature": self.feature_columns,
                "importance": self.model.feature_importances_,
            }).sort_values("importance", ascending=False).head(n_top)
            return fi

        return pd.DataFrame()
