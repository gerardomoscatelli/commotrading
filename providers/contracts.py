"""Exchange calendar helpers (no holiday calendar): last business days, ICE Brent expiry, estimated last-trade dates.
Used when a vendor does not report an expiry, and by the Brent curve filter."""
import datetime as dt

def last_business_day(y, m):
    """Last Mon–Fri of calendar month y-m."""
    d = dt.date(y + 1, 1, 1) - dt.timedelta(days=1) if m == 12 else dt.date(y, m + 1, 1) - dt.timedelta(days=1)
    while d.weekday() >= 5: d -= dt.timedelta(days=1)
    return d

# Optional known ICE Brent last-trade overrides (YYYY-MM -> date). Else last BD of M-2.
BRENT_LAST_TRADE = {}

def brent_expiry(y, m):
    """Expiry of Brent delivery month M: known last-trade if set, else last business day of M-2."""
    key = f"{y}-{m:02d}"
    if key in BRENT_LAST_TRADE: return BRENT_LAST_TRADE[key]
    ey, em = (y - 1, m + 10) if m <= 2 else (y, m - 2)
    return last_business_day(ey, em)

def bd_before(d, n):
    """n business days before d."""
    while n > 0:
        d -= dt.timedelta(days=1)
        if d.weekday() < 5: n -= 1
    return d

def est_expiry(root, y, m):
    """Approximate last trading day per exchange rule (marked 'est.' in the UI)."""
    first = dt.date(y, m, 1); prev_y, prev_m = (y - 1, 12) if m == 1 else (y, m - 1)
    if root in ("ZS", "ZM", "ZL", "ZC", "ZW", "KE"): return bd_before(dt.date(y, m, 15), 1)
    if root == "CL":
        d = dt.date(prev_y, prev_m, 25)
        return bd_before(d, 3) if d.weekday() < 5 else bd_before(bd_before(d, 1) + dt.timedelta(days=1), 3)
    if root == "BZ": return brent_expiry(y, m)
    if root in ("HO", "RB"): return last_business_day(prev_y, prev_m)
    if root == "NG": return bd_before(first, 3)
    if root == "TTF": return bd_before(first, 2)
    if root == "6E":
        d = first; w = 0
        while True:
            if d.weekday() == 2:
                w += 1
                if w == 3: break
            d += dt.timedelta(days=1)
        return bd_before(d, 2)
    return None
