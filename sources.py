"""Modular data adapters. Each returns plain dicts; errors -> {'error': reason}.
Real-time providers: set COMMODASH_PROVIDER=databento|barchart plus DATABENTO_API_KEY / BARCHART_API_KEY
in /workspace/commodash/.env and implement the stub below (same output shape as yahoo_curve)."""
import os, json, datetime as dt, math, re, hashlib, requests, feedparser
import yfinance as yf
MC="FGHJKMNQUVXZ"
UA={"User-Agent":"Mozilla/5.0 commodash"}

def months_ahead(n, start=None, allowed=MC, skip_current=True):
    d=start or dt.date.today(); y,m=d.year,d.month+(1 if skip_current else 0)
    out=[]
    while len(out)<n:
        if m>12: y+=1; m-=12
        if MC[m-1] in allowed: out.append((MC[m-1],y,m))
        m+=1
    return out

# product: (yahoo root, suffix, allowed months, unit, n, note)
PRODUCTS={
 "CL":("CL",".NYM",MC,"$/bbl",8,"NYMEX WTI"),
 "BZ":("BZ",".NYM",MC,"$/bbl",8,"NYMEX Brent (financial, tracks ICE Brent)"),
 "HO":("HO",".NYM",MC,"$/gal",6,"NYMEX NY Harbor ULSD (heating oil)"),
 "RB":("RB",".NYM",MC,"$/gal",6,"NYMEX RBOB gasoline"),
 "NG":("NG",".NYM",MC,"$/MMBtu",8,"NYMEX Henry Hub"),
 "TTF":("TTF",".NYM",MC,"EUR/MWh",6,"Dutch TTF (NYMEX look-alike of ICE Endex)"),
 "6E":("6E",".CME","HMUZ","USD per EUR",5,"CME Euro FX futures"),
 "ZS":("ZS",".CBT","FHKNQUX","c/bu",7,"CBOT soybeans"),
 "ZM":("ZM",".CBT","FHKNQUVZ","$/short ton",7,"CBOT soybean meal"),
 "ZL":("ZL",".CBT","FHKNQUVZ","c/lb",7,"CBOT soybean oil"),
 "ZC":("ZC",".CBT","HKNUZ","c/bu",6,"CBOT corn"),
 "ZW":("ZW",".CBT","HKNUZ","c/bu",6,"CBOT SRW wheat"),
 "KE":("KE",".CBT","HKNUZ","c/bu",6,"KC HRW wheat"),
}

def yahoo_curve(key):
    root,suf,allowed,unit,n,note=PRODUCTS[key]
    # grains: include current month if contract not yet expired (e.g. ZSX in Oct)
    cands=months_ahead(n+2,allowed=allowed,skip_current=(root not in ("ZS","ZM","ZL","ZC","ZW","KE","6E")))
    tick={f"{root}{c}{str(y)[2:]}{suf}":(c,y,m) for c,y,m in cands}
    df=yf.download(list(tick),period="7d",interval="1d",progress=False,auto_adjust=False,threads=True,group_by="ticker")
    rows=[]
    for t,(c,y,m) in tick.items():
        try:
            s=df[t]["Close"].dropna()
            if len(s)<1: continue
            last=float(s.iloc[-1]); prev=float(s.iloc[-2]) if len(s)>1 else None
            rows.append(dict(contract=f"{root}{c}{str(y)[2:]}",month=f"{y}-{m:02d}",last=last,
              chg=None if prev is None else last-prev,pct=None if not prev else (last/prev-1)*100,
              asof=str(s.index[-1].date()),vol=float(df[t]["Volume"].dropna().iloc[-1]) if len(df[t]["Volume"].dropna()) else None))
        except Exception: pass
    rows=sorted(rows,key=lambda r:r["month"])[:n]
    out=dict(key=key,unit=unit,source=f"Yahoo Finance ({note}), delayed ~10-20 min / last settle",rows=rows)
    if not rows: out["error"]="no contract data returned by Yahoo"
    return out

def realtime_curve(key):  # plug-in point
    prov=os.getenv("COMMODASH_PROVIDER","yahoo")
    if prov=="databento" and os.getenv("DATABENTO_API_KEY"):
        raise NotImplementedError("Databento adapter: implement with databento.Historical(key).timeseries.get_range(dataset='GLBX.MDP3', schema='ohlcv-1d'/'mbp-1', stype_in='parent', symbols=[f'{key}.FUT'])")
    if prov=="barchart" and os.getenv("BARCHART_API_KEY"):
        raise NotImplementedError("Barchart OnDemand adapter: getQuote.json?apikey=...&symbols=CLZ26,...")
    return yahoo_curve(key)

def gasoil():
    return dict(key="LGO",unit="$/t",rows=[],source="ICE Futures Europe Low Sulphur Gasoil",
      error="source needed: no free, terms-compliant feed. ICE's site terms forbid robots/data extraction of its delayed prices; Yahoo has no ICE gasoil or NYMEX 7F look-alike; Barchart OnDemand has no free tier. Add a licensed key (Databento GLBX 7F, Barchart, ICE) to enable.")

def history(tickers,period="6mo"):
    df=yf.download(tickers,period=period,interval="1d",progress=False,auto_adjust=False,group_by="ticker")
    return {t:df[t]["Close"] for t in tickers}

