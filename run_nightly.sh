#!/usr/bin/env bash
# Nightly refresh: pull fresh data, rebuild the static site. Rerunnable any time.
set -euo pipefail
cd "$(dirname "$0")"
python3 scripts/pipeline.py --season "${SEASON:-$(date +%Y)}"
python3 scripts/build_site.py
