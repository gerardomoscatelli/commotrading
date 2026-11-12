"""Canonical symbol map: internal id -> per-vendor code.

Internal ids (used everywhere in the app, the API and the browser):
  futures contract   ROOT+MONTH+YY  ZSF27, ZCH27, BZF27, 6EZ26, TTFF27
  continuous front   ROOT+"1!"      ZS1!, CL1!, GC1!, SI1!, CPO1!
  instruments        DXY, US10Y, SPX, NDX, VIX, BTCUSD, EURUSD, XAGUSD (silver spot), XAUUSD (gold spot)

To add a vendor: add an entry to VENDOR with its contract format, continuous format and instrument codes.
"""
import re

MONTHS = "FGHJKMNQUVXZ"
MNAME = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# futures roots: name, exchange, unit, currency, decimals
FUTURES = {
 "ZS": ("Soybeans", "CBOT", "¢/bu", "US cents", 2),
 "ZM": ("Soybean Meal", "CBOT", "$/st", "USD", 1),
 "ZL": ("Soybean Oil", "CBOT", "¢/lb", "US cents", 2),
 "ZC": ("Corn", "CBOT", "¢/bu", "US cents", 2),
 "ZW": ("Wheat SRW", "CBOT", "¢/bu", "US cents", 2),
 "KE": ("KC Wheat HRW", "CBOT", "¢/bu", "US cents", 2),
 "CL": ("WTI Crude Oil", "NYMEX", "$/bbl", "USD", 2),
 "BZ": ("Brent Crude Oil", "NYMEX", "$/bbl", "USD", 2),
 "HO": ("NY Harbor ULSD", "NYMEX", "$/gal", "USD", 4),
 "RB": ("RBOB Gasoline", "NYMEX", "$/gal", "USD", 4),
 "NG": ("Henry Hub Natural Gas", "NYMEX", "$/MMBtu", "USD", 3),
 "TTF": ("Dutch TTF Natural Gas", "NYMEX", "€/MWh", "EUR", 3),
 "6E": ("Euro FX", "CME", "$ per €", "USD", 5),
 "GC": ("Gold (COMEX front month)", "COMEX", "$/oz", "USD", 1),
 "SI": ("Silver (COMEX front month)", "COMEX", "$/oz", "USD", 3),
 "CPO": ("Crude Palm Oil (USD)", "CME", "$/t", "USD", 2),
}
# continuous-only display overrides (name used when the id is ROOT1!)
INSTRUMENTS = {
 "DXY": ("US Dollar Index", "ICE", "index pts", "USD", 3),
 "US10Y": ("US 10Y Treasury yield", "CBOE", "% yield", "", 3),
 "SPX": ("S&P 500", "Index", "index pts", "USD", 2),
 "NDX": ("Nasdaq 100", "Index", "index pts", "USD", 2),
 "VIX": ("VIX volatility", "CBOE", "index pts", "", 2),
 "BTCUSD": ("Bitcoin", "Spot", "$", "USD", 0),
 "EURUSD": ("EUR/USD spot", "FX", "$ per €", "USD", 5),
 "XAGUSD": ("Silver spot", "Spot", "$/oz", "USD", 2),
 "XAUUSD": ("Gold spot", "Spot", "$/oz", "USD", 1),
}

