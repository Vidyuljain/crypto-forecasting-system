"""
collector.py — Download historical crypto prices and save them as CSV files.

This module is used to build datasets for the ML forecasting step later.
It fetches data from CoinGecko, cleans it with pandas, and stores it in
the project's data/raw/ folder.
"""

from pathlib import Path
import time

import pandas as pd

from coingecko import get_historical_data, get_top_100_coins, resolve_coin_id

# Folder where CSV files are saved (backend/../data/raw/)
RAW_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def collect_historical_data(coin_id: str, days: int = 365, resolve: bool = True) -> pd.DataFrame:
    """
    Fetch historical prices for a coin and save them to a CSV file.

    Args:
        coin_id: User input — CoinGecko id or symbol (example: "bitcoin", "XRP", "btc").
        days:    How many days of history to download (default: 365).
        resolve: If True, convert symbols to CoinGecko ids. Set False when coin_id
                 already comes from get_top_100_coins().

    Returns:
        A pandas DataFrame with columns: date, price
    """
    # Step 1: Convert symbols like XRP/BTC into CoinGecko ids like ripple/bitcoin.
    if resolve:
        resolved_id = resolve_coin_id(coin_id)
        if not resolved_id:
            raise ValueError(f"Coin not found: '{coin_id}'")
    else:
        resolved_id = coin_id

    csv_path = RAW_DATA_DIR / f"{resolved_id}.csv"

    # If CSV already exists, load it and skip the CoinGecko API call (avoids 429 errors).
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        df["date"] = pd.to_datetime(df["date"])
        return df[["date", "price"]]

    # Step 2: Call CoinGecko market_chart endpoint through our helper function.
    response = get_historical_data(resolved_id, days=days)

    # Step 3: Extract the "prices" list from the API response.
    # Each item looks like: [timestamp_in_milliseconds, price_in_usd]
    prices = response.get("prices", [])
    if not prices:
        raise ValueError(f"No price data returned for coin_id='{resolved_id}'")

    # Step 4: Build a pandas DataFrame from timestamp + price pairs.
    df = pd.DataFrame(prices, columns=["timestamp_ms", "price"])

    # Step 5: Convert millisecond timestamps into readable dates.
    # Example output: "2024-06-17 12:00:00"
    df["date"] = pd.to_datetime(df["timestamp_ms"], unit="ms")

    # Step 6: Keep only the columns we need for forecasting.
    df = df[["date", "price"]]

    # Step 7: Create data/raw/ folder if it does not exist yet.
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Step 8: Save CSV file (example: data/raw/ripple.csv).
    df.to_csv(csv_path, index=False)

    # Step 9: Return the dataframe so other code can use it immediately.
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
    # get_top_100_coins()
    top_coins = get_top_100_coins()
    total_coins = len(top_coins)
    collected_count = 0
    failed_coins = []

    # for coin in top100: collect_historical_data(coin_id)
    for index, coin in enumerate(top_coins, start=1):
        coin_id = coin["id"]
        coin_name = coin.get("name", coin_id)
        csv_path = RAW_DATA_DIR / f"{coin_id}.csv"

        # Skip CoinGecko if we already have this coin's CSV file.
        if csv_path.exists():
            print(f"Skipping {coin_id} (already exists)")
            collected_count += 1
            continue

        print(f"Collecting {coin_id} {index}/{total_coins}")

        try:
            # coin_id is already a CoinGecko id from the top 100 list — no symbol resolution needed.
            collect_historical_data(coin_id, days=days, resolve=False)
            collected_count += 1
        except Exception as exc:
            # Keep going even if one coin fails (rate limit, network, missing data).
            failed_coins.append(coin_id)
            print(f"Failed to collect {coin_name}: {exc}")
            continue

        # Wait 5 seconds after a new API call to avoid CoinGecko 429 rate limit errors.
        if index < total_coins:
            time.sleep(5)

    return {
        "coins_collected": collected_count,
        "failed_coins": failed_coins,
    }
