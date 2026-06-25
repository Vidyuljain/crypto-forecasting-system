"""
train.py — Full ML training pipeline for cryptocurrency price forecasting.

Loads data from the backend, trains models, evaluates them, and saves results.
"""

import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from data_loader import load_crypto_data
from models import train_linear_model, train_random_forest
from preprocessing import create_features

# Folder where trained models and metrics are saved.
MODELS_DIR = Path(__file__).resolve().parent / "models"


def train_models(coin_id: str) -> dict:
    """
    Train Linear Regression and Random Forest models for one coin.

    Args:
        coin_id: CoinGecko coin id (example: "bitcoin").

    Returns:
        Dictionary with evaluation metrics and best model name.
    """
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Load historical price data from the backend API.
    print(f"Loading data for {coin_id}...")
    df = load_crypto_data(coin_id)

    # Step 2: Create features (X) and target (y).
    X, y = create_features(df)

    # Step 3: Split data — 80% train, 20% test (no shuffle for time series).
    split_index = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_index], X.iloc[split_index:]
    y_train, y_test = y.iloc[:split_index], y.iloc[split_index:]

    # Step 4: Train both models.
    print("Training Linear Regression...")
    linear_model = train_linear_model(X_train, y_train)

    print("Training Random Forest...")
    forest_model = train_random_forest(X_train, y_train)

    # Step 5: Make predictions on the test set.
    linear_predictions = linear_model.predict(X_test)
    forest_predictions = forest_model.predict(X_test)

    # Step 6: Calculate evaluation metrics.
    linear_mae = mean_absolute_error(y_test, linear_predictions)
    linear_rmse = np.sqrt(mean_squared_error(y_test, linear_predictions))
    linear_r2 = r2_score(y_test, linear_predictions)

    forest_mae = mean_absolute_error(y_test, forest_predictions)
    forest_rmse = np.sqrt(mean_squared_error(y_test, forest_predictions))
    forest_r2 = r2_score(y_test, forest_predictions)

    # Pick the model with the lower RMSE (better predictions).
    best_model = "random_forest" if forest_rmse < linear_rmse else "linear_regression"

    metrics = {
        "linear_mae": round(linear_mae, 2),
        "linear_rmse": round(linear_rmse, 2),
        "linear_r2": round(linear_r2, 4),
        "forest_mae": round(forest_mae, 2),
        "forest_rmse": round(forest_rmse, 2),
        "forest_r2": round(forest_r2, 4),
        "best_model": best_model,
    }

    # Step 7: Save trained models with joblib.
    joblib.dump(linear_model, MODELS_DIR / f"{coin_id}_linear.pkl")
    joblib.dump(forest_model, MODELS_DIR / f"{coin_id}_forest.pkl")

    # Step 8: Save metrics as JSON.
    metrics_path = MODELS_DIR / f"{coin_id}_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as file:
        json.dump(metrics, file, indent=2)

    print(f"Models saved to {MODELS_DIR}")
    print(f"Metrics: {metrics}")

    return metrics


if __name__ == "__main__":
    # Example: python train.py (trains models for bitcoin)
    train_models("bitcoin")
