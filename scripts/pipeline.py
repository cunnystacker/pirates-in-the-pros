#!/usr/bin/env python3
"""Nightly data refresh for Pirates in the Pros.
Reads data/roster_seed.json (+ data/manual_players.json), pulls from the free MLB Stats API,
writes data/players.json. Safe to rerun any time. Usage: python3 scripts/pipeline.py [--season 2026]"""
import json, os, sys, time, datetime as dt, urllib.request, urllib.error, concurrent.futures as cf, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://statsapi.mlb.com/api/v1"
SEASON = int(sys.argv[sys.argv.index("--season") + 1]) if "--season" in sys.argv else dt.date.today().year
SPORTS = {1: ("MLB", 6), 11: ("Triple-A", 5), 12: ("Double-A", 4), 13: ("High-A", 3), 14: ("Single-A", 2), 16: ("Rookie", 1)}
SPORT_IDS = ",".join(map(str, SPORTS))
STATCAST_SPORTS = {1, 11}  # Statcast-type data only exists for MLB and Triple-A

def get(path, tries=3):
    url = path if path.startswith("http") else API + path
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except (urllib.error.URLError, TimeoutError) as e:
            if i == tries - 1:
                print("WARN", url, e, file=sys.stderr); return {}
            time.sleep(2 * (i + 1))

_team_cache = {}
def team_info(tid):
    if not tid: return {}
    if tid not in _team_cache:
        t = (get(f"/teams/{tid}?hydrate=parentOrg") .get("teams") or [{}])[0]
        _team_cache[tid] = t
    return _team_cache[tid]

def org_name(t):
    if not t: return None
    if t.get("sport", {}).get("id") == 1: return t.get("name")
    return t.get("parentOrgName") or (team_info(t.get("parentOrgId")).get("name") if t.get("parentOrgId") else None)

def classify(desc):
    d = desc.lower()
    if "number" in d and "changed" in d: return None
    if "released" in d: return "Released"
    if "elected free agency" in d or "free agency" in d: return "Free agent"
    if "retired" in d: return "Retired"
    if "recalled" in d or "selected the contract" in d or "purchased the contract" in d: return "Call-up"
    if "optioned" in d: return "Optioned"
    if "traded" in d or "acquired" in d or "claimed" in d: return "Trade/claim"
    if re.search(r"\bsigned\b", d): return "Signed"
    if "injured list" in d or "development list" in d:
        return "Activated" if "activated" in d else "Injured/Dev list"
    if "activated" in d: return "Activated"
    if "rehab" in d: return "Rehab"
    if "assigned" in d: return "Assigned"
    if "debut" in d: return "Debut"
    return "Other"

LEVEL_BY_TEAMNAME = {}
def level_of_team(tid):
    t = team_info(tid)
    sid = t.get("sport", {}).get("id")
    return sid

