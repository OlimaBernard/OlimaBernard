from __future__ import annotations

from datetime import date, timedelta
from dataclasses import asdict

from src.alignment import alignment_score
from src.data_loader import load_ohlc
from src.excel_reporter import write_report
from src.forecast_engine import generate_forecast
from src.mt5_connector import MT5Connector
from src.news_scraper import ForexFactoryScraper
from src.performance_tracker import append_forecasts
from src.retrain_alerts import retrain_alert
from src.utils import ensure_dirs, flatten_symbols, is_synthetic, load_settings, load_symbols


def print_portfolio(rows: list[dict]) -> None:
    print("=" * 70)
    print("BIAS ENGINE PORTFOLIO SCAN")
    print("=" * 70)
    for r in rows:
        print(f"\n{r['Symbol']}")
        print(f"Daily : {r['Daily Bias']} ({r['Daily Confidence']:.0%}) | {r['Daily Conviction']}")
        print(f"Weekly: {r['Weekly Bias']} ({r['Weekly Confidence']:.0%}) | {r['Weekly Conviction']}")
        print(f"Alignment: {r['Alignment']}")
        print(f"Top Driver: {r['Top Driver']}")
        print(f"Risk: {r['Risk Factors']}")
    print("\n" + "=" * 70)


def main() -> None:
    ensure_dirs()
    settings = load_settings()
    symbols = flatten_symbols(load_symbols())

    mt5 = MT5Connector()
    connected = mt5.connect()
    print(f"MT5 connection: {'OK' if connected else 'FAILED - CSV fallback will be used if available'}")

    # One broad news scrape for all non-synthetic symbols.
    news_df = None
    news_status = "not_required"
    if settings.get("news", {}).get("use_forexfactory", True) and any(not is_synthetic(s["group"]) for s in symbols):
        start = date.today() - timedelta(days=365 * 10)
        end = date.today() + timedelta(days=14)
        scraper = ForexFactoryScraper(settings.get("news", {}).get("cache_folder", "data/news_cache"))
        news_df, news_status = scraper.scrape(start, end, use_cache=True)
        print(f"ForexFactory news status: {news_status}; rows={len(news_df)}")

    forecasts = []
    portfolio_rows = []
    retrain_rows = []

    for item in symbols:
        symbol, group = item["symbol"], item["group"]
        daily_bars = int(settings.get("history", {}).get("daily_bars", 2500))
        weekly_bars = int(settings.get("history", {}).get("weekly_bars", 700))
        try:
            d1, dsrc = load_ohlc(symbol, "D1", daily_bars, settings, mt5)
            w1, wsrc = load_ohlc(symbol, "W1", weekly_bars, settings, mt5)
        except Exception as e:
            print(f"Skipping {symbol}: {e}")
            continue

        d_news_status = "not_required" if is_synthetic(group) else news_status
        w_news_status = "not_required" if is_synthetic(group) else news_status

        daily = generate_forecast(symbol, group, "D1", d1, settings, news_df, d_news_status, dsrc)
        weekly = generate_forecast(symbol, group, "W1", w1, settings, news_df, w_news_status, wsrc)
        forecasts.extend([daily, weekly])

        align = alignment_score(daily.bias, weekly.bias)
        portfolio_rows.append({
            "Symbol": symbol,
            "Group": group,
            "Daily Bias": daily.bias,
            "Daily Confidence": daily.confidence,
            "Daily Conviction": daily.conviction,
            "Weekly Bias": weekly.bias,
            "Weekly Confidence": weekly.confidence,
            "Weekly Conviction": weekly.conviction,
            "Alignment": align,
            "Top Driver": daily.top_drivers,
            "Risk Factors": daily.risk_factors,
        })
        retrain_rows.append(retrain_alert(symbol, "D1", d1, settings))
        retrain_rows.append(retrain_alert(symbol, "W1", w1, settings))

    print_portfolio(portfolio_rows)
    report = write_report(portfolio_rows, forecasts, retrain_rows, settings)
    log = append_forecasts(forecasts, settings)
    print(f"Excel report saved: {report}")
    print(f"Forecast history saved: {log}")
    mt5.shutdown()


if __name__ == "__main__":
    main()
