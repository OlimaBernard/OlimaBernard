# Day / Week Candlestick Bias Engine

Python-based portfolio bias engine for forecasting the next closed Daily and Weekly directional delivery as Bullish, Bearish, or Neutral.

## What Version 1 Includes

- MT5 API candle download as primary data source
- CSV fallback if MT5 is unavailable
- Separate Daily and Weekly models
- Hybrid candle labels using body %, CLV, and candle direction
- Multi-lookback OHLC-derived candle features: 3, 5, 10, 20
- ForexFactory red-folder news scraper for forex/metals/indices
- No news or seasonality for Deriv synthetic indices
- Ensemble model:
  - Logistic Regression
  - Random Forest
  - XGBoost if installed, otherwise LightGBM if installed
- Performance-based ensemble weighting
- Model versioning and registry
- Manual retraining with retrain alerts
- Console report
- Excel report
- Forecast history log
- Daily/Weekly alignment score

## Requirements

Install dependencies:

```bash
pip install -r requirements.txt
```

Optional stronger models:

```bash
pip install -r requirements-optional.txt
```

MT5 requirement:

- MetaTrader 5 Desktop must be installed
- MT5 must be open and logged in
- Symbols in `config/symbols.yaml` must match your broker's exact symbol names

## Configure Symbols

Edit:

```text
config/symbols.yaml
```

Example:

```yaml
metals:
  - XAUUSD

synthetics:
  - Volatility 75 Index
```

## Train Models

Train all configured instruments:

```bash
python retrain.py
```

Train one symbol:

```bash
python retrain.py --symbol XAUUSD
```

Saved models go to:

```text
models/
```

The active model registry is:

```text
models/model_registry.json
```

## Generate Forecasts

Run portfolio scan:

```bash
python main.py
```

Outputs:

```text
reports/bias_forecast_report.xlsx
reports/forecast_history.xlsx
```

## CSV Fallback

If MT5 is unavailable, place CSV files here:

```text
data/csv_fallback/
```

Naming convention:

```text
XAUUSD_D1.csv
XAUUSD_W1.csv
Volatility75Index_D1.csv
Volatility75Index_W1.csv
```

Required columns:

```text
Date, Open, High, Low, Close
```

## Bias Label Rules

Bullish:

```text
Close > Open
CLV >= 0.60
Body% >= 0.20
```

Bearish:

```text
Close < Open
CLV <= 0.40
Body% >= 0.20
```

Neutral:

```text
Everything else
```

## Confidence Rules

```text
<60%   = Neutral / No Clear Bias
60-69% = Medium Conviction
70-79% = High Conviction
80%+   = Very High Conviction
```

## Important Note

This tool is an analytical aid, not a guarantee. It should be used as part of your broader market analysis and risk-management framework.
