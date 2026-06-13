from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests
from bs4 import BeautifulSoup

from .utils import root_path


class ForexFactoryScraper:
    """Best-effort ForexFactory calendar scraper.

    ForexFactory can change its HTML or block requests. The bias engine is designed
    to continue without news if scraping fails.
    """

    BASE = "https://www.forexfactory.com/calendar"

    def __init__(self, cache_folder: str = "data/news_cache") -> None:
        self.cache_folder = root_path(cache_folder)
        self.cache_folder.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, start: date, end: date) -> Path:
        return self.cache_folder / f"forexfactory_red_{start}_{end}.csv"

    def load_cache(self, start: date, end: date) -> pd.DataFrame | None:
        path = self._cache_path(start, end)
        if path.exists():
            return pd.read_csv(path)
        return None

    def scrape(self, start: date, end: date, use_cache: bool = True) -> tuple[pd.DataFrame, str]:
        if use_cache:
            cached = self.load_cache(start, end)
            if cached is not None:
                return cached, "cache"

        rows: list[dict] = []
        try:
            # ForexFactory commonly uses week-based calendar pages.
            current = start - timedelta(days=start.weekday())
            while current <= end:
                url = f"{self.BASE}?week={current.strftime('%b%d.%Y').lower()}"
                html = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"}).text
                soup = BeautifulSoup(html, "lxml")

                for tr in soup.select("tr.calendar__row"):
                    currency = (tr.select_one("td.calendar__currency") or {}).get_text(" ", strip=True) if tr.select_one("td.calendar__currency") else ""
                    impact_span = tr.select_one("td.calendar__impact span")
                    impact_title = impact_span.get("title", "") if impact_span else ""
                    title = tr.select_one("td.calendar__event")
                    event_title = title.get_text(" ", strip=True) if title else ""
                    date_cell = tr.select_one("td.calendar__date")
                    time_cell = tr.select_one("td.calendar__time")
                    raw_date = date_cell.get_text(" ", strip=True) if date_cell else ""
                    raw_time = time_cell.get_text(" ", strip=True) if time_cell else ""

                    if "High" not in impact_title:
                        continue

                    rows.append({
                        "Date": current.isoformat(),
                        "Currency": currency,
                        "Impact": "High",
                        "Title": event_title,
                        "RawDate": raw_date,
                        "RawTime": raw_time,
                        "SourceWeek": current.isoformat(),
                    })
                current += timedelta(days=7)

            df = pd.DataFrame(rows)
            if not df.empty:
                df.to_csv(self._cache_path(start, end), index=False)
            return df, "scraped"
        except Exception as e:
            print(f"ForexFactory scrape failed: {e}")
            return pd.DataFrame(columns=["Date", "Currency", "Impact", "Title"]), "failed"


def currency_filter_for_symbol(symbol: str) -> set[str]:
    s = symbol.upper().replace(".", "").replace("#", "")
    currencies = {"USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF"}
    found = {c for c in currencies if c in s}
    if "XAU" in s or "XAG" in s or s in {"US30", "NAS100", "SPX500"}:
        found.add("USD")
    return found


def filter_news_for_symbol(news_df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if news_df is None or news_df.empty:
        return pd.DataFrame(columns=["Date", "Currency", "Impact", "Title"])
    currencies = currency_filter_for_symbol(symbol)
    if not currencies:
        return news_df.iloc[0:0].copy()
    return news_df[news_df["Currency"].astype(str).str.upper().isin(currencies)].copy()
