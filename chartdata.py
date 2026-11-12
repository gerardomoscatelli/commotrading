"""TradingView-style chart data for the commodash chart window (12 Nov 2026; provider layer 12 Nov 2026).
chart(sym, tf, src) -> OHLCV columns for 15m / 60m / 1d / 1wk / 1mo, plus contract details (units, expiry, OI ...).
Daily = full listed life of the contract; weekly/monthly are resampled from daily. Intraday 15m ~60 days, 1h ~2 years
with the default feed. All prices come from providers.get_provider(); this module never talks to a vendor.
Shared by server.py (local FastAPI) and build.py (static GitHub Pages build)."""
import datetime as dt
import pandas as pd
from providers import get_provider, symbols as SY

TF = ("15m", "60m", "1d", "1wk", "1mo")

def _clean(df):
    df = df.dropna(subset=["Close"])
    return df[(df["High"] > 0) | (df["Close"] > 0)]

def _resample(df, rule):
    if df.index.tz is not None: df = df.tz_localize(None)
    r = df.resample(rule, label="left", closed="left")
    return pd.DataFrame({"Open": r["Open"].first(), "High": r["High"].max(), "Low": r["Low"].min(), "Close": r["Close"].last(), "Volume": r["Volume"].sum()}).dropna(subset=["Close"])

def _cols(df, intraday):
    o = df["Open"].where(df["Open"] > 0, df["Close"])  # some settles carry open=0
    h = pd.concat([df["High"], o, df["Close"]], axis=1).max(axis=1)
    l = pd.concat([df["Low"].where(df["Low"] > 0, df["Close"]), o, df["Close"]], axis=1).min(axis=1)
    t = [int(x.timestamp()) for x in df.index] if intraday else [str(x.date()) for x in df.index]
    v = df["Volume"].fillna(0)
    rnd = lambda s: [round(float(x), 6) for x in s]
    # recent coverage decides: some series report volume only on scattered days (shown as none)
    hasv = len(v) > 0 and (float((v.tail(120) > 0).mean()) > 0.5 if len(v) >= 120 else float((v > 0).mean()) > 0.2)
    return dict(t=t, o=rnd(o), h=rnd(h), l=rnd(l), c=rnd(df["Close"]), v=[float(x) for x in v] if hasv else None)

def details(sym, daily, P):
    d = P.get_contract_info(sym)
    try: q0 = P.get_quote(sym) or {}
    except Exception: q0 = {}
    if d.get("expiry"):
        d["days_to_expiry"] = (dt.date.fromisoformat(d["expiry"]) - dt.date.today()).days
    c = daily.get("c") or []
    if c:
        n = len(c)
        q = dict(last=c[-1], prev=c[-2] if n > 1 else None, open=daily["o"][-1], high=daily["h"][-1], low=daily["l"][-1], date=daily["t"][-1],
                 volume=(daily["v"][-1] if daily.get("v") else None))
        # the live quote is fresher (current session) when the vendor provides one
        if q0.get("last") is not None and q0.get("prev"):
            q.update(last=q0["last"], prev=q0["prev"])
            for k in ("open", "high", "low", "volume"):
                if q0.get(k): q[k] = q0[k]
            if q0.get("time"): q["time"] = int(q0["time"])
        if q["prev"]: q["chg"] = q["last"] - q["prev"]; q["pct"] = (q["last"] / q["prev"] - 1) * 100
        q["oi"] = q0.get("oi")
        t = daily["t"]; cut = str(dt.date.today() - dt.timedelta(days=365))
        i0 = next((i for i, x in enumerate(t) if x >= cut), 0)
        q["wk52_high"] = max(daily["h"][i0:]); q["wk52_low"] = min(daily["l"][i0:])
        q["life_high"] = max(daily["h"]); q["life_low"] = min(daily["l"]); q["life_from"] = t[0]
        q["life_high_date"] = t[daily["h"].index(q["life_high"])]; q["life_low_date"] = t[daily["l"].index(q["life_low"])]
        d["quote"] = q
    return d

def chart(sym, tf="1d", src="auto", price_secs=None):
    if tf not in TF: raise ValueError("tf must be one of " + ",".join(TF))
    P = get_provider()
    sym = SY.normalize(sym); p = SY.parse(sym)
    use = sym
    res = dict(requested=sym, tf=tf, continuous=p["kind"] == "cont", fallback=False)
    if p["kind"] == "contract" and src == "cont": use = SY.cont_id(p["root"]); res["continuous"] = True
    daily_df = _clean(P.get_history(use, "1d"))
    if p["kind"] == "contract" and src == "auto" and len(daily_df) < 20:
        res["note"] = f"{sym}: only {len(daily_df)} daily bars so far; showing the continuous front month"
        use = SY.cont_id(p["root"]); res.update(continuous=True, fallback=True)
        daily_df = _clean(P.get_history(use, "1d"))
    if len(daily_df) == 0: raise RuntimeError("no history returned for " + use)
    daily = _cols(daily_df, False)
    if tf == "1d": df_out = daily
    elif tf == "1wk": df_out = _cols(_resample(daily_df, "W-MON"), False)
    elif tf == "1mo": df_out = _cols(_resample(daily_df, "MS"), False)
    else:
        idf = _clean(P.get_intraday(use, tf))
        if len(idf) == 0: raise RuntimeError(f"no {tf} bars for {use}")
        df_out = _cols(idf, True)
    if tf in ("1wk", "1mo") and daily["v"] is None: df_out["v"] = None   # follow the daily volume decision
    res.update(symbol=use, bars=df_out, intraday=tf in ("15m", "60m"), has_volume=df_out["v"] is not None, n=len(df_out["t"]),
               first=df_out["t"][0], last=df_out["t"][-1], details=details(use, daily, P))
    if use != sym and p["kind"] == "contract": res["details"]["requested_contract"] = sym
    res["fetched"] = dt.datetime.now(dt.timezone.utc).isoformat()
    return res
