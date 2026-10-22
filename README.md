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

## Step by step setup
1. Sign in at github.com as `gerardomoscatelli` and open https://github.com/new
2. Repository name: `commotrading` — use exactly this name when you create the new repository (after deleting the old one), because the page address below (gerardomoscatelli.github.io/commotrading) is built from it. Visibility **Public** (free Pages + unlimited Actions minutes need a public repo). Don't add a README. Click **Create repository**.
3. Upload the files. Unzip `commodash_github_2026-10-22.zip` and upload the *contents* of the `commodash_github` folder (not the folder itself):
   - **Website:** on the repo page click **Add file → Upload files**, drag in `build.py`, `sources.py`, `maps.py`, `requirements.txt`, `README.md`, `.gitignore` and the `templates` and `data` folders, then **Commit changes**.
     Drag-and-drop usually **skips hidden folders** such as `.github`, so create the workflow by hand: **Add file → Create new file**, type the name `.github/workflows/update.yml` (typing the `/` creates the folders), paste the full contents of `.github/workflows/update.yml` from the zip, then **Commit changes**.
   - **Or with git** (from inside the unzipped `commodash_github` folder):
     ```
     git init -b main
     git add .
     git commit -m "initial"
     git remote add origin https://github.com/gerardomoscatelli/commotrading.git
     git push -u origin main
     ```
     GitHub Desktop also works: File → Add local repository → choose the folder → Publish (untick "Keep this code private").
4. **Settings → Pages → Build and deployment → Source: GitHub Actions.**
5. **Settings → Actions → General → Workflow permissions: "Read and write permissions"** → Save.
6. **Actions** tab → (click "I understand… enable workflows" if asked) → **Update dashboard** → **Run workflow**. The first run takes ~3–5 min (installs Python packages and downloads map shapes); later runs are faster thanks to caching.
7. Open https://gerardomoscatelli.github.io/commotrading/ . After that it updates by itself.

Check runs in the Actions tab; a red run usually means one install/deploy step failed — open it to see the log. If a single data source fails, the run still succeeds and that panel keeps its previous data.

## Limits
- GitHub schedules are best-effort: runs often start 5–20 min late and can be skipped at busy times, so data is typically 15–30 min old on top of the Yahoo delay.
- GitHub disables scheduled workflows after 60 days with no repository activity; the bot's data commits normally count, but if it stops, re-enable it in the Actions tab.
- The page and the repo are **public**: anyone with the address can see them.
- Yahoo Finance data is unofficial and delayed (~10–20 min / last settle); RSS feeds are third-party. For personal use only, not official quotes. No ICE/Euronext data, no Squawk.
- The chart popup only works for symbols saved in the last build (all contracts shown on the page + macro + EUR/USD).
- GDELT rate-limits shared IPs; when it refuses, the energy/war window still works on its RSS feeds.
- Every run adds a small "data: update" commit to the repo (state persistence). This is normal.

## Run locally (optional)
```
pip install -r requirements.txt
python build.py
cd site && python -m http.server 8000   # open http://localhost:8000
```
