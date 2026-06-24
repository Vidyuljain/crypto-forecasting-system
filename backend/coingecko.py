"""
Simple helper functions for CoinGecko API calls.

This file keeps all external API calls in one place so `main.py`
stays clean and easy to understand.
"""

import requests

# CoinGecko base API URL.
BASE_URL = "https://api.coingecko.com/api/v3"


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
