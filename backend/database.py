"""
database.py — Simple SQLite database helpers for the crypto project.

This file stores coin market data and historical prices in crypto.db.
Uses only the built-in sqlite3 module — no ORM, no classes.
"""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

# Database file lives next to this script: backend/crypto.db
DB_PATH = Path(__file__).resolve().parent / "crypto.db"


def get_connection() -> sqlite3.Connection:
    """Open a connection to the SQLite database."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row  # lets us read columns by name
    return connection


def initialize_database() -> None:
    """
    Create crypto.db and the coins / historical_prices tables if they do not exist.
    Call this once when the API starts.
    """
    connection = get_connection()
    cursor = connection.cursor()

    # Table for current coin market snapshots (from top 100 list, live prices, etc.)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS coins (
            id            TEXT PRIMARY KEY,
            symbol        TEXT NOT NULL,
            name          TEXT NOT NULL,
            current_price REAL,
            market_cap    REAL,
            volume        REAL,
            updated_at    TEXT NOT NULL
        )
    """)

    # Table for historical daily prices used by forecasting.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historical_prices (
            coin_id  TEXT NOT NULL,
            date     TEXT NOT NULL,
            price    REAL NOT NULL,
            PRIMARY KEY (coin_id, date)
        )
    """)

    connection.commit()
    connection.close()


def save_coin_data(
    coin_id: str,
    symbol: str,
    name: str,
    current_price: float,
    market_cap: float,
    volume: float,
) -> None:
    """
    Save or update one coin's market data in the coins table.

    If the coin already exists, its row is replaced with the new values.
    """
    updated_at = datetime.now(UTC).isoformat()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO coins
            (id, symbol, name, current_price, market_cap, volume, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (coin_id, symbol, name, current_price, market_cap, volume, updated_at),
    )

    connection.commit()
    connection.close()


def save_historical_data(coin_id: str, date: str, price: float) -> None:
    """
    Save one historical price row for a coin.

    Args:
        coin_id: CoinGecko id (example: "bitcoin").
        date:    Date string (example: "2026-06-01").
        price:   Price on that date.
    """
    connection = get_connection()
    cursor = connection.cursor()

    # INSERT OR REPLACE avoids duplicate rows for the same coin + date.
    cursor.execute(
        """
        INSERT OR REPLACE INTO historical_prices (coin_id, date, price)
        VALUES (?, ?, ?)
        """,
        (coin_id, date, price),
    )

    connection.commit()
    connection.close()


def get_coin_history(coin_id: str) -> list[dict]:
    """
    Load all saved historical prices for one coin from the database.

    Returns:
        List of dictionaries: [{"date": "...", "price": ...}, ...]
    """
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT date, price
        FROM historical_prices
        WHERE coin_id = ?
        ORDER BY date ASC
        """,
        (coin_id,),
    )

    rows = cursor.fetchall()
    connection.close()

    return [{"date": row["date"], "price": row["price"]} for row in rows]


def get_database_status() -> dict:
    """
    Check the database and return simple row counts.

    Used by GET /database/status to show how much data is stored.
    """
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM coins")
    coins_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM historical_prices")
    historical_count = cursor.fetchone()[0]

    connection.close()

    return {
        "database": "connected",
        "coins": coins_count,
        "historical_records": historical_count,
    }