def cracks():
    h=history(["CL=F","BZ=F","RB=F","HO=F"])
    import pandas as pd
    d=pd.DataFrame(h).dropna()
    rb,ho=d["RB=F"]*42,d["HO=F"]*42
    wti=(2*rb+ho-3*d["CL=F"])/3; brent=(2*rb+ho-3*d["BZ=F"])/3; hob=ho-d["BZ=F"]
    f=lambda s:[round(float(x),2) for x in s]
    return dict(dates=[str(x.date()) for x in d.index],wti321=f(wti),brent321=f(brent),ho_brent=f(hob),
      source="Yahoo front-month continuous CL=F, BZ=F, RB=F, HO=F (daily settles/last, delayed)",
      formula="3-2-1 = (2*RB*42 + 1*HO*42 - 3*Crude)/3 in $/bbl (RB, HO quoted $/gal, 42 gal/bbl). HO-Brent = HO*42 - BZ. Gasoil-Brent crack pending ICE gasoil source.")

def rates():
    out={}
    try:
        t=requests.get("https://data-api.ecb.europa.eu/service/data/EST/B.EU000A2X2A25.WT?lastNObservations=1&format=csvdata",timeout=20).text.strip().splitlines()
        hdr=t[0].split(","); v=t[-1].split(","); out["estr"]=float(v[hdr.index("OBS_VALUE")]); out["estr_date"]=v[hdr.index("TIME_PERIOD")]
    except Exception as e: out["estr_err"]=str(e)
    try:
        j=requests.get("https://markets.newyorkfed.org/api/rates/secured/sofr/last/1.json",timeout=20).json()["refRates"][0]
        out["sofr"]=j["percentRate"]; out["sofr_date"]=j["effectiveDate"]
    except Exception as e: out["sofr_err"]=str(e)
    return out

def fx():
    s=yf.Ticker("EURUSD=X").history(period="5d")["Close"].dropna()
    spot=float(s.iloc[-1]); prev=float(s.iloc[-2])
    r=rates(); fwd=[]
    if "estr" in r and "sofr" in r:
        for lbl,days in [("1M",30),("2M",61),("3M",91),("6M",182),("9M",273),("1Y",365),("2Y",730)]:
            f=spot*(1+r["sofr"]/100*days/360)/(1+r["estr"]/100*days/360)
            fwd.append(dict(tenor=lbl,days=days,eurusd=f,usdeur=1/f,points=(f-spot)*1e4))
    return dict(spot=spot,usdeur=1/spot,chg=spot-prev,pct=(spot/prev-1)*100,asof=str(s.index[-1]),rates=r,forwards=fwd,
      source="Spot: Yahoo EURUSD=X (delayed). Forwards COMPUTED by covered interest parity from SOFR (NY Fed) and €STR (ECB), ACT/360, simple interest - indicative, not dealer quotes. EUR is deliverable, so no true NDF exists; CME 6E futures shown as traded outright forwards.",
      futures=realtime_curve("6E"))

NEWSQ={"energy":"crude oil OR Brent OR WTI OR OPEC OR natural gas OR LNG OR diesel OR gasoline OR refinery","war":"Hormuz OR Iran OR \"Middle East\" OR Israel OR Russia Ukraine OR \"Black Sea\" OR \"Red Sea\" OR Houthi",
       "shipping":"tanker OR ship attack OR vessel struck OR shipping war risk","movers":"oil prices surge OR plunge OR jump OR slump OR gas prices spike"}
FEEDS=[("energy","https://oilprice.com/rss/main"),("energy","https://www.eia.gov/rss/todayinenergy.xml")]
AGQ={"usda":"USDA WASDE OR \"crop progress\" OR \"export sales\" OR NASS","us":"soybeans OR corn OR wheat CBOT futures OR harvest","eu":"FranceAgriMer OR \"Strategie Grains\" OR \"EU wheat\" OR \"EU maize\" OR \"EU crop\" OR Euronext wheat",
     "brazil":"CONAB OR IMEA OR Deral soja OR milho OR Brazil soybean crop","argentina":"\"Bolsa de Cereales\" OR \"Bolsa de Comercio de Rosario\" OR Argentina soybean OR maize OR wheat crop","estimates":"crop estimate OR production forecast grain OR oilseed"}
AGFEEDS=[("usda","https://www.usda.gov/rss/latest-releases.xml"),("us","https://www.farmprogress.com/rss.xml"),("us","https://www.agweb.com/rss/news"),("us","https://www.world-grain.com/rss/articles"),("us","https://www.brownfieldagnews.com/feed/")]
def gnews(q): return "https://news.google.com/rss/search?q="+requests.utils.quote(q+" when:2d")+"&hl=en-US&gl=US&ceid=US:en"

def _parse(cat,url,lim=25):
    f=feedparser.parse(requests.get(url,headers=UA,timeout=20).content); out=[]
    for e in f.entries[:lim]:
        t=e.get("published_parsed") or e.get("updated_parsed")
        src=(e.get("source") or {}).get("title") or f.feed.get("title","")
        out.append(dict(cat=cat,title=e.get("title","").strip(),link=e.get("link"),source=src,ts=dt.datetime(*t[:6],tzinfo=dt.timezone.utc).isoformat() if t else None))
    return out

