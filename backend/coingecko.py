"""
Simple helper functions for CoinGecko API calls.

This file keeps all external API calls in one place so `main.py`
stays clean and easy to understand.
"""

from datetime import UTC, datetime

import requests

# CoinGecko base API URL.
BASE_URL = "https://api.coingecko.com/api/v3"

# Fields we keep when returning top 100 coin market data.
TOP_100_FIELDS = (
    "id",
    "symbol",
    "name",
    "image",
    "current_price",
    "market_cap",
    "market_cap_rank",
    "price_change_percentage_24h",
)

# Simple in-memory cache for top 100 results (used by GET /top100).
_top_100_cache = None
_top_100_cache_time = None
TOP_100_CACHE_MINUTES = 5


def get_top_coins(limit: int = 10) -> list[dict]:
    """Return top coins by market cap."""
    response = requests.get(
        f"{BASE_URL}/coins/markets",
        params={
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": limit,
            "page": 1,
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def get_top_100_coins() -> list[dict]:
    """
    Return the top 100 cryptocurrencies ranked by market cap.

    Uses CoinGecko /coins/markets and keeps only the fields needed
    for dynamic coin selection in the forecasting project.

    Results are cached in memory for 5 minutes to avoid repeated API calls.
    """
    global _top_100_cache, _top_100_cache_time

    now = datetime.now(UTC)

    # If we already fetched top 100 recently, return the saved result.
    if _top_100_cache is not None and _top_100_cache_time is not None:
        minutes_old = (now - _top_100_cache_time).total_seconds() / 60
        if minutes_old < TOP_100_CACHE_MINUTES:
            return _top_100_cache

    response = requests.get(
        f"{BASE_URL}/coins/markets",
        params={
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 100,
            "page": 1,
        },
        timeout=20,
    )
    response.raise_for_status()
    coins = response.json()

    # Remove extra CoinGecko fields and return a clean list for the API.
    result = [{field: coin.get(field) for field in TOP_100_FIELDS} for coin in coins]

    # Save result in memory so the next request can use it without calling CoinGecko.
    _top_100_cache = result
    _top_100_cache_time = now

    return result


def get_coin_details(coin_id: str) -> dict:
    """Return details for a specific coin id (example: 'bitcoin')."""
    response = requests.get(
        f"{BASE_URL}/coins/{coin_id}",
        params={
            "localization": "false",
            "tickers": "false",
            "market_data": "true",
            "community_data": "false",
            "developer_data": "false",
            "sparkline": "false",
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def get_current_price(coin_id: str) -> dict:
    """Return current USD price for a specific coin."""
    response = requests.get(
        f"{BASE_URL}/simple/price",
        params={"ids": coin_id, "vs_currencies": "usd"},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def get_historical_data(coin_id: str, days: int = 30) -> dict:
    """Return historical market chart data for the given number of days."""
    response = requests.get(
        f"{BASE_URL}/coins/{coin_id}/market_chart",
        params={"vs_currency": "usd", "days": days},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def format_historical_prices(raw_data: dict) -> list[dict]:
    """
    Convert raw CoinGecko history into a simple list of date + price objects.

    CoinGecko returns extra fields (market_caps, total_volumes) and timestamps
    in milliseconds. This function keeps only what our API needs.
    """
    prices = raw_data.get("prices", [])
    daily_prices: dict[str, int] = {}

    for timestamp_ms, price in prices:
        # Convert milliseconds to a readable date like "2026-06-01".
        date_str = datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC).strftime("%Y-%m-%d")
        # If multiple prices exist on the same day, keep the latest one.
        daily_prices[date_str] = round(price)

    # Return sorted list so dates appear in order.
    return [{"date": date, "price": daily_prices[date]} for date in sorted(daily_prices)]
