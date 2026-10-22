"""One-shot static build for GitHub Pages: runs every data job once and writes site/.
State (data/*.json, data/maps/*.png) is kept in the repo and committed back by the workflow,
so the vessel extractor (keeps previous incidents) and climatology (recomputed once/day) persist."""
import json, os, re, sys, shutil, time, traceback, datetime as dt
from concurrent.futures import ThreadPoolExecutor
ROOT=os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT); sys.path.insert(0,ROOT)
D=os.path.join(ROOT,"data"); SITE=os.path.join(ROOT,"site")
os.makedirs(D,exist_ok=True)
import sources as S
now=lambda: dt.datetime.now(dt.timezone.utc).isoformat()
def load(n):
    try: return json.load(open(f"{D}/{n}.json"))
    except Exception: return {"error":"not yet fetched"}
def save(n,o):
    o["updated"]=now(); tmp=f"{D}/{n}.json.tmp"; json.dump(o,open(tmp,"w"),default=str); os.replace(tmp,f"{D}/{n}.json")
RESULTS={}
def run(n,fn):
    t=time.time()
    try:
        o=fn()
        if not isinstance(o,dict) or (o.get("error") and len(o)<=2): raise RuntimeError((o or {}).get("error","empty result"))
        save(n,o); RESULTS[n]=f"ok ({time.time()-t:.0f}s)"
    except Exception as e:
        old=load(n); old["error_last"]=f"{type(e).__name__}: {e}"; old["error_at"]=now()
        json.dump(old,open(f"{D}/{n}.json","w"),default=str); RESULTS[n]=f"FAILED, kept previous: {old['error_last'][:150]}"; traceback.print_exc()
def prices(): return {k:S.realtime_curve(k) for k in S.PRODUCTS if k!="6E"}
def clim():
    c=load("clim")
    if c.get("date")==str(dt.date.today()) and c.get("clim7"): return c
    return S.climatology()
def wx():
    w=S.weather()
    try:
        import maps; w["maps"]=maps.render_all(w,load("clim"))
    except Exception as e: w["maps_error"]=f"{type(e).__name__}: {e}"
    return w
JOBS=[("prices",prices),("cracks",S.cracks),("crush",S.crush),("fx",S.fx),("macro",S.macro),("news",S.news),
      ("gnews",S.general_news),("agnews",S.ags_news),("vessels",S.vessels),("clim",clim),("weather",wx)]
# ---- popup history ----
MAC={t for t,_,_ in S.MACRO}|{"EURUSD=X"}
def okcontract(sym):
    m=re.fullmatch(r"([A-Z0-9]+?)([FGHJKMNQUVXZ])(\d{2})(\.[A-Z]{3})",sym)
    if not m: return None
    for root,suf,allowed,*_ in S.PRODUCTS.values():
        if m.group(1)==root and m.group(4)==suf and m.group(2) in allowed: return root
    return None
def fname(sym): return re.sub(r"[^A-Za-z0-9.\-]","_",sym)+".json"
def ohlcv(sym):
    import yfinance as yf
    df=yf.Ticker(sym).history(period="2y",interval="1d",auto_adjust=False); return df.dropna(subset=["Close"])
def pack(df):
    c=df["Close"]; out=dict(dates=[str(d.date()) for d in df.index],open=df["Open"].round(6).tolist(),high=df["High"].round(6).tolist(),low=df["Low"].round(6).tolist(),close=c.round(6).tolist())
    for n in (20,50,100,200): out[f"sma{n}"]=[None if x!=x else round(float(x),6) for x in c.rolling(n).mean()]
    v=df["Volume"].fillna(0); out["volume"]=v.tolist() if float(v.sum())>0 else None
    return out
def hist(sym):
    root=okcontract(sym); cont=sym.endswith("=F")
    res=dict(requested=sym,symbol=sym,continuous=cont,fallback=False)
    try:
        df=ohlcv(sym)
        if root and len(df)<220:
            res["note"]=f"{sym}: only {len(df)} daily bars on Yahoo, not enough for a 200d SMA; showing continuous front month {root}=F"
            df=ohlcv(root+"=F"); res.update(symbol=root+"=F",continuous=True,fallback=True)
        if len(df)==0: res["error"]="no history returned by Yahoo"
        else:
            if len(df)<200: res["warn"]=f"not enough history for 200d SMA ({len(df)} bars)"
            res.update(pack(df))
        res["fetched"]=now()
    except Exception as e: res["error"]=f"{type(e).__name__}: {e}"
    return sym,res
def hist_symbols():
    syms=set(MAC)|{r+"=F" for r,*_ in S.PRODUCTS.values()}
    sufs={suf for _,suf,*_ in S.PRODUCTS.values()}
    def walk(o):
        if isinstance(o,dict):
            c=o.get("contract")
            if isinstance(c,str):
                for s in sufs:
                    if okcontract(c+s): syms.add(c+s)
            for v in o.values(): walk(v)
        elif isinstance(o,list):
            for v in o: walk(v)
    for n in ("prices","fx","crush","cracks"): walk(load(n))
    return sorted(syms)
def build_hist(hd):
    os.makedirs(hd,exist_ok=True); ok=bad=0; idx={}
    with ThreadPoolExecutor(6) as ex:
        for sym,res in ex.map(hist,hist_symbols()):
            f=os.path.join(hd,fname(sym))
            if "error" in res and os.path.exists(os.path.join(D,"hist",fname(sym))):
                shutil.copy(os.path.join(D,"hist",fname(sym)),f); bad+=1
            else:
                json.dump(res,open(f,"w")); ok+=("error" not in res); bad+=("error" in res)
            idx[sym]=fname(sym)
    json.dump(idx,open(os.path.join(hd,"index.json"),"w"))
    RESULTS["hist"]=f"{ok} ok, {bad} failed/kept of {len(idx)}"
def main():
    skip=set(os.getenv("SKIP_JOBS","").split(","))
    for n,fn in JOBS:
        if n not in skip: print("job",n,flush=True); run(n,fn)
    if os.path.isdir(SITE): shutil.rmtree(SITE)
    os.makedirs(f"{SITE}/data"); os.makedirs(f"{SITE}/maps")
    for n,_ in JOBS: shutil.copy(f"{D}/{n}.json",f"{SITE}/data/{n}.json")
    for p in ("precip","tmax","anom"):
        if os.path.exists(f"{D}/maps/{p}.png"): shutil.copy(f"{D}/maps/{p}.png",f"{SITE}/maps/{p}.png")
    if "hist" not in skip: build_hist(f"{SITE}/hist")
    json.dump(dict(built=now(),jobs=RESULTS),open(f"{SITE}/data/build.json","w"),indent=1)
    shutil.copy(os.path.join(ROOT,"templates","index.html"),f"{SITE}/index.html")
    open(f"{SITE}/.nojekyll","w").close()
    print(json.dumps(RESULTS,indent=1))
if __name__=="__main__": main()
