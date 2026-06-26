"""
predict.py — Predict future cryptocurrency prices using a trained model.

Loads historical data from CSV files, applies the saved Random Forest model,
and forecasts the next several days of prices.
"""

from pathlib import Path

import joblib
import pandas as pd

from preprocessing import create_features

# Folder where trained models are saved.
MODELS_DIR = Path(__file__).resolve().parent / "models"

# Folder where collected coin CSV files are stored.
RAW_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def predict_future_prices(coin_id: str, days: int = 7) -> list[dict]:
    """
    Predict future prices for a coin using the saved Random Forest model.

    Args:
        coin_id: CoinGecko coin id (example: "bitcoin", "ethereum", "ripple").
        days:    Number of future days to predict (default: 7).

    Returns:
        List of dictionaries: [{"date": "...", "predicted_price": ...}, ...]
    """
    # Step 1: Load historical price data from CSV (data/raw/{coin_id}.csv).
    csv_path = RAW_DATA_DIR / f"{coin_id}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"No CSV data for '{coin_id}' at {csv_path}")

    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # Step 2: Create features from the historical data.
    X, _ = create_features(df)

    # Step 3: Load the saved Random Forest model for this coin.
    # Example: bitcoin -> models/bitcoin/forest.pkl
    model_path = MODELS_DIR / coin_id / "forest.pkl"
    if not model_path.exists():
        raise FileNotFoundError(f"Model not trained for {coin_id}. Run train_all.py")

    model = joblib.load(model_path)

    # Step 4: Start with the latest available feature row and recent prices.
    previous_price = float(X.iloc[-1]["previous_price"])
    seven_day_average = float(X.iloc[-1]["7_day_average"])
    recent_prices = list(df["price"].tail(7))
    last_date = pd.Timestamp(df["date"].iloc[-1])

    predictions = []

    # Step 5: Predict one day at a time and update features for the next day.
    for day_offset in range(1, days + 1):
        # Use a DataFrame with the same column names the model was trained on.
        features = pd.DataFrame(
            {
                "previous_price": [previous_price],
                "7_day_average": [seven_day_average],
            }
        )
        predicted_price = float(model.predict(features)[0])

        future_date = last_date + pd.Timedelta(days=day_offset)

        predictions.append(
            {
                "date": future_date.strftime("%Y-%m-%d"),
                "predicted_price": round(predicted_price, 2),
            }
        )

        # Use the new prediction when building features for the next day.
        previous_price = predicted_price
        recent_prices = recent_prices[1:] + [predicted_price]
        seven_day_average = sum(recent_prices) / len(recent_prices)

    # Step 6: Return JSON-friendly list of predictions.
    return predictions


if __name__ == "__main__":
    # Example: python predict.py
    results = predict_future_prices("bitcoin", days=7)
    for row in results:
        print(row)
