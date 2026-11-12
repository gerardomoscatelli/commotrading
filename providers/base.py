"""Abstract price-provider interface. Every market-data vendor is one adapter implementing this class.

Conventions (all adapters):
- Symbols are canonical internal ids (see providers/symbols.py), never vendor codes:
    futures contract  ROOT+MONTH+YY   e.g. ZSF27, BZF27, 6EZ26, TTFF27
    continuous front  ROOT+"1!"       e.g. ZS1!, GC1!, SI1!, CPO1!
    other instruments                 e.g. DXY, US10Y, SPX, NDX, VIX, BTCUSD, EURUSD, XAGUSD
  The adapter translates with symbols.to_vendor(sym, self.name).
- History is a pandas DataFrame with columns Open, High, Low, Close, Volume and a DatetimeIndex
  (exchange-local tz-aware for intraday; daily bars may be tz-aware or naive, one row per session).
  An empty DataFrame means "no data"; raise NotSupported when the vendor cannot serve the request at all.
- `start` may be a date/datetime, or a lookback string: '5d', '7d', '1mo', '6mo', '1y', '2y', 'max', '60d', '730d'.
- `src`: 'contract' = the contract itself; 'cont' = continuous front month of the same root.
- Quotes are plain dicts: last, prev (previous settle/close), open, high, low, volume, oi, time (unix s), expiry (YYYY-MM-DD).
  Missing fields are None or absent.
"""
from abc import ABC, abstractmethod
import pandas as pd
from . import symbols as SY, contracts as CT

COLS = ["Open", "High", "Low", "Close", "Volume"]
TFS = ("15m", "60m", "1d", "1wk", "1mo")

class NotSupported(Exception):
    """The adapter cannot serve this symbol / request (lets the chain try the next provider)."""

def empty_frame():
    return pd.DataFrame(columns=COLS)

class PriceProvider(ABC):
    name = "base"           # registry key, also the vendor key in symbols.VENDOR
    label = "Market data"   # human label used in data 'source' strings

    def supports(self, sym, what="history"):
        """True if this adapter can serve `what` ('history','intraday','quote','info') for canonical `sym`."""
        return SY.to_vendor(sym, self.name) is not None

    def resolve(self, sym, src="contract"):
        """Apply src: 'cont' maps a contract to the continuous front month of its root."""
        p = SY.parse(sym)
        return SY.cont_id(p["root"]) if src == "cont" and p["kind"] == "contract" else sym

    # ---- required -------------------------------------------------------------------------
    @abstractmethod
    def get_history(self, sym, tf="1d", start=None, end=None, src="contract"):
        """OHLCV bars. tf in TFS. start=None means the longest series the vendor has."""

    @abstractmethod
    def get_quote(self, sym):
        """Latest quote dict (see module doc)."""

    # ---- optional, with sensible defaults --------------------------------------------------
    def get_intraday(self, sym, tf="15m", start=None, end=None, src="contract"):
        """Intraday bars (15m / 60m). Default: get_history with an intraday tf."""
        return self.get_history(sym, tf, start, end, src)

    def get_contract_info(self, sym):
        """Static contract facts: name, exchange, unit, currency, decimals, contract, month, expiry (+ expiry_est)."""
        info = SY.static_info(sym)
        p = SY.parse(sym)
        if p["kind"] == "contract":
            vend = None
            try: vend = (self.get_quote(sym) or {}).get("expiry")
            except Exception: pass
            if vend: info.update(expiry=vend, expiry_est=False)
            else:
                e = CT.est_expiry(p["root"], p["year"], p["month"])
                if e: info.update(expiry=str(e), expiry_est=True)
        return info

    def get_volume_oi(self, sym):
        """Session volume and open interest."""
        q = self.get_quote(sym) or {}
        return {"volume": q.get("volume"), "oi": q.get("oi")}

    def get_history_batch(self, syms, tf="1d", start=None, end=None):
        """{sym: DataFrame} for many symbols at once. Default loops get_history; vendors with bulk endpoints override."""
        out = {}
        for s in syms:
            try: out[s] = self.get_history(s, tf, start, end)
            except Exception: out[s] = empty_frame()
        return out
