"""TEMPLATE: how to plug in a professional market-data vendor (Barchart OnDemand, CQG, Databento, LSEG/Refinitiv, ICE Connect ...).

Steps
1. Copy this file to providers/<vendor>_adapter.py and rename the class / `name` (e.g. name = "databento").
2. Add the vendor's symbol formats to providers/symbols.py -> VENDOR["<vendor>"]
   (contract format, continuous format, instrument codes). Symbols reaching this class are canonical ids
   (ZSF27, ZS1!, GC1!, DXY ...); translate them with SY.to_vendor(sym, self.name).
3. Implement get_history, get_intraday, get_quote (and optionally get_history_batch, get_contract_info, get_volume_oi).
   Return pandas DataFrames with columns Open, High, Low, Close, Volume (see providers/base.py).
4. Register it in providers/__init__.py -> REGISTRY.
5. Set the API key in the environment (never in code or in git), then select the vendor:
       COMMODASH_PROVIDER=<vendor>         (e.g. in .env next to server.py, or in Windows: set COMMODASH_PROVIDER=databento)
       COMMODASH_FALLBACK=yahoo            (optional: used when the vendor errors or has no data for a symbol)
       <VENDOR>_API_KEY=...                (this template reads TEMPLATE_API_KEY)
   or put {"provider": "<vendor>", "fallback": ["yahoo"]} in providers.json next to server.py.

Vendor hints
- Databento:  databento.Historical(key).timeseries.get_range(dataset="GLBX.MDP3", schema="ohlcv-1d" | "ohlcv-1m",
              stype_in="raw_symbol", symbols=["ZSF7"], start=..., end=...)  -> resample 1m to 15m/60m; IFEU.IMPACT for ICE Brent/TTF.
- Barchart OnDemand:  getHistory.json?apikey=...&symbol=ZSF27&type=daily|minutes&interval=15&startDate=...  ; getQuote.json for quotes/OI.
- CQG / LSEG / ICE: map the same methods onto their history and quote calls.
"""
import os
import pandas as pd
from .base import PriceProvider, NotSupported, empty_frame
from . import symbols as SY

class TemplateProvider(PriceProvider):
    name = "template"
    label = "Template vendor"
    KEY_ENV = "TEMPLATE_API_KEY"

    def __init__(self):
        self.key = os.getenv(self.KEY_ENV)          # never hardcode keys
        if not self.key:
            raise RuntimeError(f"{self.KEY_ENV} is not set")
        # self.session = requests.Session(); self.session.headers["Authorization"] = f"Bearer {self.key}"

    def _code(self, sym):
        c = SY.to_vendor(sym, self.name)
        if not c: raise NotSupported(sym)
        return c

    def get_history(self, sym, tf="1d", start=None, end=None, src="contract"):
        code = self._code(self.resolve(sym, src))
        # rows = self.session.get(BASE + "/history", params={"symbol": code, "interval": tf, "start": start, "end": end}).json()
        # df = pd.DataFrame(rows).rename(columns={"o": "Open", "h": "High", "l": "Low", "c": "Close", "v": "Volume"})
        # df.index = pd.to_datetime(df.pop("t"), unit="s", utc=True); return df
        raise NotImplementedError(f"implement history for {code}")

    def get_intraday(self, sym, tf="15m", start=None, end=None, src="contract"):
        return self.get_history(sym, tf, start, end, src)

    def get_quote(self, sym):
        code = self._code(sym)
        # j = self.session.get(BASE + "/quote", params={"symbol": code}).json()
        # return dict(last=j["last"], prev=j["settle_prev"], open=j["open"], high=j["high"], low=j["low"],
        #             volume=j["volume"], oi=j["open_interest"], time=j["ts"], expiry=j.get("expiration"))
        raise NotImplementedError(f"implement quote for {code}")
