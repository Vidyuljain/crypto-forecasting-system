"""
data_loader.py — Load cryptocurrency historical data from the backend API.

Used by the ML module to fetch training data for price forecasting models.
"""

import requests
import pandas as pd

# Backend API base URL (FastAPI server must be running).
API_BASE_URL = "http://127.0.0.1:8000"


def load_crypto_data(coin_id: str) -> pd.DataFrame:
    """
    Load historical price data for a coin from the backend ML endpoint.

    Args:
        coin_id: CoinGecko coin id (example: "bitcoin", "ethereum").

    Returns:
        A pandas DataFrame with columns: date, price (sorted oldest to newest).
    """
    # Step 1: Call the backend ML data endpoint.
    url = f"{API_BASE_URL}/ml/data/{coin_id}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    # Step 2: Get JSON list of {date, price} objects.
    data = response.json()

    # Step 3: Convert to a pandas DataFrame.
    df = pd.DataFrame(data)

    # Step 4: Convert date strings into proper datetime values.
    df["date"] = pd.to_datetime(df["date"])

    # Step 5: Sort rows from oldest to newest (important for forecasting).
    df = df.sort_values("date").reset_index(drop=True)

    return df[["date", "price"]]
