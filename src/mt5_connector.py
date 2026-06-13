from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import pandas as pd

try:
    import MetaTrader5 as mt5
except Exception:  # pragma: no cover
    mt5 = None


class MT5Connector:
    def __init__(self) -> None:
        self.connected = False

    def connect(self) -> bool:
        if mt5 is None:
            return False
        if mt5.initialize():
            self.connected = True
            return True
        self.connected = False
        return False

    def shutdown(self) -> None:
        if mt5 is not None and self.connected:
            mt5.shutdown()
            self.connected = False

    @staticmethod
    def _timeframe(tf: str):
        if mt5 is None:
            return None
        tf = tf.upper()
        if tf == "D1":
            return mt5.TIMEFRAME_D1
        if tf == "W1":
            return mt5.TIMEFRAME_W1
        raise ValueError(f"Unsupported timeframe: {tf}")

    def fetch_rates(self, symbol: str, timeframe: str, bars: int) -> pd.DataFrame:
        if mt5 is None or not self.connected:
            raise RuntimeError("MT5 is not connected. Open MT5 desktop and log in, or use CSV fallback.")

        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"MT5 symbol not found or not selectable: {symbol}")

        rates = mt5.copy_rates_from_pos(symbol, self._timeframe(timeframe), 0, bars)
        if rates is None or len(rates) == 0:
            raise RuntimeError(f"No MT5 rates returned for {symbol} {timeframe}")

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True).dt.tz_convert(None)
        df = df.rename(columns={"time": "Date", "open": "Open", "high": "High", "low": "Low", "close": "Close"})
        keep = ["Date", "Open", "High", "Low", "Close"]
        return df[keep].sort_values("Date").reset_index(drop=True)
