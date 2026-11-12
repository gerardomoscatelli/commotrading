"""Market-data layer. The rest of the app talks ONLY to get_provider() (plus get_rates() for SOFR/€STR).

    from providers import get_provider
    P = get_provider()
    P.get_history("ZSF27", "1d")            # full life of the contract
    P.get_intraday("ZSF27", "15m")          # ~60 days with the default feed
    P.get_quote("GC1!"); P.get_contract_info("ZSF27"); P.get_volume_oi("ZSF27")

Configuration (env wins over file):
    COMMODASH_PROVIDER   primary vendor, default "yahoo"
    COMMODASH_FALLBACK   comma list tried in order when the primary errors / returns no data (default none)
    COMMODASH_SPOT       spot-metal quote adapter appended to the chain, default "goldapi" ("" to disable)
    COMMODASH_PROVIDER_CONFIG  path of a JSON file, default providers.json next to server.py:
        {"provider": "databento", "fallback": ["yahoo"], "spot": "goldapi", "ttl": {"quote": 60, "daily": 180}}
Caching: every call is cached in-process for a short TTL (seconds, configurable via "ttl" or PRICE_SECS for daily).
"""
import os, json, time, threading, logging
import pandas as pd
from .base import PriceProvider, NotSupported, empty_frame, TFS
from . import symbols
from .reference_rates import get_reference_rates

log = logging.getLogger("commodash.providers")

def _registry():
    from .yahoo_adapter import YahooProvider
    from .goldapi_spot import GoldApiSpotProvider
    from .template_adapter import TemplateProvider
    return {"yahoo": YahooProvider, "goldapi": GoldApiSpotProvider, "template": TemplateProvider}

def _config():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.getenv("COMMODASH_PROVIDER_CONFIG", os.path.join(root, "providers.json"))
    cfg = {}
    if os.path.exists(path):
        try: cfg = json.load(open(path))
        except Exception as e: log.warning("providers.json unreadable: %s", e)
    if os.getenv("COMMODASH_PROVIDER"): cfg["provider"] = os.getenv("COMMODASH_PROVIDER")
    if os.getenv("COMMODASH_FALLBACK") is not None: cfg["fallback"] = [x for x in os.getenv("COMMODASH_FALLBACK").split(",") if x.strip()]
    if os.getenv("COMMODASH_SPOT") is not None: cfg["spot"] = os.getenv("COMMODASH_SPOT")
    cfg.setdefault("provider", "yahoo"); cfg.setdefault("fallback", []); cfg.setdefault("spot", "goldapi")
    ttl = {"quote": 60, "info": 120, "intraday": 60, "daily": int(os.getenv("PRICE_SECS", "180")), "batch": 60}
    ttl.update(cfg.get("ttl") or {}); cfg["ttl"] = ttl
    return cfg

def _empty(r): return r is None or (isinstance(r, pd.DataFrame) and len(r) == 0) or (isinstance(r, dict) and not any(v is not None for v in r.values()))