# per-vendor codes. contract: format with {root},{m},{yy},{yyyy},{sfx}; cont: format with {root}; instr: id -> code (None = not served)
VENDOR = {
 "yahoo": {
   "contract": "{root}{m}{yy}{sfx}",
   "suffix": {"ZS": ".CBT", "ZM": ".CBT", "ZL": ".CBT", "ZC": ".CBT", "ZW": ".CBT", "KE": ".CBT",
              "CL": ".NYM", "BZ": ".NYM", "HO": ".NYM", "RB": ".NYM", "NG": ".NYM", "TTF": ".NYM", "6E": ".CME",
              "GC": ".CMX", "SI": ".CMX"},
   "cont": "{root}=F",
   "instr": {"DXY": "DX-Y.NYB", "US10Y": "^TNX", "SPX": "^GSPC", "NDX": "^NDX", "VIX": "^VIX", "BTCUSD": "BTC-USD", "EURUSD": "EURUSD=X"},
 },
 "goldapi": {"instr": {"XAGUSD": "XAG", "XAUUSD": "XAU"}},
 # example for a paid vendor (see template_adapter.py); fill in the vendor's real formats
 "template": {
   "contract": "{root}{m}{yy}", "suffix": {}, "cont": "{root}*1",
   "instr": {"DXY": "DXY", "US10Y": "US10Y", "SPX": "SPX", "NDX": "NDX", "VIX": "VIX", "BTCUSD": "BTCUSD", "EURUSD": "EURUSD"},
 },
}

_ROOTS = sorted(FUTURES, key=len, reverse=True)

def parse(sym):
    """-> dict(kind='contract'|'cont'|'instr'|'unknown', root, code, year, month)."""
    s = (sym or "").strip().upper()
    if s in INSTRUMENTS: return dict(kind="instr", id=s, root=None)
    if s.endswith("1!") and s[:-2] in FUTURES: return dict(kind="cont", id=s, root=s[:-2])
    for r in _ROOTS:
        m = re.fullmatch(re.escape(r) + r"([FGHJKMNQUVXZ])(\d{2})", s)
        if m: return dict(kind="contract", id=s, root=r, code=m.group(1), year=2000 + int(m.group(2)), month=MONTHS.index(m.group(1)) + 1)
    return dict(kind="unknown", id=s, root=None)

def contract_id(root, code, year): return f"{root}{code}{str(year)[2:]}"
def cont_id(root): return f"{root}1!"

def to_vendor(sym, vendor):
    """Canonical id -> vendor code, or None if the vendor does not carry it."""
    v = VENDOR.get(vendor); p = parse(sym)
    if not v: return None
    if p["kind"] == "instr": return v.get("instr", {}).get(p["id"])
    if p["kind"] == "cont": return v["cont"].format(root=p["root"]) if "cont" in v else None
    if p["kind"] == "contract" and "contract" in v:
        sfx = v.get("suffix", {})
        if sfx and p["root"] not in sfx: return None
        return v["contract"].format(root=p["root"], m=p["code"], yy=str(p["year"])[2:], yyyy=p["year"], sfx=sfx.get(p["root"], ""))
    return None

def normalize(sym):
    """Accept canonical ids and legacy vendor codes (old bookmarks/links), return the canonical id."""
    s = (sym or "").strip().upper()
    if parse(s)["kind"] != "unknown": return s
    for v in VENDOR.values():
        for k, code in v.get("instr", {}).items():
            if code and s == code.upper(): return k
    m = re.fullmatch(r"([A-Z0-9]+)=F", s)
    if m and m.group(1) in FUTURES: return cont_id(m.group(1))
    m = re.fullmatch(r"([A-Z0-9]+?[FGHJKMNQUVXZ]\d{2})\.[A-Z]{3}", s)
    if m and parse(m.group(1))["kind"] == "contract": return m.group(1)
    return s

def static_info(sym):
    """name, exchange, unit, currency, decimals, symbol (+ contract, month) from the static tables."""
    p = parse(sym)
    base = FUTURES.get(p["root"]) if p["root"] else INSTRUMENTS.get(p["id"])
    name, exch, unit, ccy, dec = base or (p["id"], "", "", "", 2)
    d = dict(name=name, exchange=exch, unit=unit, currency=ccy, decimals=dec, symbol=p["id"])
    if p["kind"] == "contract":
        d["contract"] = p["id"]; d["month"] = f"{MNAME[p['month']-1]} {p['year']}"
    elif p["kind"] == "cont" and p["root"] not in ("GC", "SI", "CPO"):
        d["contract"] = f"{p['root']} front month (continuous)"
    return d
