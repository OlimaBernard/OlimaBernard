from __future__ import annotations

import numpy as np
import pandas as pd

from .label_generator import add_labels


def _streak(labels: pd.Series, value: str) -> int:
    count = 0
    for item in reversed(labels.tolist()):
        if item == value:
            count += 1
        else:
            break
    return count


def week_of_month(dt: pd.Timestamp) -> int:
    return int((dt.day - 1) // 7 + 1)


def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    d = pd.to_datetime(out["Date"])
    out["day_of_week"] = d.dt.dayofweek
    out["week_of_month"] = d.apply(week_of_month)
    out["month"] = d.dt.month
    out["quarter"] = d.dt.quarter
    out["is_month_end"] = d.dt.is_month_end.astype(int)
    out["is_quarter_end"] = d.dt.is_quarter_end.astype(int)
    return out


def add_news_features(df: pd.DataFrame, news_df: pd.DataFrame | None) -> pd.DataFrame:
    out = df.copy()
    out["red_news_count"] = 0
    out["nfp_flag"] = 0
    out["cpi_flag"] = 0
    out["fomc_flag"] = 0
    out["central_bank_flag"] = 0
    if news_df is None or news_df.empty:
        return out

    news = news_df.copy()
    news["Date"] = pd.to_datetime(news["Date"], errors="coerce").dt.date
    out_dates = pd.to_datetime(out["Date"]).dt.date
    for i, day in enumerate(out_dates):
        subset = news[news["Date"] == day]
        if subset.empty:
            continue
        titles = subset.get("Title", pd.Series(dtype=str)).astype(str).str.lower()
        out.loc[out.index[i], "red_news_count"] = len(subset)
        out.loc[out.index[i], "nfp_flag"] = titles.str.contains("non-farm|nonfarm|nfp").any().astype(int) if hasattr(titles.str.contains("nfp").any(), 'astype') else int(titles.str.contains("non-farm|nonfarm|nfp").any())
        out.loc[out.index[i], "cpi_flag"] = int(titles.str.contains("cpi|consumer price").any())
        out.loc[out.index[i], "fomc_flag"] = int(titles.str.contains("fomc|federal funds|fed interest").any())
        out.loc[out.index[i], "central_bank_flag"] = int(titles.str.contains("rate statement|interest rate|monetary policy|central bank").any())
    return out


def build_features(
    df: pd.DataFrame,
    settings: dict,
    include_calendar: bool,
    include_news: bool,
    news_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    out = add_labels(df, settings)
    lookbacks = settings.get("lookbacks", [3, 5, 10, 20])

    for lb in lookbacks:
        out[f"bullish_ratio_{lb}"] = out["label"].eq("Bullish").rolling(lb).mean()
        out[f"bearish_ratio_{lb}"] = out["label"].eq("Bearish").rolling(lb).mean()
        out[f"neutral_ratio_{lb}"] = out["label"].eq("Neutral").rolling(lb).mean()
        out[f"avg_body_{lb}"] = out["body"].rolling(lb).mean()
        out[f"avg_range_{lb}"] = out["range"].rolling(lb).mean()
        out[f"max_range_{lb}"] = out["range"].rolling(lb).max()
        out[f"min_range_{lb}"] = out["range"].rolling(lb).min()
        out[f"range_expansion_{lb}"] = out["range"] / out[f"avg_range_{lb}"].replace(0, np.nan)
        out[f"avg_clv_{lb}"] = out["clv"].rolling(lb).mean()
        out[f"bullish_streak_{lb}"] = out["label"].rolling(lb).apply(lambda x: _streak(pd.Series(x).map({0:"Bearish",1:"Bullish",2:"Neutral"}), "Bullish"), raw=False) if False else 0
        out[f"bearish_streak_{lb}"] = 0

        bull_streaks, bear_streaks = [], []
        for idx in range(len(out)):
            labels = out["label"].iloc[max(0, idx-lb+1):idx+1]
            bull_streaks.append(_streak(labels, "Bullish"))
            bear_streaks.append(_streak(labels, "Bearish"))
        out[f"bullish_streak_{lb}"] = bull_streaks
        out[f"bearish_streak_{lb}"] = bear_streaks

    if include_calendar:
        out = add_calendar_features(out)

    if include_news:
        out = add_news_features(out, news_df)

    out = out.replace([np.inf, -np.inf], np.nan)
    return out


def feature_columns(df: pd.DataFrame) -> list[str]:
    exclude = {"Date", "Open", "High", "Low", "Close", "label", "target"}
    return [c for c in df.columns if c not in exclude and pd.api.types.is_numeric_dtype(df[c])]
