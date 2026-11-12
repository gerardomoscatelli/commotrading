"""Official overnight reference rates used for EUR/USD forwards: SOFR (NY Fed) and €STR (ECB). Public, no key."""
import requests

def get_reference_rates():
    out = {}
    try:
        t = requests.get("https://data-api.ecb.europa.eu/service/data/EST/B.EU000A2X2A25.WT?lastNObservations=1&format=csvdata", timeout=20).text.strip().splitlines()
        hdr = t[0].split(","); v = t[-1].split(","); out["estr"] = float(v[hdr.index("OBS_VALUE")]); out["estr_date"] = v[hdr.index("TIME_PERIOD")]
    except Exception as e: out["estr_err"] = str(e)
    try:
        j = requests.get("https://markets.newyorkfed.org/api/rates/secured/sofr/last/1.json", timeout=20).json()["refRates"][0]
        out["sofr"] = j["percentRate"]; out["sofr_date"] = j["effectiveDate"]
    except Exception as e: out["sofr_err"] = str(e)
    return out
