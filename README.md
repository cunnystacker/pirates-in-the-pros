# Pirates in the Pros (v1)
Independent fan site tracking every former ECU baseball player in pro ball. Not affiliated with ECU.

## Layout
- `data/roster_seed.json` – MLB Stats API player IDs to track (+ ECU years, sources, notes). Edit to add/remove players.
- `data/manual_players.json` – hand-kept players the API doesn't cover (undrafted not yet assigned, indy, overseas), each with sources.
- `data/draft_ecu.json`, `data/api_discovered.json` – discovery outputs (draft picks 2008-2026 from ECU; 2026 roster scan by education).
- `scripts/discover_roster.py [season]` – scans all ~230 affiliated rosters for "East Carolina" in player education. Run monthly / in spring to find new ECU pros, then add IDs to the seed.
- `scripts/pipeline.py [--season YYYY]` – nightly: team/level, season stats, game logs, transactions, MLB/AAA expected stats + sabermetrics -> `data/players.json`.
- `scripts/build_site.py` – static HTML into `site/`.
- `scripts/screenshots.py` – Playwright screenshots (needs `.venv` with playwright).
- `run_nightly.sh` – pipeline + build. During the off-season it uses the current year; set `SEASON=2026` to keep showing 2026 lines until 2027 games start.

Newsletter: set `NEWSLETTER_ACTION` in `scripts/build_site.py` to the provider's form endpoint.
