from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from .ensemble_engine import ensemble_predict_proba, final_bias_from_probs
from .feature_engineering import build_features
from .model_trainer import load_active_model
from .news_scraper import filter_news_for_symbol
from .utils import is_synthetic, timeframe_name


@dataclass
class ForecastResult:
    symbol: str
    group: str
    timeframe: str
    model_type: str
    forecast_date: str
    bias: str
    confidence: float
    conviction: str
    reliability: str
    approved: bool
    model_version: str
    sample_size: int
    top_drivers: str
    risk_factors: str
    news_status: str
    data_source: str
    validation_accuracy: float | None


def conviction(conf: float, min_conf: float) -> str:
    if conf < min_conf:
        return "Neutral / No Clear Bias"
    if conf < 0.70:
        return "Medium"
    if conf < 0.80:
        return "High"
    return "Very High"


def reliability(sample_size: int, approved: bool, news_status: str) -> str:
    if not approved:
        return "Low"
    if sample_size >= 1000:
        base = "High"
    elif sample_size >= 260:
        base = "Medium"
    else:
        base = "Low"
    if news_status == "failed" and base == "High":
        return "Medium"
    return base


def explain(features_latest: pd.Series, probs: pd.Series, include_news: bool) -> tuple[str, str]:
    drivers: list[str] = []
    risks: list[str] = []

    for lb in [3, 5, 10, 20]:
        br = features_latest.get(f"bullish_ratio_{lb}", np.nan)
        sr = features_latest.get(f"bearish_ratio_{lb}", np.nan)
        clv = features_latest.get(f"avg_clv_{lb}", np.nan)
        exp = features_latest.get(f"range_expansion_{lb}", np.nan)
        if pd.notna(br) and br >= 0.60:
            drivers.append(f"{lb}-candle bullish ratio elevated ({br:.0%})")
        if pd.notna(sr) and sr >= 0.60:
            drivers.append(f"{lb}-candle bearish ratio elevated ({sr:.0%})")
        if pd.notna(clv) and clv >= 0.60:
            drivers.append(f"{lb}-candle average CLV strong ({clv:.2f})")
        if pd.notna(clv) and clv <= 0.40:
            drivers.append(f"{lb}-candle average CLV weak ({clv:.2f})")
        if pd.notna(exp) and exp >= 1.20:
            drivers.append(f"Range expansion detected over {lb} candles ({exp:.2f}x)")

    if include_news:
        cnt = int(features_latest.get("red_news_count", 0) or 0)
        if cnt > 0:
            risks.append(f"{cnt} red-folder news event(s) in forecast context")
        for flag, name in [("nfp_flag", "NFP"), ("cpi_flag", "CPI"), ("fomc_flag", "FOMC"), ("central_bank_flag", "central bank event")]:
            if int(features_latest.get(flag, 0) or 0) == 1:
                risks.append(f"{name} risk present")

    if not drivers:
        sorted_probs = probs.sort_values(ascending=False)
        drivers.append(f"Ensemble probability highest for {sorted_probs.index[0]} ({sorted_probs.iloc[0]:.0%})")
    return " | ".join(drivers[:5]), " | ".join(risks[:5]) if risks else "None"


def generate_forecast(
    symbol: str,
    group: str,
    timeframe: str,
    ohlc: pd.DataFrame,
    settings: dict,
    news_df: pd.DataFrame | None,
    news_status: str,
    data_source: str,
) -> ForecastResult:
    package = load_active_model(symbol, timeframe, settings)
    tf_name = timeframe_name(timeframe)
    if package is None:
        return ForecastResult(
            symbol, group, timeframe, tf_name, str(ohlc["Date"].iloc[-1]), "No Model", 0.0,
            "Unavailable", "Low", False, "None", len(ohlc), "Train model first", "None", news_status, data_source, None
        )

    synthetic = is_synthetic(group)
    include_calendar = not synthetic
    include_news = (not synthetic) and settings.get("news", {}).get("use_forexfactory", True)
    symbol_news = filter_news_for_symbol(news_df, symbol) if include_news else None
    feats = build_features(ohlc, settings, include_calendar=include_calendar, include_news=include_news, news_df=symbol_news)
    latest = feats.iloc[[-1]].copy()
    latest[package.feature_cols] = latest.reindex(columns=package.feature_cols).fillna(0.0)
    probs_df = ensemble_predict_proba(package, latest)
    probs = probs_df.iloc[0]
    min_conf = float(settings.get("min_directional_confidence", 0.60))
    bias, conf = final_bias_from_probs(probs, min_conf)
    top, risk = explain(latest.iloc[0], probs, include_news)
    approved = bool(package.approved)
    version = package.metadata.get("version", "unknown")
    sample_size = int(package.metadata.get("rows", len(ohlc)))
    val_acc = package.validation.get("ensemble_accuracy") if package.validation else None

    return ForecastResult(
        symbol=symbol,
        group=group,
        timeframe=timeframe,
        model_type=tf_name,
        forecast_date=str(ohlc["Date"].iloc[-1]),
        bias=bias,
        confidence=conf,
        conviction=conviction(conf, min_conf),
        reliability=reliability(sample_size, approved, news_status),
        approved=approved,
        model_version=version,
        sample_size=sample_size,
        top_drivers=top,
        risk_factors=risk,
        news_status=news_status,
        data_source=data_source,
        validation_accuracy=val_acc,
    )