def build_player(seed):
    pid = seed["id"]
    p = (get(f"/people/{pid}?hydrate=currentTeam,education,draft").get("people") or [{}])[0]
    pos = p.get("primaryPosition", {}).get("abbreviation", "")
    is_pitcher = pos in ("P", "RHP", "LHP") or p.get("primaryPosition", {}).get("type") == "Pitcher"
    if pos == "TWP": is_pitcher = False
    group = "pitching" if is_pitcher else "hitting"
    ct = p.get("currentTeam") or {}
    ctfull = team_info(ct.get("id")) if ct.get("id") else {}
    cur_sport = ctfull.get("sport", {}).get("id")

    # Year-by-year across MLB + MiLB -> career path and season line
    yby = get(f"/people/{pid}/stats?stats=yearByYear&group={group}&leagueListId=mlb_milb")
    splits = (yby.get("stats") or [{}])[0].get("splits", [])
    path, season_rows, milb_agg = [], [], None
    for s in splits:
        sid = s.get("sport", {}).get("id")
        if sid in SPORTS and not s.get("team"): continue  # multi-team aggregate row within one level
        if sid not in SPORTS:
            if str(s.get("season")) == str(SEASON) and not s.get("team"): milb_agg = s["stat"]
            continue
        row = dict(season=int(s["season"]), team=s.get("team", {}).get("name"), team_id=s.get("team", {}).get("id"),
                   level=SPORTS[sid][0], rank=SPORTS[sid][1], league=s.get("league", {}).get("name"), stat=s["stat"])
        path.append(row)
        if row["season"] == SEASON: season_rows.append(row)
    mlb_rows = [r for r in season_rows if r["level"] == "MLB"]
    milb_rows = [r for r in season_rows if r["level"] != "MLB"]
    mlb_line = mlb_rows[0]["stat"] if len(mlb_rows) == 1 else None
    if len(mlb_rows) > 1:  # traded mid-season: ask the API for the combined MLB line
        agg = get(f"/people/{pid}/stats?stats=season&group={group}&season={SEASON}&sportId=1")
        sp = (agg.get("stats") or [{}])[0].get("splits", [])
        mlb_line = sp[0]["stat"] if sp else None
    milb_line = milb_rows[0]["stat"] if len(milb_rows) == 1 else (milb_agg if milb_rows else None)
    season_total = mlb_line or milb_line
    season_line_label = "MLB" if mlb_line else ("MiLB" if milb_line else None)

    # Highest level reached ever / in season
    highest = max(path, key=lambda r: r["rank"])["level"] if path else None
    season_levels = sorted({r["level"] for r in season_rows}, key=lambda l: -[v for v in SPORTS.values() if v[0] == l][0][1])

    # Game logs (last 10 regular-season games at the levels played this season)
    logs = []
    for sid in {s for s, v in SPORTS.items() if v[0] in season_levels}:
        gl = get(f"/people/{pid}/stats?stats=gameLog&group={group}&season={SEASON}&sportId={sid}")
        for g in (gl.get("stats") or [{}])[0].get("splits", []):
            st = g["stat"]
            logs.append(dict(date=g.get("date"), team=g.get("team", {}).get("name"), opp=g.get("opponent", {}).get("name"),
                             home=g.get("isHome"), level=SPORTS[sid][0], summary=st.get("summary"),
                             line={k: st.get(k) for k in (["inningsPitched","hits","runs","earnedRuns","baseOnBalls","strikeOuts","homeRuns","pitchesThrown","decisions"] if is_pitcher else ["atBats","hits","doubles","triples","homeRuns","rbi","baseOnBalls","strikeOuts","stolenBases","runs"])}))
    logs.sort(key=lambda x: x["date"] or "", reverse=True)

    # Statcast-type / advanced fields only for MLB and Triple-A
    statcast = {}
    for sid in STATCAST_SPORTS:
        if SPORTS[sid][0] not in season_levels: continue
        sc = get(f"/people/{pid}/stats?stats=expectedStatistics,sabermetrics&group={group}&season={SEASON}&sportId={sid}")
        for blk in sc.get("stats", []):
            for sp in blk.get("splits", []):
                statcast.setdefault(SPORTS[sid][0], {}).update({f"{blk['type']['displayName']}.{k}": v for k, v in sp["stat"].items()})

    # Transactions (full history; feed uses recent)
    txs = []
    for t in get(f"/transactions?playerId={pid}&startDate=2008-01-01&endDate={dt.date.today().isoformat()}").get("transactions", []):
        kind = classify(t.get("description", ""))
        if not kind: continue
        tt, ft = t.get("toTeam", {}), t.get("fromTeam", {})
        if kind == "Assigned" and tt.get("id") and ft.get("id"):
            a, b = level_of_team(ft["id"]), level_of_team(tt["id"])
            if a in SPORTS and b in SPORTS and SPORTS[a][1] != SPORTS[b][1]:
                kind = "Promotion" if SPORTS[b][1] > SPORTS[a][1] else "Reassigned down"
        txs.append(dict(date=t.get("date"), kind=kind, desc=t.get("description"), typeDesc=t.get("typeDesc")))
    txs.sort(key=lambda x: x["date"] or "")

    # Status
    status, status_note = "active", None
    rel = [t for t in txs if t["kind"] in ("Released", "Free agent", "Retired", "Signed", "Trade/claim")]
    last = rel[-1] if rel else None
    if last and last["kind"] in ("Released", "Free agent", "Retired"):
        status = {"Released": "released", "Free agent": "free agent", "Retired": "retired"}[last["kind"]]
        status_note = f"{last['desc']} ({last['date']})"
    elif not p.get("active", True):
        status = "inactive"
    uncertain = []
    if status == "active" and not season_rows: uncertain.append(f"No {SEASON} stats in MLB/MiLB; may be injured or not yet assigned.")
    if seed.get("note") and "not verified" in seed["note"]: uncertain.append(seed["note"])
    il = [t for t in txs if "injured list" in (t["desc"] or "").lower()]
    if status == "active" and il and "activated" not in il[-1]["desc"].lower() and il[-1]["date"] >= f"{SEASON}-01-01":
        status_note = f"Last IL move: {il[-1]['desc']} ({il[-1]['date']})"

    level_now = SPORTS[cur_sport][0] if cur_sport in SPORTS else (season_levels[0] if season_levels else None)
    drafts = [dict(year=d.get("year"), round=d.get("pickRound"), pick=d.get("pickNumber"), team=d.get("team", {}).get("name"),
                   school=d.get("school", {}).get("name"), bonus=d.get("signingBonus")) for d in p.get("drafts", [])]
    return dict(
        id=pid, slug=p.get("nameSlug") or str(pid), name=p.get("fullName"), first=p.get("useName") or p.get("firstName"), last=p.get("lastName"),
        position=pos, type="Pitcher" if is_pitcher else "Hitter", bats=p.get("batSide", {}).get("code"), throws=p.get("pitchHand", {}).get("code"),
        age=p.get("currentAge"), hometown=", ".join(x for x in [p.get("birthCity"), p.get("birthStateProvince")] if x),
        mlb_debut=p.get("mlbDebutDate"), team=ct.get("name"), team_id=ct.get("id"), org=org_name(ctfull) if ctfull else None,
        level=level_now, highest_level=highest, season_levels=season_levels, status=status, status_note=status_note,
        uncertain=uncertain, note=seed.get("note"), ecu_years=seed.get("ecu_years"), sources=seed.get("sources", []),
        drafts=drafts, season=SEASON, season_stats=season_total, season_line_label=season_line_label, mlb_line=mlb_line, milb_line=milb_line, season_by_team=season_rows, career_path=path,
        game_logs=logs[:10], statcast=statcast, transactions=txs, source="MLB Stats API", manual=False)

