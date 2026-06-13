from __future__ import annotations

from pathlib import Path
import pandas as pd

from .mt5_connector import MT5Connector
from .utils import root_path, safe_symbol_name


REQUIRED_COLS = ["Date", "Open", "High", "Low", "Close"]


def normalize_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    mapping = {c.lower(): c for c in df.columns}
    ren = {}
    for target in REQUIRED_COLS:
        key = target.lower()
        if key in mapping:
            ren[mapping[key]] = target
    df = df.rename(columns=ren)
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"OHLC file missing required columns: {missing}")
    df = df[REQUIRED_COLS].copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    for col in ["Open", "High", "Low", "Close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna().sort_values("Date").drop_duplicates("Date").reset_index(drop=True)
    return df


def csv_path(symbol: str, timeframe: str, csv_folder: str) -> Path:
    return root_path(csv_folder, f"{safe_symbol_name(symbol)}_{timeframe.upper()}.csv")


def load_from_csv(symbol: str, timeframe: str, csv_folder: str) -> pd.DataFrame:
    path = csv_path(symbol, timeframe, csv_folder)
    if not path.exists():
        raise FileNotFoundError(f"CSV fallback not found: {path}")
    return normalize_ohlc(pd.read_csv(path))


def load_ohlc(symbol: str, timeframe: str, bars: int, settings: dict, mt5_conn: MT5Connector | None = None) -> tuple[pd.DataFrame, str]:
    csv_folder = settings.get("data", {}).get("csv_folder", "data/csv_fallback")
    use_mt5 = settings.get("data", {}).get("mt5_primary", True)
    use_csv = settings.get("data", {}).get("csv_fallback", True)

    if use_mt5 and mt5_conn is not None and mt5_conn.connected:
        try:
            return mt5_conn.fetch_rates(symbol, timeframe, bars), "MT5"
        except Exception as e:
            print(f"MT5 load failed for {symbol} {timeframe}: {e}")

    if use_csv:
        return load_from_csv(symbol, timeframe, csv_folder), "CSV"

    raise RuntimeError(f"No data source available for {symbol} {timeframe}")
