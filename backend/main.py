"""
Simple FastAPI backend for a college crypto forecasting project.

Run with:
    uvicorn main:app --reload
"""

import json
import sys
from pathlib import Path

import pandas as pd
import requests
from datetime import UTC, datetime
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Add the ml folder to the import path so we can use the prediction pipeline.
ML_DIR = Path(__file__).resolve().parent.parent / "ml"
sys.path.insert(0, str(ML_DIR))

from predict import predict_future_prices

from coingecko import (
    get_coin_details,
    get_current_price,
    get_top_100_coins,
    get_top_coins,
    resolve_coin_id,
)
from collector import collect_historical_data, collect_top_100_data
import database

# Local CSV files collected by /collect/{coin_id} (avoids CoinGecko on history charts).
RAW_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

app = FastAPI(
    title="Crypto Forecasting API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables when the API starts.
database.initialize_database()


def get_resolved_coin_id(user_input: str) -> str:
    """Convert BTC/btc/bitcoin style input into a CoinGecko id, or raise 404."""
    coin_id = resolve_coin_id(user_input)
    if not coin_id:
        raise HTTPException(status_code=404, detail=f"Coin not found: '{user_input}'")
    return coin_id


# Root route to confirm API is running.
@app.get("/")
def read_root():
    return {"message": "Crypto Forecasting API is running"}


# Return database connection status and row counts.
@app.get("/database/status")
def read_database_status():
    try:
        return database.get_database_status()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc


# Return historical price data from SQLite for ML models.
@app.get("/ml/data/{coin_id}")
def read_ml_data(coin_id: str):
    """
    Load saved historical prices for a coin from the database.

    Example: GET /ml/data/bitcoin
    Used by the ML module — does not call CoinGecko.
    """
    try:
        history = database.get_coin_history(coin_id)

        if not history:
            raise HTTPException(
                status_code=404,
                detail=f"No historical data in database for '{coin_id}'. Run /collect/{coin_id} first.",
            )

        return history
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc


# Return ML price forecasts for a coin.
@app.get("/predict/{coin_id}")
def predict_coin_prices(coin_id: str, days: int = 7, model: str = "random_forest"):
    """
    Predict future prices using the trained ML model.

    Example: GET /predict/bitcoin?days=7&model=random_forest
    """
    if days < 1:
        raise HTTPException(status_code=400, detail="days must be greater than 0")

    if model not in {"linear_regression", "random_forest"}:
        raise HTTPException(status_code=400, detail="model must be linear_regression or random_forest")

    try:
        resolved_id = get_resolved_coin_id(coin_id)
        predictions = predict_future_prices(resolved_id, days=days, model=model)

        return {
            "coin": resolved_id,
            "model": model,
            "predictions": predictions,
        }
    except HTTPException:
        raise
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Model not trained for '{coin_id}'. Run ml/train.py first.",
        ) from exc
    except requests.exceptions.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"No historical data for '{coin_id}'. Run /collect/{coin_id} first.",
            ) from exc
        raise HTTPException(status_code=502, detail=f"Failed to load coin data: {exc}") from exc
    except requests.exceptions.RequestException as exc:
        raise HTTPException(status_code=503, detail=f"Network error: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Prediction error: {exc}") from exc


# Return ML training metrics for a coin (best model, RMSE, etc.).
@app.get("/metrics/{coin_id}")
def get_coin_metrics(coin_id: str):
    try:
        resolved_id = get_resolved_coin_id(coin_id)
        metrics_path = ML_DIR / "models" / resolved_id / "metrics.json"

        if not metrics_path.exists():
            raise HTTPException(status_code=404, detail=f"Metrics not found for '{coin_id}'")

        with open(metrics_path, encoding="utf-8") as file:
            return json.load(file)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Metrics error: {exc}") from exc


