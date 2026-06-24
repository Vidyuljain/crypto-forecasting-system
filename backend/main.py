"""
Simple FastAPI backend for a college crypto forecasting project.

Run with:
    uvicorn main:app --reload
"""

import requests
from fastapi import FastAPI, HTTPException

from coingecko import (
    get_coin_details,
    get_current_price,
    get_historical_data,
    get_top_coins,
)
from collector import collect_historical_data

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


# Return historical market data for one coin.
@app.get("/coin/{coin_id}/history")
def read_coin_history(coin_id: str, days: int = 30):
    if days < 1:
        raise HTTPException(status_code=400, detail="days must be greater than 0")
    try:
        data = get_historical_data(coin_id, days)
        if not data or "prices" not in data:
            raise HTTPException(status_code=404, detail="Historical data not found")
        return data
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
