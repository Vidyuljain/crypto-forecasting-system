"""
collector.py — Download historical crypto prices and save them as CSV files.

This module is used to build datasets for the ML forecasting step later.
It fetches data from CoinGecko, cleans it with pandas, and stores it in
the project's data/raw/ folder.
"""

from pathlib import Path
import time

import pandas as pd

from coingecko import get_historical_data, get_top_100_coins

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


def collect_top_100_data(days: int = 365) -> dict:
    """
    Download historical data for the top 100 coins and save each as a CSV file.

    Example output files:
        data/raw/bitcoin.csv
        data/raw/ethereum.csv
        data/raw/dogecoin.csv

    Returns:
        Dictionary with coins_collected count and failed_coins list.
    """
    # Step 1: Get the current top 100 cryptocurrencies.
    top_coins = get_top_100_coins()
    total_coins = len(top_coins)
    collected_count = 0
    failed_coins = []

    # Step 2: Loop through each coin and save its historical data.
    for index, coin in enumerate(top_coins, start=1):
        coin_id = coin["id"]
        coin_name = coin.get("name", coin_id)

        # Show simple progress in the terminal while collecting data.
        print(f"Collecting {index}/{total_coins} {coin_name}")

        try:
            collect_historical_data(coin_id, days=days)
            collected_count += 1
        except Exception as exc:
            # Keep going even if one coin fails (rate limit, network, missing data).
            failed_coins.append(coin_id)
            print(f"Failed to collect {coin_name}: {exc}")
            continue

        # Step 3: Wait between API calls to avoid CoinGecko 429 rate limit errors.
        if index < total_coins:
            time.sleep(2)

    return {
        "coins_collected": collected_count,
        "failed_coins": failed_coins,
    }
