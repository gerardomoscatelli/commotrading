# Energy & Ags Commodities Trading — GitHub Pages version

Static version of the dashboard. A scheduled GitHub Actions job runs `build.py` about every 15 minutes:
it fetches every data source once (Yahoo Finance futures/FX/macro, SOFR/€STR, RSS + Google News RSS,
GDELT, vessel-incident extractor, Open-Meteo weather + cartopy maps, climatology), writes static files
into `site/` and publishes them to GitHub Pages. The page re-reads the data every 5 minutes and shows
when the data was built (Geneva time).

Page address: **https://gerardomoscatelli.github.io/commotrading/**

## Files
- `build.py` – runs all jobs once, writes `site/` (index.html, data/*.json, maps/*.png, hist/*.json for the chart popup)
- `sources.py`, `maps.py` – data adapters and weather-map rendering (same as the local app)
- `templates/index.html` – the page (reads `data/…json`, `maps/…png`, `hist/…json` with relative paths)
- `data/` – saved state between runs (last good JSON of every panel, maps). The workflow commits it back to the repo after each run, so the vessel list and the daily climatology are kept, and a source that fails keeps showing its previous data with an error note.
- `.github/workflows/update.yml` – the schedule (every 15 min), manual "Run workflow", and run on every code push
- `requirements.txt`

## Limits
- GitHub schedules are best-effort: runs often start 5–20 min late and can be skipped at busy times, so data is typically 15–30 min old on top of the Yahoo delay.
- GitHub disables scheduled workflows after 60 days with no repository activity; the bot's data commits normally count, but if it stops, re-enable it in the Actions tab.
- The page and the repo are **public**: anyone with the address can see them.
- Yahoo Finance data is unofficial and delayed (~10–20 min / last settle); RSS feeds are third-party. For personal use only, not official quotes. No ICE/Euronext data, no Squawk.
- The chart popup only works for symbols saved in the last build (all contracts shown on the page + macro + EUR/USD).
- GDELT rate-limits shared IPs; when it refuses, the energy/war window still works on its RSS feeds.
- Every run adds a small "data: update" commit to the repo (state persistence). This is normal.

```