def main():
    seed = json.load(open(os.path.join(ROOT, "data/roster_seed.json")))["players"]
    manual = json.load(open(os.path.join(ROOT, "data/manual_players.json")))["players"]
    with cf.ThreadPoolExecutor(8) as ex:
        players = list(ex.map(build_player, seed))
    for m in manual:
        players.append(dict(m, id=None, slug=re.sub(r"[^a-z0-9]+", "-", m["name"].lower()).strip("-"), type="Pitcher" if m.get("position", "").endswith("HP") else "Hitter",
                            highest_level=m.get("level"), season_levels=[], status_note=None, season_line_label=None, mlb_line=None, milb_line=None, uncertain=[m["note"]] if m.get("uncertain") else [], season=SEASON,
                            season_stats=None, season_by_team=[], career_path=[], game_logs=[], statcast={}, transactions=[], drafts=[], manual=True, source="Hand-kept"))
    # Recent moves feed: last 180 days of meaningful transactions across all players
    cutoff = (dt.date.today() - dt.timedelta(days=180)).isoformat()
    feed = [dict(t, player=p["name"], slug=p["slug"]) for p in players for t in p.get("transactions", [])
            if (t["date"] or "") >= cutoff and t["kind"] not in ("Other",)]
    seen=set(); feed=[f for f in feed if not ((f["player"],f["date"],f["desc"]) in seen or seen.add((f["player"],f["date"],f["desc"])))]
    feed.sort(key=lambda x: x["date"], reverse=True)
    out = dict(generated_at=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), season=SEASON, players=players, recent_moves=feed[:60])
    path = os.path.join(ROOT, "data/players.json")
    tmp = path + ".tmp"
    json.dump(out, open(tmp, "w"), indent=1); os.replace(tmp, path)
    print(f"wrote {path}: {len(players)} players, {len(feed)} moves in last 180 days")

if __name__ == "__main__":
    main()
