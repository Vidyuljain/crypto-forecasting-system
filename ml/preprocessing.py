"""
preprocessing.py — Create features for cryptocurrency price forecasting.

Turns raw date + price data into model inputs (X) and target (y).
"""

import pandas as pd


def create_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """
    Build features and target from historical price data.

    Args:
        df: DataFrame with columns: date, price (sorted by date).

    Returns:
        X: Feature matrix (previous_price, 7_day_average)
        y: Target values (future price)
    """
    data = df.copy()

    # Feature: price from the previous day.
    data["previous_price"] = data["price"].shift(1)

    # Feature: average price over the last 7 days.
    data["7_day_average"] = data["price"].rolling(window=7).mean()

    # Target: next day's price (what we want to predict).
    data["future_price"] = data["price"].shift(-1)

    # Remove rows with missing values (first rows lack history, last row has no future price).
    data = data.dropna()

    # Features used to train the model.
    X = data[["previous_price", "7_day_average"]]

    # Target the model should predict.
    y = data["future_price"]

    return X, y