GENQ={"world":"world news","macro":"economy OR inflation OR GDP OR central bank OR Fed OR ECB","markets":"stock market OR bonds OR dollar OR Wall Street","politics":"politics OR election OR government"}
GENFEEDS=[("world","https://feeds.bbci.co.uk/news/world/rss.xml"),("business","https://feeds.bbci.co.uk/news/business/rss.xml"),("world","https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"),
  ("business","https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en"),("markets","https://www.cnbc.com/id/100003114/device/rss/rss.html")]
def _collect(qs,feeds,src,lim=150):
    items,errs=[],[]
    for cat,q in qs.items():
        try: items+=_parse(cat,gnews(q))
        except Exception as e: errs.append(f"{cat}: {e}")
    for cat,u in feeds:
        try: items+=_parse(cat,u,20)
        except Exception as e: errs.append(f"{u}: {type(e).__name__}")
    seen,ded=set(),[]
    for i in sorted(items,key=lambda x:x["ts"] or "",reverse=True):
        k=re.sub(r"\W+","",re.sub(r" - [^-]+$","",i["title"]).lower())[:70]
        if k in seen: continue
        seen.add(k); ded.append(i)
    return dict(items=ded[:lim],errors=errs,source=src)
def ags_news(): return _collect(AGQ,AGFEEDS,"Google News RSS queries (USDA/NASS, CBOT, EU MARS/FranceAgriMer/Strategie Grains, CONAB/IMEA/Deral, BCBA/BCR) + USDA, Farm Progress, AgWeb, World-Grain, Brownfield RSS")
def general_news():
    q=dict(GENQ); q["fx"]="site:fxstreet.com"  # FXStreet direct RSS is Cloudflare-blocked (403); its articles via Google News RSS
    feeds=GENFEEDS+[("forexlive","https://www.forexlive.com/feed/news"),("forexlive","https://www.forexlive.com/feed")]
    out=_collect(q,feeds,"Google News RSS (top, business, queries, site:fxstreet.com) + BBC World/Business + CNBC + ForexLive/investingLive RSS",lim=150)
    for i in out["items"]:
        if i["cat"]=="forexlive": i["source"]="ForexLive"
    return out

GDELTQ='(Hormuz OR "tanker attack" OR "Red Sea" OR Houthi OR OPEC OR "crude oil" OR Brent OR "Russia Ukraine") sourcelang:english'
def _gcat(t):
    t=t.lower()
    if re.search(r"hormuz|tanker|red sea|houthi|ship|vessel",t): return "shipping"
    if re.search(r"ukrain|russia|iran|israel|war|strike|missile",t): return "war"
    return "energy"
