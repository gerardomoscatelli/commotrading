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
JOBS=[("prices",prices),("cracks",S.cracks),("crush",S.crush),("palm",S.palm),("fx",S.fx),("macro",S.macro),("news",S.news),
      ("gnews",S.general_news),("agnews",S.ags_news),("vessels",S.vessels),("clim",clim),("weather",wx)]
# ---- chart history (all prices via the provider layer, providers/; symbols are canonical ids) ----
from providers import symbols as SY
MAC={t for t,_,_ in S.MACRO}|{"EURUSD","CPO1!","SI1!"}  # SI1!: silver row in the macro snapshot
def fname(sym): return re.sub(r"[^A-Za-z0-9.\-]","_",sym)+".json"
def hist_symbols():
    syms=set(MAC)|{SY.cont_id(r) for r,*_ in S.PRODUCTS.values()}
    def walk(o):
        if isinstance(o,dict):
            c=o.get("contract")
            if isinstance(c,str) and S.contract_allowed(c): syms.add(c)
            for v in o.values(): walk(v)
        elif isinstance(o,list):
            for v in o: walk(v)
    for n in ("prices","fx","crush","cracks"): walk(load(n))
    return sorted(syms)
# Chart window (12 Nov 2026): per symbol, write hist/chart/<sym>__<tf>.json for 15m, 60m and 1d.
# Weekly and monthly are resampled from the daily file in the browser. Failed fetches reuse the last good daily file from .cache/chart when present.
import chartdata as CD
CHART_TFS=("15m","60m","1d")
def _chart_one(arg):
    sym,tf=arg
    try: return sym,tf,CD.chart(sym,tf,"auto")
    except Exception as e: return sym,tf,{"error":f"{type(e).__name__}: {e}"}
def _compact(o): return json.dumps(o,separators=(",",":"),default=str)
def build_hist(hd):
    cd=os.path.join(hd,"chart"); keep=os.path.join(ROOT,".cache","chart"); os.makedirs(cd,exist_ok=True); os.makedirs(keep,exist_ok=True)  # last-good daily files: local cache, NOT in data/ (the workflow commits data/ every run)
    ok=bad=0; idx={}; syms=hist_symbols()
    with ThreadPoolExecutor(6) as ex:
        for sym,tf,res in ex.map(_chart_one,[(s,t) for s in syms for t in CHART_TFS]):
            fn=fname(sym)[:-5]+"__"+tf+".json"; f=os.path.join(cd,fn); k=os.path.join(keep,fn)
            if "error" in res:
                bad+=1
                if os.path.exists(k): shutil.copy(k,f)
                else: continue
            else:
                txt=_compact(res); open(f,"w").write(txt); ok+=1
                if tf=="1d": open(k,"w").write(txt)   # keep only daily as last-good state (intraday goes stale anyway)
            idx.setdefault(sym,[]).append(tf)
    json.dump(idx,open(os.path.join(cd,"index.json"),"w"))
    RESULTS["hist"]=f"{ok} ok, {bad} failed of {len(syms)*len(CHART_TFS)} chart files"
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
    assets_src=os.path.join(ROOT,"assets")
    if os.path.isdir(assets_src):
        assets_dst=os.path.join(SITE,"assets")
        if os.path.isdir(assets_dst): shutil.rmtree(assets_dst)
        shutil.copytree(assets_src, assets_dst)
    open(f"{SITE}/.nojekyll","w").close()
    print(json.dumps(RESULTS,indent=1))
if __name__=="__main__": main()
