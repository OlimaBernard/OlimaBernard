from __future__ import annotations

from datetime import datetime

import pandas as pd

from .model_trainer import load_active_model
from .utils import timeframe_name


def retrain_alert(symbol: str, timeframe: str, ohlc: pd.DataFrame, settings: dict) -> dict:
    package = load_active_model(symbol, timeframe, settings)
    tf_name = timeframe_name(timeframe)
    threshold = settings.get("retrain_alert", {}).get("daily_new_candles" if tf_name == "daily" else "weekly_new_candles", 50)
    if package is None:
        return {"Symbol": symbol, "Model": tf_name, "New Candles": None, "Retrain Alert": "YES", "Reason": "No active model"}
    last_train = pd.to_datetime(package.metadata.get("last_training_candle"), errors="coerce")
    new_count = int((pd.to_datetime(ohlc["Date"]) > last_train).sum()) if pd.notna(last_train) else None
    alert = new_count is None or new_count >= int(threshold)
    return {
        "Symbol": symbol,
        "Model": tf_name,
        "New Candles": new_count,
        "Retrain Alert": "YES" if alert else "NO",
        "Reason": f"Threshold={threshold}",
    }
