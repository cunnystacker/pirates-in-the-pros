"""Scan every affiliated MLB/MiLB 2026 roster for players whose college is East Carolina.
Writes data/api_discovered.json. Slow-ish (~250 teams); run occasionally, not nightly."""
import json, urllib.request, concurrent.futures as cf, sys
API="https://statsapi.mlb.com/api/v1"
SEASON=int(sys.argv[1]) if len(sys.argv)>1 else 2026
def get(u):
    return json.load(urllib.request.urlopen(u,timeout=60))
teams=get(f"{API}/teams?sportIds=1,11,12,13,14,16&season={SEASON}")["teams"]
def scan(t):
    hits=[]
    for rt in ("fullSeason","40Man"):
        try:
            r=get(f"{API}/teams/{t['id']}/roster?rosterType={rt}&season={SEASON}&hydrate=person(education)")
        except Exception as e:
            continue
        for e in r.get("roster",[]):
            p=e["person"]
            cols=[c.get("name","") for c in (p.get("education") or {}).get("colleges",[])]
            if any("east carolina" in c.lower() for c in cols):
                hits.append(dict(id=p["id"],name=p["fullName"],team=t["name"],sport=t.get("sport",{}).get("id"),rosterType=rt))
    return hits
out={}
with cf.ThreadPoolExecutor(12) as ex:
    for h in ex.map(scan,teams):
        for x in h: out.setdefault(x["id"],x)
print(len(teams),"teams scanned;",len(out),"ECU players")
for x in out.values(): print(x)
json.dump(list(out.values()),open("data/api_discovered.json","w"),indent=1)
