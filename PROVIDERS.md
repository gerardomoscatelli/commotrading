# Market-data providers

All prices (futures curves, history, intraday bars, quotes, contract details, spot metals, SOFR/€STR) are fetched in one place: the `providers/` package. Nothing else in the app talks to a data vendor. `server.py`, `sources.py`, `chartdata.py` and `build.py` call only `providers.get_provider()` (and `providers.get_rates()` for SOFR/€STR).

## Layout
| File | Role |
|---|---|
| `providers/base.py` | Abstract interface `PriceProvider`: `get_history(sym, tf, start, end, src)`, `get_intraday`, `get_quote`, `get_contract_info`, `get_volume_oi`, `get_history_batch` |
| `providers/symbols.py` | Canonical symbol map: internal id → per-vendor code, plus units, currency, exchange and decimals |
| `providers/contracts.py` | Expiry rules and calendar helpers (used when a vendor reports no expiry) |
| `providers/yahoo_adapter.py` | Default free feed (the only module that imports `yfinance`) |
| `providers/goldapi_spot.py` | Silver/gold spot quotes (gold-api.com) |
| `providers/reference_rates.py` | SOFR (NY Fed) and €STR (ECB) |
| `providers/template_adapter.py` | Documented stub for a paid vendor |
| `providers/__init__.py` | `get_provider()` factory: config, fallback chain, in-process TTL cache |

## Symbols
Internal ids are vendor-neutral and are what the browser and the API use:
- futures contract `ZSF27`, `ZCH27`, `BZF27`, `6EZ26`, `TTFF27`
- continuous front month `ZS1!`, `CL1!`, `GC1!`, `SI1!`, `CPO1!`
- instruments `DXY`, `US10Y`, `SPX`, `NDX`, `VIX`, `BTCUSD`, `EURUSD`, `XAGUSD` (spot)

The API also accepts the old vendor-style codes (e.g. `ZSF27.CBT`, `GC=F`), so old links keep working.

## Choosing a provider
Environment variables override `providers.json` (next to `server.py`; see `providers.example.json`):
```
COMMODASH_PROVIDER=yahoo          # primary (default)
COMMODASH_FALLBACK=               # comma list tried when the primary errors or has no data
COMMODASH_SPOT=goldapi            # spot-metal quote adapter at the end of the chain ("" disables)
PRICE_SECS=180                    # daily-history cache TTL (also the dashboard refresh)
```
On Windows, either run `set COMMODASH_PROVIDER=...` in the console before starting `run.bat`, or use `providers.json`:
```json
{"provider": "databento", "fallback": ["yahoo"], "spot": "goldapi", "ttl": {"quote": 60, "intraday": 60, "daily": 180}}
```
If the primary cannot start (e.g. its API key is missing), the factory logs a warning and uses the default feed.

## Adding a professional vendor (Barchart, CQG, Databento, LSEG/Refinitiv, ICE)
1. Copy `providers/template_adapter.py` to `providers/<vendor>_adapter.py` and set `name = "<vendor>"`.
2. Add the vendor's symbol formats to `VENDOR` in `providers/symbols.py`.
3. Implement `get_history`, `get_intraday` and `get_quote` (return DataFrames with `Open, High, Low, Close, Volume`); override `get_history_batch` if the vendor has a bulk endpoint.
4. Register the class in `_registry()` in `providers/__init__.py`.
5. Put the API key in an environment variable (never in code or git) and set `COMMODASH_PROVIDER=<vendor>`, optionally `COMMODASH_FALLBACK=yahoo`.

Check which chain is active at `GET /api/provider` (local server). In the static build, set the same variables as repository secrets/variables in the workflow.
