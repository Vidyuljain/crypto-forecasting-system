"""
collector.py — Download historical crypto prices and save them as CSV files.

This module is used to build datasets for the ML forecasting step later.
It fetches data from CoinGecko, cleans it with pandas, and stores it in
the project's data/raw/ folder.
"""

from pathlib import Path

import pandas as pd

from coingecko import get_historical_data

# Folder where CSV files are saved (backend/../data/raw/)
RAW_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def collect_historical_data(coin_id: str, days: int = 365) -> pd.DataFrame:
    """
    Fetch historical prices for a coin and save them to a CSV file.

    Args:
        coin_id: CoinGecko coin id (example: "bitcoin", "ethereum").
        days:    How many days of history to download (default: 365).

    Returns:
        A pandas DataFrame with columns: date, price
    """
    # Step 1: Call CoinGecko market_chart endpoint through our helper function.
    response = get_historical_data(coin_id, days=days)

    # Step 2: Extract the "prices" list from the API response.
    # Each item looks like: [timestamp_in_milliseconds, price_in_usd]
    prices = response.get("prices", [])
    if not prices:
        raise ValueError(f"No price data returned for coin_id='{coin_id}'")

    # Step 3: Build a pandas DataFrame from timestamp + price pairs.
    df = pd.DataFrame(prices, columns=["timestamp_ms", "price"])

    # Step 4: Convert millisecond timestamps into readable dates.
    # Example output: "2024-06-17 12:00:00"
    df["date"] = pd.to_datetime(df["timestamp_ms"], unit="ms")

    # Step 5: Keep only the columns we need for forecasting.
    df = df[["date", "price"]]

    # Step 6: Create data/raw/ folder if it does not exist yet.
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Step 7: Save CSV file (example: data/raw/bitcoin.csv).
    csv_path = RAW_DATA_DIR / f"{coin_id}.csv"
    df.to_csv(csv_path, index=False)

    # Step 8: Return the dataframe so other code can use it immediately.
    return df
