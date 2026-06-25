"""
Simple FastAPI backend for a college crypto forecasting project.

Run with:
    uvicorn main:app --reload
"""

import requests
from datetime import UTC, datetime
from fastapi import FastAPI, HTTPException

from coingecko import (
    format_historical_prices,
    get_coin_details,
    get_current_price,
    get_historical_data,
    get_top_100_coins,
    get_top_coins,
)
from collector import collect_historical_data, collect_top_100_data

# Create FastAPI app instance.
app = FastAPI(title="Crypto Forecasting API", version="1.0.0")


# Root route to confirm API is running.
@app.get("/")
def read_root():
    return {"message": "Crypto Forecasting API is running"}


# Return top coins from CoinGecko.
@app.get("/coins")
def read_coins(limit: int = 10):
    if limit < 1 or limit > 250:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 250")
    try:
        return get_top_coins(limit)
    except requests.exceptions.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"CoinGecko HTTP error: {exc}") from exc
    except requests.exceptions.RequestException as exc:
        raise HTTPException(status_code=503, detail=f"Network error: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


# Return the current top 100 cryptocurrencies by market cap.
# Results are cached in memory for 5 minutes (see coingecko.get_top_100_coins).
@app.get("/top100")
def read_top_100_coins():
    try:
        return get_top_100_coins()
    except requests.exceptions.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"CoinGecko HTTP error: {exc}") from exc
    except requests.exceptions.RequestException as exc:
        raise HTTPException(status_code=503, detail=f"Network error: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


# Return details of one coin by id (example: bitcoin).
@app.get("/coin/{coin_id}")
def read_coin_details(coin_id: str):
    try:
        data = get_coin_details(coin_id)
        if not data or data.get("id") is None:
            raise HTTPException(status_code=404, detail="Coin not found")
        return data
    except HTTPException:
        raise
    except requests.exceptions.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Coin not found") from exc
        raise HTTPException(status_code=502, detail=f"CoinGecko HTTP error: {exc}") from exc
    except requests.exceptions.RequestException as exc:
        raise HTTPException(status_code=503, detail=f"Network error: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


# Return current USD price of one coin.
@app.get("/coin/{coin_id}/price")
def read_coin_price(coin_id: str):
    try:
        data = get_current_price(coin_id)
        if coin_id not in data:
            raise HTTPException(status_code=404, detail="Coin price not found")
        return data
    except HTTPException:
        raise
    except requests.exceptions.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"CoinGecko HTTP error: {exc}") from exc
    except requests.exceptions.RequestException as exc:
        raise HTTPException(status_code=503, detail=f"Network error: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


# Return live price in a simple format for dashboards and frontend charts.
@app.get("/coin/{coin_id}/live")
def read_coin_live_price(coin_id: str):
    try:
        # Use existing CoinGecko helper to fetch the latest USD price.
        data = get_current_price(coin_id)
        if coin_id not in data:
            raise HTTPException(status_code=404, detail="Coin price not found")

        return {
            "coin": coin_id,
            "price": round(data[coin_id]["usd"]),
            "currency": "usd",
            "timestamp": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
        }
    except HTTPException:
        raise
    except requests.exceptions.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"CoinGecko HTTP error: {exc}") from exc
    except requests.exceptions.RequestException as exc:
        raise HTTPException(status_code=503, detail=f"Network error: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


# Return historical price data in a clean date + price format.
@app.get("/coin/{coin_id}/history")
def read_coin_history(coin_id: str, days: int = 30):
    if days < 1:
        raise HTTPException(status_code=400, detail="days must be greater than 0")
    try:
        # Fetch raw CoinGecko data, then convert it to simple JSON for the frontend/ML team.
        raw_data = get_historical_data(coin_id, days)
        clean_history = format_historical_prices(raw_data)

        if not clean_history:
            raise HTTPException(status_code=404, detail="Historical data not found")

        return clean_history
    except HTTPException:
        raise
    except requests.exceptions.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"CoinGecko HTTP error: {exc}") from exc
    except requests.exceptions.RequestException as exc:
        raise HTTPException(status_code=503, detail=f"Network error: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


# Download historical data for all top 100 coins and save CSV files.
@app.get("/collect/top100")
def collect_top_100_coin_data(days: int = 365):
    """
    Collect historical price data for the top 100 cryptocurrencies.

    Example: GET /collect/top100
    Saves files like: data/raw/bitcoin.csv, data/raw/ethereum.csv
    """
    if days < 1:
        raise HTTPException(status_code=400, detail="days must be greater than 0")

    try:
        result = collect_top_100_data(days=days)

        if result["coins_collected"] == 0:
            raise HTTPException(status_code=500, detail="No coin datasets were collected")

        return {
            "message": "Top 100 crypto datasets collected",
            "coins_collected": result["coins_collected"],
            "failed_coins": result["failed_coins"],
        }
    except HTTPException:
        raise
    except requests.exceptions.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"CoinGecko HTTP error: {exc}") from exc
    except requests.exceptions.RequestException as exc:
        raise HTTPException(status_code=503, detail=f"Network error: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


# Download historical prices and save them to data/raw/{coin_id}.csv
@app.get("/collect/{coin_id}")
def collect_coin_data(coin_id: str, days: int = 365):
    """
    Collect historical price data for a coin and save it as a CSV file.

    Example: GET /collect/bitcoin
    Saves to: data/raw/bitcoin.csv
    """
    if days < 1:
        raise HTTPException(status_code=400, detail="days must be greater than 0")

    try:
        # Fetches from CoinGecko, builds a DataFrame, and saves the CSV file.
        collect_historical_data(coin_id, days=days)
        return {"message": f"{coin_id} historical data collected successfully"}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except requests.exceptions.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Coin not found") from exc
        raise HTTPException(status_code=502, detail=f"CoinGecko HTTP error: {exc}") from exc
    except requests.exceptions.RequestException as exc:
        raise HTTPException(status_code=503, detail=f"Network error: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc
