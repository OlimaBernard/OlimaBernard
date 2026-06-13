from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import pandas as pd

from .label_generator import add_labels
from .utils import root_path


def append_forecasts(forecasts: list, settings: dict) -> Path:
    path = root_path(settings.get("reports", {}).get("forecast_log", "reports/forecast_history.xlsx"))
    rows = [asdict(f) for f in forecasts]
    new_df = pd.DataFrame(rows)
    if path.exists():
        try:
            old = pd.read_excel(path, sheet_name="Forecast History")
            new_df = pd.concat([old, new_df], ignore_index=True)
        except Exception:
            pass
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        new_df.drop_duplicates(subset=["symbol", "model_type", "forecast_date", "model_version"], keep="last").to_excel(writer, sheet_name="Forecast History", index=False)
    return path


def evaluate_latest_forecasts(history_path: Path, latest_ohlc_by_key: dict, settings: dict) -> pd.DataFrame:
    # Placeholder hook for the next operational step: after enough candles close,
    # match logged predictions to actual next candle labels.
    if not history_path.exists():
        return pd.DataFrame()
    return pd.read_excel(history_path, sheet_name="Forecast History")
