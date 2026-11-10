# MedCommodities — Energy & Ags Commodities Dashboard

A static, self-updating market dashboard for grains, oilseeds, energy and macro, published on GitHub Pages.

**Live page:** https://gerardomoscatelli.github.io/commotrading/

A scheduled GitHub Actions job runs `build.py` about every 15 minutes. It fetches each data source once, writes static files into `site/` and publishes them to GitHub Pages. The page reloads its data every 5 minutes and shows when it was last built (Geneva time).

## What it shows
- CBOT grains and oilseeds futures curves (corn, wheat, KC wheat, soybeans, meal, oil) with soybean crush and the SBO–palm spread
- Energy: Brent, WTI, heating oil, RBOB, Henry Hub and TTF gas, with crack spreads
- Macro snapshot: DXY, gold, silver, US 10Y (in points), equity indices, VIX, EUR/USD, SOFR and €STR
- Malaysian palm oil (CME USD CPO)
- Market and agricultural news from RSS and Google News, plus GDELT event coverage
- Strait of Hormuz / Gulf vessel incident tracker (verified incidents, with unverified claims shown separately)
- South America weather: Open-Meteo forecasts, anomaly maps and climatology, with a Windy live embed
- Click any contract for a history chart popup

## Repository layout
- `build.py`: runs every job once and writes `site/` (`index.html`, `data/*.json`, `maps/*.png`, `hist/*.json`)
- `sources.py`: data adapters (prices, macro, news, vessel incidents, weather)
- `maps.py`: weather map rendering with cartopy
- `templates/index.html`: the page template
- `assets/`: logo and icons
- `data/`: saved state between runs. The workflow commits it back after each run, so history is kept and a failing source keeps showing its last good data with an error note.
- `.github/workflows/update.yml`: the schedule (every 15 minutes), manual runs and runs on every push
- `requirements.txt`: Python dependencies

## Notes and limits
- Market data comes from free public sources, may be delayed, and isn't official exchange data. News comes from third-party feeds.
- GitHub scheduled runs are best-effort and can start late or be skipped at busy times.
- Each run adds a small `data: update` commit; this is how state is kept between runs.
- The history popup only covers symbols saved in the latest build.

## Disclaimer
For information only. Nothing here is investment advice or an offer to buy or sell any commodity or financial instrument.

© MedCommodities