class ProviderChain(PriceProvider):
    """Primary adapter + fallbacks, with a TTL cache. Implements the same interface."""
    name = "chain"

    def __init__(self, adapters, ttl):
        self.adapters = adapters; self.ttl = ttl; self._c = {}; self._l = threading.Lock()
        self.label = adapters[0].label if adapters else "Market data"
        self.primary = adapters[0].name if adapters else None

    # cache --------------------------------------------------------------------------------
    def _cached(self, kind, key, fn):
        with self._l:
            c = self._c.get(key)
            if c and time.time() - c[0] < self.ttl.get(kind, 60):
                v = c[1]
                return v.copy() if isinstance(v, pd.DataFrame) else v
        v = fn()
        with self._l: self._c[key] = (time.time(), v)
        return v.copy() if isinstance(v, pd.DataFrame) else v

    def clear_cache(self):
        with self._l: self._c.clear()

    # fallback -----------------------------------------------------------------------------
    def _first(self, what, sym, call):
        last_err, last_empty = None, None
        for a in self.adapters:
            if not a.supports(sym, what): continue
            try:
                r = call(a)
                if _empty(r): last_empty = r; continue
                return r
            except NotSupported: continue
            except Exception as e:
                last_err = e; log.warning("%s.%s(%s) failed: %s", a.name, what, sym, e)
        if last_empty is not None: return last_empty
        if last_err: raise last_err
        raise NotSupported(f"no provider serves {what} for {sym}")

    # interface ----------------------------------------------------------------------------
    def supports(self, sym, what="history"): return any(a.supports(sym, what) for a in self.adapters)

    def get_history(self, sym, tf="1d", start=None, end=None, src="contract"):
        kind = "intraday" if tf in ("15m", "60m") else "daily"
        s = self.resolve(sym, src)
        return self._cached(kind, ("h", s, tf, str(start), str(end)), lambda: self._first("history", s, lambda a: a.get_history(s, tf, start, end)))

    def get_intraday(self, sym, tf="15m", start=None, end=None, src="contract"):
        s = self.resolve(sym, src)
        return self._cached("intraday", ("i", s, tf, str(start), str(end)), lambda: self._first("intraday", s, lambda a: a.get_intraday(s, tf, start, end)))

    def get_quote(self, sym):
        return self._cached("quote", ("q", sym), lambda: self._first("quote", sym, lambda a: a.get_quote(sym)))

    def get_contract_info(self, sym):
        def run():
            info = symbols.static_info(sym)
            p = symbols.parse(sym)
            if p["kind"] == "contract":
                exp = None
                try: exp = (self.get_quote(sym) or {}).get("expiry")
                except Exception: pass
                from .contracts import est_expiry
                if exp: info.update(expiry=exp, expiry_est=False)
                else:
                    e = est_expiry(p["root"], p["year"], p["month"])
                    if e: info.update(expiry=str(e), expiry_est=True)
            return info
        return self._cached("info", ("c", sym), run)

    def get_volume_oi(self, sym):
        q = {}
        try: q = self.get_quote(sym) or {}
        except Exception: pass
        return {"volume": q.get("volume"), "oi": q.get("oi")}

    def get_history_batch(self, syms, tf="1d", start=None, end=None):
        syms = list(syms)
        def run():
            out = {}
            for a in self.adapters:
                todo = [s for s in syms if (s not in out or _empty(out[s])) and a.supports(s, "history")]
                if not todo: continue
                try: got = a.get_history_batch(todo, tf, start, end)
                except NotSupported: continue
                except Exception as e: log.warning("%s batch failed: %s", a.name, e); continue
                for s, df in got.items():
                    if s not in out or (_empty(out[s]) and not _empty(df)) or (s in out and _empty(out[s])): out[s] = df
            for s in syms: out.setdefault(s, empty_frame())
            return out
        r = self._cached("batch", ("b", tuple(syms), tf, str(start), str(end)), run)
        return {k: v.copy() for k, v in r.items()}

_P = None; _PL = threading.Lock()
def get_provider(refresh=False):
    """The configured provider chain (singleton)."""
    global _P
    with _PL:
        if _P is not None and not refresh: return _P
        cfg = _config(); reg = _registry(); names = [cfg["provider"]] + [n for n in cfg["fallback"] if n != cfg["provider"]]
        if cfg.get("spot"): names.append(cfg["spot"])
        adapters = []
        for n in names:
            cls = reg.get(n)
            if not cls: log.warning("unknown provider %r ignored", n); continue
            try: adapters.append(cls())
            except Exception as e: log.warning("provider %r unavailable: %s", n, e)
        if not any(a.name not in ("goldapi",) for a in adapters):   # primary failed to start: fall back to the default feed
            log.warning("no usable primary provider; using yahoo"); adapters.insert(0, reg["yahoo"]())
        _P = ProviderChain(adapters, cfg["ttl"])
        return _P

def get_rates():
    """SOFR / €STR (official, public)."""
    return get_reference_rates()

__all__ = ["get_provider", "get_rates", "PriceProvider", "NotSupported", "symbols", "TFS"]
