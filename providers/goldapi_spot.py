"""Precious-metal spot adapter (gold-api.com, free, no key). Quotes only: XAGUSD, XAUUSD."""
import requests
from .base import PriceProvider, NotSupported
from . import symbols as SY

UA = {"User-Agent": "Mozilla/5.0 commodash"}

class GoldApiSpotProvider(PriceProvider):
    name = "goldapi"
    label = "gold-api.com"

    def supports(self, sym, what="history"):
        return what == "quote" and SY.to_vendor(sym, self.name) is not None

    def get_history(self, sym, tf="1d", start=None, end=None, src="contract"):
        raise NotSupported("spot adapter has no history")

    def get_quote(self, sym):
        code = SY.to_vendor(sym, self.name)
        if not code: raise NotSupported(sym)
        j = requests.get(f"https://api.gold-api.com/price/{code}", headers=UA, timeout=15).json()
        return dict(last=float(j["price"]), time=j.get("updatedAt"), source=self.label)