# Return top coins from CoinGecko and save them to the database.
@app.get("/coins")
def read_coins(limit: int = 10):
    if limit < 1 or limit > 250:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 250")
    try:
        coins = get_top_coins(limit)

        # Save each coin into the SQLite coins table.
        for coin in coins:
            database.save_coin_data(
                coin_id=coin["id"],
                symbol=coin.get("symbol", ""),
                name=coin.get("name", ""),
                current_price=coin.get("current_price") or 0,
                market_cap=coin.get("market_cap") or 0,
                volume=coin.get("total_volume") or 0,
            )

        return coins
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
        resolved_id = get_resolved_coin_id(coin_id)
        data = get_coin_details(resolved_id)
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
        resolved_id = get_resolved_coin_id(coin_id)
        data = get_current_price(resolved_id)
        if resolved_id not in data:
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
        resolved_id = get_resolved_coin_id(coin_id)

        # Use existing CoinGecko helper to fetch the latest USD price.
        data = get_current_price(resolved_id)
        if resolved_id not in data:
            raise HTTPException(status_code=404, detail="Coin price not found")

        return {
            "coin": resolved_id,
            "price": round(data[resolved_id]["usd"]),
            "currency": "usd",
            "timestamp": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
        }
    except HTTPException:
        raise
    except requests.exceptions.HTTPError as exc:
         print("HTTP ERROR:", repr(exc))
         raise HTTPException(status_code=502, detail=f"CoinGecko HTTP error: {exc}") from exc
    except requests.exceptions.RequestException as exc:
        print("NETWORK ERROR:", repr(exc))
        raise HTTPException(status_code=503, detail=f"Network error: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


# Return historical price data in a clean date + price format.
@app.get("/coin/{coin_id}/history")
def read_coin_history(coin_id: str, days: int = 30):
    if days < 1:
        raise HTTPException(status_code=400, detail="days must be greater than 0")
    try:
        resolved_id = get_resolved_coin_id(coin_id)

        # Use collected CSV data instead of CoinGecko to avoid rate limit 502 errors.
        csv_path = RAW_DATA_DIR / f"{resolved_id}.csv"
        if not csv_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Historical data not found for '{resolved_id}'. Run /collect/{resolved_id} first.",
            )

        df = pd.read_csv(csv_path)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        df = df.tail(days)

        if df.empty:
            raise HTTPException(status_code=404, detail="Historical data not found")

        return [
            {
                "date": row["date"].strftime("%Y-%m-%d"),
                "price": round(float(row["price"]), 2),
            }
            for _, row in df.iterrows()
        ]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


# Download historical data for all top 100 coins and save CSV files.
@app.get("/collect/top100")
def collect_top_100_coin_data(
    background_tasks: BackgroundTasks,
    start: int = 0,
    limit: int = 25,
    days: int = 365,
):
    """
    Start collecting historical price data for a batch of the top 100 cryptocurrencies.

    Examples:
    /collect/top100?start=0&limit=25
    /collect/top100?start=25&limit=25
    /collect/top100?start=50&limit=25
    /collect/top100?start=75&limit=25

    Collection runs in the background.
    """

    if days < 1:
        raise HTTPException(status_code=400, detail="days must be greater than 0")

    if start < 0:
        raise HTTPException(status_code=400, detail="start must be 0 or greater")

    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")

    background_tasks.add_task(
        collect_top_100_data,
        start,
        limit,
        days,
    )

    return {
        "message": "Top 100 collection started",
        "start": start,
        "limit": limit,
    }


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
        resolved_id = get_resolved_coin_id(coin_id)

        # Fetches from CoinGecko, builds a DataFrame, and saves the CSV file.
        df = collect_historical_data(
            resolved_id,
            days=days,
            resolve=False,
        )

        # Also save historical prices into the SQLite database.
        for _, row in df.iterrows():
            date_str = row["date"].strftime("%Y-%m-%d")
            database.save_historical_data(resolved_id, date_str, float(row["price"]))

        return {"message": f"{resolved_id} historical data collected successfully"}
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
