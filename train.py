"""
IPL Match Prediction - Model Training Script.

Run this to:
1. Load/generate data
2. Preprocess
3. Engineer features
4. Train all ML models
5. Train deep learning models
6. Fit Bayesian model
7. Fit Monte Carlo simulator
8. Print evaluation results
"""

import sys
import os
import warnings
warnings.filterwarnings("ignore")

# Fix Windows encoding
os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to path
sys.path.insert(0, ".")

import pandas as pd
import numpy as np
from pathlib import Path

from config.settings import settings
from utils.logger import logger
from scrapers.kaggle_loader import KaggleDataLoader
from features.preprocessor import DataPreprocessor
from features.engineer import FeatureEngineer
from models.ml_models import MLModelTrainer
from models.bayesian_model import BayesianPredictor
from models.monte_carlo import MonteCarloSimulator


def main():
    logger.info("=" * 70)
    logger.info("IPL MATCH PREDICTION SYSTEM - TRAINING PIPELINE")
    logger.info("=" * 70)

    # ── Step 1: Load Data ──────────────────────────────────────────────
    logger.info("\n📊 STEP 1: Loading data...")
    loader = KaggleDataLoader()
    matches_raw, deliveries_raw = loader.load_data()
    logger.info(f"Loaded {len(matches_raw)} matches, {len(deliveries_raw)} deliveries")

    # ── Step 2: Preprocess ─────────────────────────────────────────────
    logger.info("\n🔧 STEP 2: Preprocessing...")
    preprocessor = DataPreprocessor()
    processed = preprocessor.run_full_pipeline(matches_raw, deliveries_raw)
    matches = processed["matches"]
    deliveries = processed["deliveries"]
    player_stats = processed["player_stats"]

    logger.info(f"Processed matches shape: {matches.shape}")
    logger.info(f"Player stats: {player_stats['player_name'].nunique()} players")

    # ── Step 3: Feature Engineering ────────────────────────────────────
    logger.info("\n⚙️ STEP 3: Engineering features...")
    engineer = FeatureEngineer()
    feature_df = engineer.engineer_features(matches, deliveries, player_stats)
    feature_cols = engineer.get_feature_columns(feature_df)

    logger.info(f"Feature matrix: {feature_df.shape}")
    logger.info(f"Number of features: {len(feature_cols)}")
    logger.info(f"Features: {feature_cols[:20]}...")

    # ── Step 4: Train ML Models ────────────────────────────────────────
    logger.info("\n🤖 STEP 4: Training ML models...")
    trainer = MLModelTrainer()
    ml_results = trainer.train_all(feature_df, feature_cols, target="team1_win")

    print("\n" + "=" * 70)
    print("ML MODEL RESULTS")
    print("=" * 70)
    for model_name, metrics in ml_results.items():
        if "error" in metrics:
            print(f"  {model_name}: ERROR - {metrics['error']}")
        else:
            print(f"  {model_name}:")
            print(f"    Accuracy:  {metrics['accuracy']:.4f}")
            print(f"    ROC AUC:   {metrics['roc_auc']:.4f}")
            print(f"    F1 Score:  {metrics['f1']:.4f}")
            print(f"    Log Loss:  {metrics['log_loss']:.4f}")
            print(f"    CV Acc:    {metrics['cv_accuracy_mean']:.4f} +/- {metrics['cv_accuracy_std']:.4f}")
            print()

    # Best model
    best_name, best_model = trainer.get_best_model()
    if best_name:
        print(f"  🏆 Best Model: {best_name} (AUC: {ml_results[best_name]['roc_auc']:.4f})")

    # Feature importance
    fi = trainer.get_feature_importance(best_name or "random_forest")
    if not fi.empty:
        print(f"\n  Top 15 Features ({best_name or 'random_forest'}):")
        for _, row in fi.head(15).iterrows():
            print(f"    {row['feature']:40s} {row['importance']:.4f}")

    # ── Step 5: Train Deep Learning ────────────────────────────────────
    logger.info("\n🧠 STEP 5: Training deep learning models...")
    try:
        from models.deep_learning import NeuralNetPredictor

        nn = NeuralNetPredictor()

        # Prepare data (same as ML models)
        valid = feature_df[feature_df["team1_win"].notna()].copy()
        X = valid[feature_cols].replace([np.inf, -np.inf], np.nan).fillna(0).values
        y = valid["team1_win"].astype(int).values

        # Normalize
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        split = int(len(X) * 0.8)
        X_train, X_val = X_scaled[:split], X_scaled[split:]
        y_train, y_val = y[:split], y[split:]

        nn.build_model(input_dim=X_train.shape[1])
        nn_metrics = nn.train(X_train, y_train, X_val, y_val, epochs=100, batch_size=32)

        print("\n" + "=" * 70)
        print("DEEP LEARNING RESULTS")
        print("=" * 70)
        if "error" not in nn_metrics:
            print(f"  Neural Network:")
            print(f"    Accuracy:  {nn_metrics['accuracy']:.4f}")
            print(f"    ROC AUC:   {nn_metrics['roc_auc']:.4f}")
            print(f"    Epochs:    {nn_metrics['epochs_trained']}")
        else:
            print(f"  Neural Network: {nn_metrics['error']}")

    except Exception as e:
        logger.warning(f"Deep learning training failed: {e}")
        print(f"\n  Deep Learning: Skipped ({e})")

    # ── Step 6: Fit Bayesian Model ─────────────────────────────────────
    logger.info("\n📈 STEP 6: Fitting Bayesian model...")
    bayesian = BayesianPredictor()
    team_strengths = bayesian.fit_analytical(matches)

    print("\n" + "=" * 70)
    print("BAYESIAN TEAM STRENGTHS")
    print("=" * 70)
    sorted_teams = sorted(team_strengths.items(), key=lambda x: x[1]["mean_strength"], reverse=True)
    for team, stats in sorted_teams[:15]:
        print(f"  {team:35s} Strength: {stats['mean_strength']:.4f}  (W:{stats.get('wins',0)} L:{stats.get('losses',0)})")

    # ── Step 7: Fit Monte Carlo ────────────────────────────────────────
    logger.info("\n🎲 STEP 7: Fitting Monte Carlo simulator...")
    mc = MonteCarloSimulator(n_simulations=5000)
    mc.fit(matches, deliveries)

    # Sample prediction
    teams = settings.current_teams
    if len(teams) >= 2:
        sample = mc.simulate_match(teams[0], teams[1])
        print("\n" + "=" * 70)
        print("SAMPLE MONTE CARLO PREDICTION")
        print("=" * 70)
        print(f"  {sample['team1']} vs {sample['team2']}")
        print(f"  {sample['team1']}: {sample['team1_win_prob']*100:.1f}%")
        print(f"  {sample['team2']}: {sample['team2_win_prob']*100:.1f}%")
        print(f"  Avg Score Diff: {sample['avg_score_diff']:.1f}")
        print(f"  Simulations: {sample['simulations']}")

    # ── Summary ────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("TRAINING COMPLETE")
    print("=" * 70)
    print(f"  Data: {len(matches)} matches, {len(deliveries)} deliveries")
    print(f"  Features: {len(feature_cols)}")
    print(f"  ML Models trained: {len([r for r in ml_results.values() if 'error' not in r])}")
    print(f"  Bayesian model: {len(team_strengths)} teams")
    print(f"  Monte Carlo: fitted")
    print(f"  Models saved to: {settings.model_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
