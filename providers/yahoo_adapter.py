"""Default free feed adapter (Yahoo Finance via the yfinance package).
This is the ONLY module in the app that imports yfinance. The UI never names the vendor."""
import datetime as dt
import pandas as pd
from .base import PriceProvider, NotSupported, empty_frame
from . import symbols as SY

_INTERVAL = {"15m": "15m", "60m": "60m", "1d": "1d", "1wk": "1wk", "1mo": "1mo"}
_INTRADAY_DEFAULT = {"15m": "60d", "60m": "730d"}

def _is_lookback(x): return isinstance(x, str) and x not in ("",) and not x[:4].isdigit()

class YahooProvider(PriceProvider):
    name = "yahoo"
    label = "Yahoo Finance"

    def __init__(self):
        import yfinance  # noqa: F401  (fail fast if the package is missing)
        self._yf = yfinance

    def _code(self, sym):
        c = SY.to_vendor(sym, self.name)
        if not c: raise NotSupported(f"{self.name}: no code for {sym}")
        return c

    def _span(self, start, end):
        """yfinance kwargs for a lookback string or a start/end pair."""
        if start is None: return {"period": "max"}
        if _is_lookback(start): return {"period": start}
        kw = {"start": start}
        if end is not None: kw["end"] = end
        return kw

    def get_history(self, sym, tf="1d", start=None, end=None, src="contract"):
        if tf not in _INTERVAL: raise NotSupported(f"tf {tf}")
        if tf in _INTRADAY_DEFAULT: return self.get_intraday(sym, tf, start, end, src)
        code = self._code(self.resolve(sym, src))
        df = self._yf.Ticker(code).history(interval=_INTERVAL[tf], auto_adjust=False, **self._span(start, end))
        return df if len(df) else empty_frame()

    def get_intraday(self, sym, tf="15m", start=None, end=None, src="contract"):
        if tf not in _INTRADAY_DEFAULT: raise NotSupported(f"intraday tf {tf}")
        code = self._code(self.resolve(sym, src))
        T = self._yf.Ticker(code)
        df = T.history(interval=tf, auto_adjust=False, **self._span(start or _INTRADAY_DEFAULT[tf], end))
        if len(df) == 0 and tf == "60m" and start is None:   # 730d window can fail for contracts listed < 2 years ago
            for p2 in ("700d", "365d", "180d"):
                df = T.history(period=p2, interval=tf, auto_adjust=False)
                if len(df): break
        return df if len(df) else empty_frame()

    def get_history_batch(self, syms, tf="1d", start=None, end=None):
        codes = {}
        for s in syms:
            c = SY.to_vendor(s, self.name)
            if c: codes[c] = s
        if not codes: return {}
        df = self._yf.download(list(codes), interval=_INTERVAL.get(tf, "1d"), progress=False, auto_adjust=False,
                               threads=True, group_by="ticker", **self._span(start, end))
        out = {}
        for c, s in codes.items():
            try: out[s] = df[c] if isinstance(df.columns, pd.MultiIndex) else df
            except KeyError: out[s] = empty_frame()
        return out

    def get_quote(self, sym):
        code = self._code(sym)
        try: i = self._yf.Ticker(code).info or {}
        except Exception: i = {}
        g = i.get
        return dict(last=g("regularMarketPrice"), prev=g("regularMarketPreviousClose"), open=g("regularMarketOpen"),
                    high=g("regularMarketDayHigh"), low=g("regularMarketDayLow"), volume=g("regularMarketVolume"),
                    oi=g("openInterest"), time=g("regularMarketTime"), expiry=(g("expireIsoDate") or "")[:10] or None,
                    wk52_high=g("fiftyTwoWeekHigh"), wk52_low=g("fiftyTwoWeekLow"), currency=g("currency"), short_name=g("shortName"))
