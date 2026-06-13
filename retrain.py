from __future__ import annotations

import argparse
from datetime import date, timedelta

from src.data_loader import load_ohlc
from src.feature_engineering import build_features
from src.model_trainer import save_model, train_ensemble
from src.mt5_connector import MT5Connector
from src.news_scraper import ForexFactoryScraper, filter_news_for_symbol
from src.utils import ensure_dirs, flatten_symbols, is_synthetic, load_settings, load_symbols


def parse_args():
    p = argparse.ArgumentParser(description="Retrain Bias Engine models manually.")
    p.add_argument("--symbol", default=None, help="Optional single symbol to retrain, e.g. XAUUSD")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    ensure_dirs()
    settings = load_settings()
    symbols = flatten_symbols(load_symbols())
    if args.symbol:
        symbols = [s for s in symbols if s["symbol"].upper() == args.symbol.upper()]
        if not symbols:
            raise SystemExit(f"Symbol not found in config: {args.symbol}")

    mt5 = MT5Connector()
    connected = mt5.connect()
    print(f"MT5 connection: {'OK' if connected else 'FAILED - CSV fallback will be used if available'}")

    news_df = None
    news_status = "not_required"
    if settings.get("news", {}).get("use_forexfactory", True) and any(not is_synthetic(s["group"]) for s in symbols):
        start = date.today() - timedelta(days=365 * 10)
        end = date.today() + timedelta(days=14)
        scraper = ForexFactoryScraper(settings.get("news", {}).get("cache_folder", "data/news_cache"))
        news_df, news_status = scraper.scrape(start, end, use_cache=True)
        print(f"ForexFactory news status: {news_status}; rows={len(news_df)}")

    for item in symbols:
        symbol, group = item["symbol"], item["group"]
        synthetic = is_synthetic(group)
        for timeframe, bars in [("D1", int(settings.get("history", {}).get("daily_bars", 2500))), ("W1", int(settings.get("history", {}).get("weekly_bars", 700)))]:
            try:
                print(f"\nTraining {symbol} {timeframe}...")
                ohlc, source = load_ohlc(symbol, timeframe, bars, settings, mt5)
                include_calendar = not synthetic
                include_news = not synthetic and settings.get("news", {}).get("use_forexfactory", True)
                sym_news = filter_news_for_symbol(news_df, symbol) if include_news else None
                features = build_features(ohlc, settings, include_calendar=include_calendar, include_news=include_news, news_df=sym_news)
                package = train_ensemble(features, symbol, timeframe, group, settings)
                path = save_model(package, settings)
                print(f"Saved: {path.name}")
                print(f"Approved: {package.approved}")
                print(f"Validation accuracy: {package.validation.get('ensemble_accuracy'):.2%}")
                print(f"Weights: {package.weights}")
            except Exception as e:
                print(f"FAILED {symbol} {timeframe}: {e}")

    mt5.shutdown()


if __name__ == "__main__":
    main()
