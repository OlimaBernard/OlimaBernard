from __future__ import annotations

import numpy as np
import pandas as pd


def add_candle_metrics(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    rng = (out["High"] - out["Low"]).replace(0, np.nan)
    out["range"] = out["High"] - out["Low"]
    out["body"] = (out["Close"] - out["Open"]).abs()
    out["upper_wick"] = out["High"] - out[["Open", "Close"]].max(axis=1)
    out["lower_wick"] = out[["Open", "Close"]].min(axis=1) - out["Low"]
    out["body_pct"] = out["body"] / rng
    out["clv"] = (out["Close"] - out["Low"]) / rng
    out[["body_pct", "clv"]] = out[["body_pct", "clv"]].fillna(0.0)
    return out


def candle_label(row: pd.Series, min_body_pct: float, bullish_clv: float, bearish_clv: float) -> str:
    if row["Close"] > row["Open"] and row["clv"] >= bullish_clv and row["body_pct"] >= min_body_pct:
        return "Bullish"
    if row["Close"] < row["Open"] and row["clv"] <= bearish_clv and row["body_pct"] >= min_body_pct:
        return "Bearish"
    return "Neutral"


def add_labels(df: pd.DataFrame, settings: dict) -> pd.DataFrame:
    cfg = settings.get("labeling", {})
    out = add_candle_metrics(df)
    out["label"] = out.apply(
        candle_label,
        axis=1,
        min_body_pct=float(cfg.get("min_body_pct", 0.20)),
        bullish_clv=float(cfg.get("bullish_clv", 0.60)),
        bearish_clv=float(cfg.get("bearish_clv", 0.40)),
    )
    out["target"] = out["label"].shift(-1)
    return out