_GCACHE=[]
def gdelt():
    """One combined GDELT DOC 2.1 query per run (GDELT allows max 1 req / 5 s per IP; one backoff retry)."""
    import time
    for att in range(2):
        try:
            r=requests.get("https://api.gdeltproject.org/api/v2/doc/doc",params=dict(query=GDELTQ,mode="ArtList",format="json",maxrecords=75,sort="DateDesc",timespan="2d"),headers=UA,timeout=40)
            if r.status_code==200 and r.text.strip().startswith("{"): break
            err=f"GDELT: HTTP {r.status_code} {'rate-limited' if r.status_code==429 else r.text[:60].strip()}"
        except Exception as e: err=f"GDELT: {type(e).__name__}"
        if att==0: time.sleep(12)
    else: return list(_GCACHE),[err+(f" (showing {len(_GCACHE)} cached)" if _GCACHE else "")]
    items=[]
    for a in r.json().get("articles",[]):
        try: ts=dt.datetime.strptime(a.get("seendate",""),"%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc).isoformat()
        except Exception: ts=None
        t=re.sub(r"\s+"," ",a.get("title","")).replace(" ,",",").strip()
        items.append(dict(cat=_gcat(t),title=t,link=a.get("url"),source=(a.get("domain") or "")+" (GDELT)",ts=ts))
    if not items: return list(_GCACHE),["GDELT: 0 articles returned"]
    _GCACHE[:]=items; return items,[]
def news():
    out=_collect(NEWSQ,FEEDS,"Google News RSS queries (energy, war/geopolitics, shipping, energy movers) + OilPrice, EIA RSS + GDELT DOC 2.1 API",lim=10**6)
    g,ge=gdelt(); out["errors"]+=ge; out["gdelt_count"]=len(g)
    seen,ded=set(),[]
    for i in sorted(out["items"]+g,key=lambda x:x["ts"] or "",reverse=True):
        k=re.sub(r"\W+","",re.sub(r" - [^-]+$","",i["title"]).lower())[:70]
        if not k or k in seen: continue
        seen.add(k); ded.append(i)
    out["items"]=ded[:180]; return out

SEED=[dict(date="2026-10-09",vessel="GEM NO. 2",imo="9735373",type="Crude tanker (VLCC), Panama",cargo="Not reported",location="~13 nm W of Al Jazeera, UAE",lat=25.70,lon=55.55,detail="Projectile/drone, fire extinguished, crew safe",source="UKMTO 160-26; IMO incident board"),
 dict(date="2026-10-10",vessel="VALTHERA",imo="9296389",type="Suezmax crude tanker, Marshall Is.",cargo="Iraqi crude ex-Basrah (Argus/Vortexa)",location="Strait of Hormuz, Omani waters",lat=26.33,lon=56.42,detail="Projectile, port side, fire contained (India says 11 Oct)",source="UKMTO; IMO; India MEA/MoPSW"),
 dict(date="2026-10-10",vessel="OCEAN MOLICA / AKIRA SUN",imo="9139270",type="Bulk carrier, 70,296 dwt, Panama",cargo="Not reported (ex-Iranian port)",location="Gulf of Oman (position not reported)",lat=24.9,lon=58.0,detail="Disabled by US jet (blockade enforcement)",source="CENTCOM"),
 dict(date="2026-10-11",vessel="PETRO DOLPHIN",imo="1072294",type="Product tanker, 3,922 dwt",cargo="Not reported",location="Sohar anchorage, Oman",lat=24.45,lon=56.85,detail="UAV/drone; 2 crew missing (India labour-state naming)",source="UKMTO 165-26; Ship & Bunker; India"),
 dict(date="2026-10-11",vessel="Unnamed (UKMTO 164-26)",imo="",type="Outbound tanker",cargo="Not reported",location="Strait of Hormuz (Fujairah-bound per JMIC Update 104)",lat=26.20,lon=56.55,detail="Port-side unidentified projectile ~1200 UTC; steering gear / port water tank damage; crew safe; no environmental impact at warning time",source="UKMTO 164-26; JMIC Update 104"),
 dict(date="2026-10-11",vessel="ANGOLA PROSPERITY (unconfirmed ID)",imo="9896414",type="VLCC crude tanker, Liberia (Sinokor)",cargo="Not reported",location="Outbound Strait of Hormuz",lat=26.15,lon=56.65,detail="Projectile, port side; name from single industry source (may overlap UKMTO unnamed files)",source="Seatrade Maritime (Vanguard Tech)"),
 dict(date="2026-10-11",vessel="Unnamed (UKMTO 166-26)",imo="",type="Outbound tanker",cargo="Not reported",location="Strait of Hormuz (position not reported)",lat=26.40,lon=56.50,detail="Unknown projectile; crew safe; environmental impact unknown; time-late report issued 12 Oct",source="UKMTO 166-26"),
 dict(date="2026-10-11",vessel="Unnamed (UKMTO 167-26)",imo="",type="Container vessel (inbound)",cargo="Containers",location="Strait of Hormuz (position not reported)",lat=26.55,lon=56.75,detail="Unknown projectile while inbound; no crew/damage/environment line on PDF; first dedicated box-ship Attack product on this autumn Hormuz tape",source="UKMTO 167-26"),
 dict(date="2026-10-11",vessel="Unnamed (UKMTO 168-26)",imo="",type="Products tanker (outbound)",cargo="Not reported",location="Strait of Hormuz (position not reported)",lat=26.35,lon=56.30,detail="Unknown projectile outbound; PDF revisions print 11 or 12 Oct; no crew/damage/environment line",source="UKMTO 168-26"),
 dict(date="2026-10-11",vessel="Unnamed (UKMTO 169-26)",imo="",type="Crude oil tanker (outbound)",cargo="Crude",location="Strait of Hormuz (position not reported)",lat=26.25,lon=56.45,detail="Unknown projectile outbound; no crew/damage/environment line; distinct from 166-26",source="UKMTO 169-26"),
 dict(date="2026-10-11",vessel="AL MAQAM (IRGC claim; not UKMTO-named)",imo="9732577",type="VLCC crude tanker, Liberia (~298,800 dwt)",cargo="Not confirmed",location="Strait of Hormuz (AIS-off colour; position not on UKMTO PDF)",lat=26.28,lon=56.60,detail="IRGC/Tasnim video: fire on funnel, tug responding; UAE-linked owner ADNOC L&S on industry reports; UKMTO did not name this hull against 166/168/169",source="Seatrade; TradeWinds; Maritime Executive (IRGC footage)"),]
VQ=['UKMTO incident','UKMTO warning','tanker attacked Hormuz','vessel struck Gulf of Oman','ship hit drone Strait of Hormuz','tanker OR vessel OR ship attacked Hormuz OR "Gulf of Oman" OR "Persian Gulf"']
VFEEDS=[("gCaptain","https://gcaptain.com/feed/"),("Splash247","https://splash247.com/feed/"),("Maritime Executive","https://maritime-executive.com/articles.rss"),
        ("Seatrade Maritime","https://www.seatrade-maritime.com/rss.xml"),("Hellenic Shipping News","https://www.hellenicshippingnews.com/feed/")]
REPUTABLE=["reuters","associated press","ap news","lloyd's list","lloyds list","tradewinds","gcaptain","splash","maritime executive","seatrade","hellenic shipping","bloomberg","bbc",
 "financial times","wall street journal","wsj","al jazeera","cnn","argus","s&p global","kpler","windward","ship & bunker","ship and bunker","the national","gulf news","marinelink","safety4sea","offshore energy","riviera","cnbc","the guardian","ukmto","jmic","centcom"]
LOC={"Fujairah":(25.12,56.45),"Khor Fakkan":(25.35,56.45),"Sohar":(24.40,56.85),"Ras al Khaimah":(25.85,55.85),"Ras Al Khaimah":(25.85,55.85),"Sharjah":(25.40,55.30),
 "Bandar Abbas":(27.05,56.25),"Muscat":(23.70,58.70),"Duqm":(19.60,57.80),"Qatar":(25.90,51.80),"Ras Laffan":(25.95,51.65),"Bahrain":(26.30,50.75),"Ras Tanura":(26.70,50.25),
 "Basrah":(29.70,48.85),"Basra":(29.70,48.85),"Kharg":(29.20,50.25),"Jebel Ali":(25.05,54.95),"Dubai":(25.30,55.10),"Hormuz":(26.45,56.50),"Gulf of Oman":(24.80,57.80),
 "Persian Gulf":(26.80,52.50),"Arabian Gulf":(26.80,52.50)}
VERB=re.compile(r"\b(attack(ed|s)?|struck|strikes?|hit|targeted|explosions?|blasts?|projectiles?|drones?|missiles?|ablaze|on fire|fire on board|boarded|seized|hijack(ed)?|sank|sinking|damaged|incident)\b",re.I)
VTYPES=[("VLCC","VLCC crude tanker"),("Suezmax","Suezmax tanker"),("Aframax","Aframax tanker"),("crude tanker","Crude tanker"),("oil tanker","Oil tanker"),("product tanker","Product tanker"),
 ("products tanker","Product tanker"),("chemical tanker","Chemical tanker"),("LPG","LPG carrier"),("LNG carrier","LNG carrier"),("container ship","Container ship"),("containership","Container ship"),
 ("box ship","Container ship"),("bulk carrier","Bulk carrier"),("bulker","Bulk carrier"),("cargo ship","Cargo ship"),("tanker","Tanker"),("dhow","Dhow")]
STOP={"UKMTO","UAE","US","USA","UK","EU","UN","IRAN","IRGC","OIL","LNG","LPG","VLCC","BREAKING","UPDATE","CENTCOM","NATO","JMIC","IMO","AIS","GPS","OPEC","NEW","LIVE","WATCH","VIDEO",
 "HORMUZ","GULF","OMAN","RED","SEA","AP","ADNOC","NIOC","QATARENERGY","ARAMCO","US-FLAGGED","NEWS","OCTOBER","TASNIM","IRNA","CMA CGM","MAERSK","HAPAG","BBC","CNN","FT","WSJ","MAREX","MSC","CMA","CGM","USD","GMT","UTC","II","III","THE","AND","OF","A","IN","ON","AT","TO","SHIP","TANKER","VESSEL"}
NAMEWORDS=r"[A-Z][A-Z0-9\.\-']+"
def _txt(h):return re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",h or "")).strip()
def _norm(n):return re.sub(r"[^A-Z0-9]","",re.sub(r"\(.*?\)","",n or "").upper())
def _vparse(name,url,lim):
    f=feedparser.parse(requests.get(url,headers=UA,timeout=20).content);out=[]
    for e in f.entries[:lim]:
        t=e.get("published_parsed") or e.get("updated_parsed")
        src=(e.get("source") or {}).get("title") or name
        title=e.get("title","").strip()
        if src and title.endswith(" - "+src): title=title[:-len(src)-3]
        out.append(dict(title=title,summary=_txt(e.get("summary",""))[:600],link=e.get("link"),source=src,ts=dt.datetime(*t[:6],tzinfo=dt.timezone.utc).isoformat() if t else None))
    return out
def extract(a):
    """Return candidate dict or None. Needs incident verb + vessel identifier + Gulf-region location. Fields not found -> 'not reported'."""
    T=a["title"];X=T+" . "+a.get("summary","")
    if not VERB.search(T): return None
    loc=next((k for k in LOC if re.search(r"\b"+re.escape(k)+r"\b",X,re.I)),None)
    if not loc: return None
    imo=re.search(r"\bIMO(?:\s*(?:No\.?|number|:))?\s*(\d{7})\b",X)
    uk=re.search(r"\bUKMTO\b[^.]{0,40}?\b(?:warning|incident|advisory|no\.?|number|#)?\s*(\d{3})(?:[-/](\d{2}))?\b",X,re.I)
    X2=X.replace(a.get("source") or "\x00"," ")
    VW=r"(?i:tanker|vessel|ship|carrier|containership|bulker|VLCC|Suezmax|Aframax|freighter|dhow)"
    names=[]
    for m in re.finditer(r"[\"“‘]([A-Z][A-Za-z0-9\-\. ]{2,30})[\"”’]",X2):
        if re.search(VW,X2[max(0,m.start()-40):m.end()+40],re.I): names.append(m.group(1).strip())
    cap=r"((?:"+NAMEWORDS+r")(?:\s+(?:NO\.\s*\d+|"+NAMEWORDS+r")){0,3})"
    for m in re.finditer(r"\b"+VW+r"s?\s+(?:named\s+|called\s+)?"+cap+r"|"+cap+r"\s*(?:\(IMO|,\s*an?\s+[\w\- ]{0,25}"+VW+r")",X2,re.I if False else 0):
        w=(m.group(1) or m.group(2) or "").strip(" .-'")
        if w and all(x.strip(".") not in STOP for x in w.split()) and len(w.replace(" ",""))>=4: names.append(w)
    for m in re.finditer(r"\b"+VW+r"\s+(?:named\s+)?((?:[A-Z][a-z]+)(?:\s+[A-Z][a-z]+){0,2})\b",X2):
        ws=[]
        for w in m.group(1).split():
            if VERB.fullmatch(w) or w in ("Hit","By","In","Off","Near","Was","Is","Says","After","Reports","Reported","Amid","As","With","At","From","Under"): break
            ws.append(w)
        nm=" ".join(ws)
        if nm and nm.split()[0] not in ("Hit","Attacked","Struck","In","Off","Near","Was","Is","Says","After","The","Of","Sails","Attack","Attacks","Strike","Strikes","Incident","Traffic","Owners","Crew","Seized","Damaged","Carrying","Bound","Heading","Sinks","Sank","Catches","Ablaze"): names.append(nm.upper())
    name=next((n for n in names if _norm(n) and _norm(n) not in STOP and not any(k.upper()==n.upper() for k in LOC)),None)
    if not (imo or uk or name): return None
    ukn=None
    if uk:
        yr=uk.group(2) or str(dt.date.today().year)[2:]
        ukn=f"{uk.group(1)}-{yr}"
    vt=next((v for k,v in VTYPES if re.search(r"\b"+re.escape(k)+r"\b",X,re.I)),"not reported")
    lat,lon=LOC[loc]
    return dict(vessel=name.upper() if name else (f"Unnamed (UKMTO {ukn})" if ukn else "Unnamed"),imo=imo.group(1) if imo else "not reported",ukmto=ukn or "not reported",
      type=vt,cargo="not reported",location=loc+" (approx., keyword)",lat=lat,lon=lon,date=(a["ts"] or "")[:10] or "not reported")
def _keys(r):
    k=set();n=_norm(r.get("vessel",""))
    if n and not n.startswith("UNNAMED"): k.add("N:"+n)
    for p in re.split(r"\s*/\s*",re.sub(r"\(.*?\)","",r.get("vessel",""))):
        if _norm(p) and not _norm(p).startswith("UNNAMED"): k.add("N:"+_norm(p))
    if re.fullmatch(r"\d{7}",str(r.get("imo",""))): k.add("I:"+r["imo"])
    for m in re.finditer(r"UKMTO\s*(\d{3})(?:-(\d{2}))?",r.get("vessel","")+" "+r.get("source","")+" "+str(r.get("ukmto",""))): k.add("U:"+m.group(1))
    if re.fullmatch(r"\d{3}-\d{2}",str(r.get("ukmto",""))): k.add("U:"+r["ukmto"][:3])
    return k
def _rep(s):s=(s or "").lower();return any(r in s for r in REPUTABLE)
def vessels():
    errs,arts=[],[]
    for q in VQ:
        try: arts+=_vparse("Google News",gnews(q).replace("when%3A2d","when%3A7d"),40)
        except Exception as e: errs.append(f"gnews '{q}': {type(e).__name__}")
    for nm,u in VFEEDS:
        try: arts+=_vparse(nm,u,40)
        except Exception as e: errs.append(f"{nm}: {type(e).__name__}")
    try: old=json.load(open(os.path.join(os.path.dirname(__file__),"data","vessels.json")))
    except Exception: old={}
    auto=[r for r in old.get("auto",[]) if r.get("date","9")>=str(dt.date.today()-dt.timedelta(days=21))]
    vkeys=[_keys(r) for r in SEED]; corro=[]
    seen=set(); rep=[]
    for a in sorted(arts,key=lambda x:x["ts"] or "",reverse=True):
        kk=re.sub(r"\W+","",a["title"].lower())[:60]
        if kk in seen: continue
        seen.add(kk); rep.append(a)
        c=extract(a)
        if not c: continue
        ks=_keys(c); s=dict(source=a["source"],title=a["title"],link=a["link"],ts=a["ts"],reputable=_rep(a["source"]))
        vi=next((i for i,vk in enumerate(vkeys) if vk&ks),None)
        if vi is not None: corro.append(dict(verified_no=vi+1,vessel=SEED[vi]["vessel"],**s)); continue
        ex=next((r for r in auto if _keys(r)&ks),None)
        if ex is None:
            ex=dict(c,sources=[],status="pending",found=dt.datetime.now(dt.timezone.utc).isoformat(),detail="Auto-extracted from headline: "+a["title"]); auto.append(ex)
        else:
            for f_ in ("imo","ukmto","type"):
                if ex.get(f_)=="not reported" and c[f_]!="not reported": ex[f_]=c[f_]
            if ex["vessel"].startswith("Unnamed") and not c["vessel"].startswith("Unnamed"): ex["vessel"]=c["vessel"]
        if a["link"] not in [x["link"] for x in ex["sources"]]: ex["sources"].append(s)
    for r in [r for r in auto if r["status"]=="pending" and not r["vessel"].startswith("Unnamed")][:8]:  # targeted corroboration search
        try:
            for a in _vparse("Google News",gnews('"'+r["vessel"].title()+'" ship OR tanker OR vessel').replace("when%3A2d","when%3A14d"),25):
                if re.search(r"\b"+re.escape(r["vessel"])+r"\b",(a["title"]+" "+a["summary"]).upper()) and VERB.search(a["title"]) and a["link"] not in [x["link"] for x in r["sources"]]:
                    r["sources"].append(dict(source=a["source"],title=a["title"],link=a["link"],ts=a["ts"],reputable=_rep(a["source"])))
        except Exception as e: errs.append(f"corroborate {r['vessel']}: {type(e).__name__}")
    for r in auto:
        srcs={x["source"].lower() for x in r["sources"] if x["reputable"]}
        r["n_sources"]=len(srcs); r["status"]="confirmed" if len(srcs)>=2 else "pending"
        r["source"]="; ".join(sorted({x["source"] for x in r["sources"]}))+" (auto)"
    auto.sort(key=lambda r:r.get("date",""),reverse=True)
    return dict(verified=SEED,auto=auto,corroborations=corro[:30],reports=[dict(title=a["title"],link=a["link"],source=a["source"],ts=a["ts"]) for a in rep[:60]],
      checked=dt.datetime.now(dt.timezone.utc).isoformat(),articles_scanned=len(rep),errors=errs,
      source="Verified table (manual, never auto-modified): UKMTO 160/164-169, CENTCOM, India MEA, Seatrade/TradeWinds/MarEx. Auto rows: extracted every 15 min from Google News RSS + gCaptain, Splash247, Maritime Executive, Seatrade, Hellenic Shipping News RSS; pending until >=2 distinct reputable outlets name the same vessel/IMO/UKMTO no. Auto positions = location keyword, approximate. UKMTO site blocks automated access.")

MACRO=[("DX-Y.NYB","DXY (ICE)",3),("GC=F","Gold $/oz",1),("^TNX","US 10Y yield %",3),("^GSPC","S&P 500",1),("^NDX","Nasdaq 100",1),("^VIX","VIX",2),("BTC-USD","Bitcoin $",0)]
def macro():
    rows=[];errs=[]
    for t,n,d in MACRO:
        try:
            h=yf.Ticker(t).history(period="1mo")["Close"].dropna()
            last,prev=float(h.iloc[-1]),float(h.iloc[-2])
            rows.append(dict(ticker=t,name=n,dec=d,last=last,chg=last-prev,pct=(last/prev-1)*100,asof=str(h.index[-1])[:16],spark=[round(float(x),4) for x in h.values],dates=[str(x)[:10] for x in h.index]))
        except Exception as e: errs.append(f"{t}: {type(e).__name__}")
    return dict(rows=rows,errors=errs,source="Yahoo Finance (delayed); spark = 1-month daily closes; ^TNX quoted in % (chg in bp)")

REGIONS=dict(lat=(-38,-8),lon=(-66,-44))
def _grid(step=2.0):
    la=[REGIONS["lat"][0]+i*step for i in range(int((REGIONS["lat"][1]-REGIONS["lat"][0])/step)+1)]
    lo=[REGIONS["lon"][0]+i*step for i in range(int((REGIONS["lon"][1]-REGIONS["lon"][0])/step)+1)]
    return la,lo
def weather(step=1.0):
    la,lo=_grid(step); pts=[(a,b) for a in la for b in lo]; P,T=[],[]
    for i in range(0,len(pts),100):
        ch=pts[i:i+100]
        for att in range(5):
            r=requests.get("https://api.open-meteo.com/v1/forecast",params=dict(latitude=",".join(str(a) for a,_ in ch),longitude=",".join(str(b) for _,b in ch),
                daily="precipitation_sum,temperature_2m_max",forecast_days=7,timezone="UTC"),timeout=60).json()
            if not (isinstance(r,dict) and r.get("error")): break
            import time; time.sleep(10*(att+1))
        else: raise RuntimeError("Open-Meteo: "+str(r.get("reason")))
        r=r if isinstance(r,list) else [r]
        for x in r:
            P.append(round(sum(v or 0 for v in x["daily"]["precipitation_sum"]),1)); tm=[v for v in x["daily"]["temperature_2m_max"] if v is not None]; T.append(round(sum(tm)/len(tm),1) if tm else None)
    return dict(lat=la,lon=lo,precip7=P,tmax7=T,days=x["daily"]["time"],source=f"Open-Meteo forecast API (best-match global models incl. GFS/ECMWF), {step}° grid")

def climatology():
    """Mean 7-day precip for the same calendar window, 2016-2025, ERA5 via Open-Meteo archive."""
    la,lo=_grid(); pts=[(a,b) for a in la for b in lo]; today=dt.date.today(); res=[0.0]*len(pts)
    y0,y1=today.year-10,today.year-1
    for i in range(0,len(pts),50):
        ch=pts[i:i+50]
        r=requests.get("https://archive-api.open-meteo.com/v1/archive",params=dict(latitude=",".join(str(a) for a,_ in ch),longitude=",".join(str(b) for _,b in ch),
          start_date=f"{y0}-01-01",end_date=f"{y1}-12-31",daily="precipitation_sum",timezone="UTC"),timeout=180).json()
        r=r if isinstance(r,list) else [r]
        for j,x in enumerate(r):
            tot=0
            for d,v in zip(x["daily"]["time"],x["daily"]["precipitation_sum"]):
                dd=dt.date.fromisoformat(d)
                try: st=dt.date(dd.year,today.month,today.day)
                except ValueError: continue
                if 0<=(dd-st).days<7: tot+=v or 0
            res[i+j]=round(tot/(y1-y0+1),1)
    return dict(clim7=res,years=f"{y0}-{y1}",date=str(today),source="ERA5 reanalysis via Open-Meteo archive API")

CRUSH_PAIRS=[("F","F"),("H","H"),("K","K"),("N","N"),("Q","Q"),("U","U"),("X","Z")]
def crush():
    """Board crush $/bu = ZM($/st)*0.022 + ZL(c/lb)*0.11 - ZS(c/bu)/100."""
    today=dt.date.today(); sets=[]
    for y in (today.year,today.year+1,today.year+2):
        for b,m in CRUSH_PAIRS:
            bm=MC.index(b)+1;
            if dt.date(y,bm,15)<today: continue
            yy=str(y)[2:]; sets.append((dt.date(y,bm,1),f"ZS{b}{yy}.CBT",f"ZM{m}{yy}.CBT",f"ZL{m}{yy}.CBT"))
    sets=sorted(sets)[:8]
    tk=sorted({t for s in sets for t in s[1:]})
    df=yf.download(tk,period="6mo",interval="1d",progress=False,auto_adjust=False,group_by="ticker")
    import pandas as pd
    rows=[];hist=None
    for d,s,m,o in sets:
        try:
            x=pd.DataFrame({"s":df[s]["Close"],"m":df[m]["Close"],"o":df[o]["Close"]}).dropna()
            if x.empty: continue
            meal=x.m*0.022; oil=x.o*0.11; c=meal+oil-x.s/100
            r=dict(set=f"{s[:5]}/{m[2:5]}",beans=float(x.s.iloc[-1]),meal=float(x.m.iloc[-1]),oil=float(x.o.iloc[-1]),
                   crush=float(c.iloc[-1]),chg=float(c.iloc[-1]-c.iloc[-2]) if len(c)>1 else None,
                   oil_share=float(oil.iloc[-1]/(oil.iloc[-1]+meal.iloc[-1])*100),asof=str(x.index[-1].date()))
            rows.append(r)
            if hist is None: hist=dict(set=r["set"],dates=[str(i.date()) for i in c.index],crush=[round(float(v),4) for v in c],oil_share=[round(float(v),2) for v in oil/(oil+meal)*100])
        except Exception: pass
    out=dict(rows=rows,hist=hist,formula="Board crush ($/bu) = meal $/short ton × 0.022 (44 lb meal/bu ÷ 2000) + oil ¢/lb × 0.11 (11 lb oil/bu ÷ 100) − beans ¢/bu ÷ 100. Oil share = oil value ÷ (oil + meal value). Pairs: Nov beans vs Dec meal/oil, other months same-month.",
             source="Yahoo Finance CBOT ZS/ZM/ZL daily (delayed)")
    if not rows: out["error"]="no matched contract sets returned"
    return out


SQ_USERS=["DeItaone","FirstSquawk"]; _XIDS={}; _XCACHE={}
def squawk():
    """X API v2 user timelines (pay-per-use X API). Free nitter/RSSHub/rss-bridge mirrors tested 14 Oct 2026: all dead or Cloudflare-blocked."""
    tok=os.getenv("X_BEARER_TOKEN","").strip()
    if not tok and os.path.exists(os.path.join(os.path.dirname(__file__),"data","squawk_sample.json")):
        return json.load(open(os.path.join(os.path.dirname(__file__),"data","squawk_sample.json")))
    if not tok: return dict(items=[],needs_key=True,error="needs X API key: set X_BEARER_TOKEN in .env (X API v2, pay-per-use)",source="X API v2")
    H={"Authorization":"Bearer "+tok,"User-Agent":"commodash"}; errs=[]
    if len(_XIDS)<len(SQ_USERS):
        r=requests.get("https://api.x.com/2/users/by",params={"usernames":",".join(SQ_USERS)},headers=H,timeout=20); r.raise_for_status()
        for u in r.json().get("data",[]): _XIDS[u["username"]]=u["id"]
    for u,uid in _XIDS.items():
        p={"max_results":20,"tweet.fields":"created_at","exclude":"retweets,replies"}
        old=_XCACHE.get(u,[])
        if old: p["since_id"]=old[0]["id"]
        try:
            r=requests.get(f"https://api.x.com/2/users/{uid}/tweets",params=p,headers=H,timeout=20)
            if r.status_code!=200: errs.append(f"@{u}: HTTP {r.status_code} {r.text[:120]}"); continue
            new=[dict(id=t["id"],user=u,text=t["text"],ts=t.get("created_at"),link=f"https://x.com/{u}/status/{t['id']}") for t in r.json().get("data",[])]
            _XCACHE[u]=(new+old)[:60]
        except Exception as e: errs.append(f"@{u}: {type(e).__name__}")
    items=sorted([t for v in _XCACHE.values() for t in v],key=lambda t:t["ts"] or "",reverse=True)[:100]
    return dict(items=items,errors=errs,source="X API v2 user timelines @"+", @".join(SQ_USERS))
