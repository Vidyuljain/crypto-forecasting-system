"""
train_all.py — Train ML models for every coin with CSV data in data/raw/.

Reads coin ids from CSV filenames and calls train_models() for each one.
Each coin is trained directly from its CSV file (no backend API needed).
"""

from pathlib import Path

from train import train_models

# Folder where collected coin CSV files are stored.
RAW_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def train_all_models() -> dict:
    """
    Train models for all coins that have a CSV file in data/raw/.

    Returns:
        Summary with trained count and failed coin ids.
    """
    csv_files = sorted(RAW_DATA_DIR.glob("*.csv"))
    total_coins = len(csv_files)
    trained_count = 0
    failed_coins = []

    for index, csv_file in enumerate(csv_files, start=1):
        # Get coin id from filename (example: bitcoin.csv -> bitcoin).
        coin_id = csv_file.stem

        print(f"Training {index}/{total_coins} {coin_id}")

        try:
            train_models(coin_id)
            trained_count += 1
        except Exception as exc:
            # Keep going even if one coin fails.
            failed_coins.append(coin_id)
            print(f"Failed to train {coin_id}: {exc}")
            continue

    print(f"Done: {trained_count}/{total_coins} models trained.")

    return {
        "trained": trained_count,
        "total": total_coins,
        "failed_coins": failed_coins,
    }


if __name__ == "__main__":
    train_all_models()
