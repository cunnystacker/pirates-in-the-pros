#!/usr/bin/env python3
"""Builds the static site in site/ from data/players.json. Usage: python3 scripts/build_site.py"""
import json, os, html, shutil, datetime as dt
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "site")
D = json.load(open(os.path.join(ROOT, "data/players.json")))
E = lambda x: html.escape(str(x)) if x is not None else ""
LEVEL_ORDER = ["MLB", "Triple-A", "Double-A", "High-A", "Single-A", "Rookie", "Independent", "Signed (no assignment)"]
SITE = "Pirates in the Pros"
NEWSLETTER_ACTION = "https://app.kit.com/forms/10117322/subscriptions"  # Kit form "Monday Box Score signup"
STATUS_LABEL = {"active": "Active", "released": "Released", "free agent": "Free agent", "retired": "Retired", "inactive": "Inactive", "unknown": "Unconfirmed"}

def fmt_date(s):
    try: return dt.date.fromisoformat(s[:10]).strftime("%b %-d, %Y")
    except Exception: return s or ""

def key_line(p):
    s = p.get("season_stats") or {}
    if not s: return "—"
    if p["type"] == "Pitcher":
        w, l = s.get("wins"), s.get("losses")
        return f"{w}-{l}, {s.get('era')} ERA, {s.get('inningsPitched')} IP, {s.get('strikeOuts')} K"
    return f"{s.get('avg')}/{s.get('obp')}/{s.get('slg')}, {s.get('homeRuns')} HR, {s.get('rbi')} RBI"

def page(title, body, depth=0, desc=""):
    up = "../" * depth
    gen = fmt_date(D["generated_at"])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc or 'Every former ECU Pirates baseball player in pro ball: stats, moves and career paths, updated nightly.')}">
<link rel="stylesheet" href="{up}assets/style.css"></head><body>
<header class="top"><div class="wrap"><a class="brand" href="{up}index.html"><span class="mark">⚓</span> {SITE}</a>
<nav><a href="{up}index.html#roster">Roster</a><a href="{up}index.html#moves">Moves</a><a href="{up}index.html#newsletter">Newsletter</a></nav></div></header>
<main class="wrap">{body}</main>
<footer><div class="wrap">
<p><strong>{SITE}</strong> is an independent fan site. Not affiliated with, endorsed by, or sponsored by East Carolina University or ECU Athletics.</p>
<p>Stats from the MLB Stats API, refreshed nightly (last update {gen}). Daily shoutouts? Follow <a href="https://x.com/PR927FM" rel="noopener">Pirate Radio 92.7's #PiratesInThePros</a>.</p>
</div></footer>
<script src="{up}assets/app.js"></script></body></html>"""

def newsletter():
    return f"""<section id="newsletter" class="card news"><div><h2>The Monday Box Score</h2>
<p>One short email a week: how every Pirate in pro ball did, who moved up, and off-season moves. Free.</p></div>
<form action="{NEWSLETTER_ACTION}" method="post" onsubmit="return pipSignup(this)">
<label class="sr" for="em">Email</label><input id="em" type="email" name="email_address" placeholder="you@example.com" required>
<button type="submit">Sign me up</button><p class="formmsg" aria-live="polite"></p></form></section>"""

def badge(p):
    st = p["status"]
    return f'<span class="badge st-{st.replace(" ","-")}">{E(STATUS_LABEL.get(st, st))}</span>'

def home():
    players = sorted(D["players"], key=lambda p: (p["status"] != "active", LEVEL_ORDER.index(p["level"]) if p["level"] in LEVEL_ORDER else 99, p["last"] if p.get("last") else p["name"].split()[-1]))
    active = [p for p in players if p["status"] == "active"]
    counts = {l: sum(1 for p in active if p["level"] == l) for l in LEVEL_ORDER}
    chips = "".join(f'<div class="stat"><b>{n}</b><span>{l}</span></div>' for l, n in counts.items() if n)
    rows = []
    for p in players:
        s = p.get("season_stats") or {}
        sortval = (s.get("ops") if p["type"] == "Hitter" else s.get("era")) or ""
        lvl_rank = LEVEL_ORDER.index(p["level"]) if p["level"] in LEVEL_ORDER else 99
        rows.append(f"""<tr data-level="{E(p['level'])}" data-type="{p['type']}" data-status="{E(p['status'])}">
<td data-v="{E(p['name'])}"><a href="players/{p['slug']}.html">{E(p['name'])}</a> <span class="pos">{E(p['position'])}</span>{' <span class="flag" title="Unverified details">?</span>' if p.get('uncertain') else ''}</td>
<td data-v="{lvl_rank}"><span class="lvl l{lvl_rank}">{E(p['level'] or '—')}</span></td>
<td data-v="{E(p['team'])}">{E(p['team'] or '—')}<div class="sub">{E(p.get('org') if p.get('org') != p.get('team') else '')}</div></td>
<td data-v="{E(sortval)}">{E(key_line(p))}{f' <span class="sub">({p["season_line_label"]})</span>' if p.get('season_line_label') else ''}</td>
<td data-v="{E(p['status'])}">{badge(p)}</td></tr>""")
    moves = feed_html(D["recent_moves"][:25])
    body = f"""<section class="hero"><h1>Every ECU Pirate in pro baseball, in one place.</h1>
<p>Stats, call-ups, promotions and off-season moves for former East Carolina players, from the complex leagues to the majors. Updated every night.</p>
<div class="stats">{chips}<div class="stat total"><b>{len(active)}</b><span>Active pros</span></div></div></section>
<section id="roster" class="card"><div class="tablehead"><h2>{D['season']} roster</h2>
<div class="filters" role="group" aria-label="Filters">
<select id="fLevel" aria-label="Level"><option value="">All levels</option>{''.join(f'<option>{l}</option>' for l in LEVEL_ORDER)}</select>
<select id="fType" aria-label="Hitter or pitcher"><option value="">Hitters &amp; pitchers</option><option value="Hitter">Hitters</option><option value="Pitcher">Pitchers</option></select>
<select id="fStatus" aria-label="Status"><option value="active">Active</option><option value="">All statuses</option><option value="released">Released / FA</option></select>
</div></div>
<div class="tablewrap"><table id="roster-table"><thead><tr><th data-sort="0">Player</th><th data-sort="1" data-num>Level</th><th data-sort="2">Team</th><th data-sort="3">{D['season']} line</th><th data-sort="4">Status</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>
<p class="note">Hitters: AVG/OBP/SLG. Pitchers: W-L, ERA, IP, K. "MiLB" lines combine all minor-league stops. <span class="flag">?</span> = details still being verified.</p></section>
<section id="moves" class="card"><h2>Recent moves</h2>{moves}</section>
{newsletter()}"""
    return page(f"{SITE}: every former ECU baseball player in pro ball", body)

KIND_CLASS = {"Promotion": "up", "Call-up": "up", "Debut": "up", "Released": "down", "Free agent": "down", "Optioned": "down", "Reassigned down": "down", "Injured/Dev list": "il", "Signed": "new", "Trade/claim": "new"}
def feed_html(items, show_player=True, depth=0):
    if not items: return '<p class="note">No moves yet.</p>'
    up = "../" * depth
    li = "".join(f'<li><time>{fmt_date(m["date"])}</time><span class="kind k-{KIND_CLASS.get(m["kind"],"other")}">{E(m["kind"])}</span>'
                 f'<span class="desc">{f"""<a href="{up}players/{m["slug"]}.html">{E(m["player"])}</a>: """ if show_player else ""}{E(m["desc"])}</span></li>' for m in items)
    return f'<ul class="feed">{li}</ul>'

def stat_table(rows, cols, labels):
    th = "".join(f"<th>{l}</th>" for l in labels)
    trs = "".join("<tr>" + "".join(f"<td>{E(r.get(c, ''))}</td>" for c in cols) + "</tr>" for r in rows)
    return f'<div class="tablewrap"><table class="mini"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>'

HIT = (["gamesPlayed","atBats","hits","doubles","homeRuns","rbi","stolenBases","baseOnBalls","strikeOuts","avg","obp","slg","ops"], ["G","AB","H","2B","HR","RBI","SB","BB","K","AVG","OBP","SLG","OPS"])
PIT = (["gamesPlayed","gamesStarted","wins","losses","saves","inningsPitched","strikeOuts","baseOnBalls","era","whip"], ["G","GS","W","L","SV","IP","K","BB","ERA","WHIP"])

def player_page(p):
    cols, labels = PIT if p["type"] == "Pitcher" else HIT
    # career path: ECU -> each level (first appearance)
    steps = [dict(level="ECU", team="East Carolina Pirates", when=p.get("ecu_years") or (f"Drafted {p['drafts'][-1]['year']}" if p.get("drafts") else "College"))]
    if p.get("drafts"):
        d = [x for x in p["drafts"] if "east carolina" in (x.get("school") or "").lower()] or p["drafts"]
        d = d[-1]
        steps.append(dict(level="Draft", team=d["team"], when=f"{d['year']} · Round {d['round']}, pick {d['pick']}"))
    seen = {}
    for r in sorted(p["career_path"], key=lambda r: (r["season"], r["rank"])):
        k = r["level"]
        if k not in seen:
            seen[k] = dict(level=k, team=r["team"], when=str(r["season"]))
        elif r["team"] not in seen[k]["team"] and len(seen[k]["team"]) < 80:
            seen[k]["team"] += f", {r['team']}"
    steps += sorted(seen.values(), key=lambda s: (["Rookie","Single-A","High-A","Double-A","Triple-A","MLB"].index(s["level"]), s["when"]))
    if p["manual"]:
        steps.append(dict(level=p["level"], team=p["team"], when="Latest known"))
    timeline = "".join(f'<li class="{"now" if s["level"] == p["level"] else ""}"><span class="dot"></span><b>{E(s["level"])}</b><span>{E(s["team"])}</span><time>{E(s["when"])}</time></li>' for s in steps)
    s = p.get("season_stats")
    season = ""
    if p["season_by_team"]:
        rows = [dict(r["stat"], team=f"{r['team']} ({r['level']})") for r in p["season_by_team"]]
        season = stat_table(rows, ["team"] + cols, ["Team"] + labels)
    yby = ""
    if p["career_path"]:
        rows = [dict(r["stat"], yr=r["season"], team=r["team"], lv=r["level"]) for r in sorted(p["career_path"], key=lambda r: (r["season"], r["rank"]))]
        yby = stat_table(rows, ["yr", "team", "lv"] + cols, ["Year", "Team", "Lvl"] + labels)
    logs = ""
    if p["game_logs"]:
        lc = ["inningsPitched","hits","earnedRuns","baseOnBalls","strikeOuts"] if p["type"] == "Pitcher" else ["atBats","hits","homeRuns","rbi","baseOnBalls","strikeOuts"]
        ll = ["IP","H","ER","BB","K"] if p["type"] == "Pitcher" else ["AB","H","HR","RBI","BB","K"]
        rows = [dict(g["line"], d=fmt_date(g["date"]), o=("vs " if g["home"] else "@ ") + (g["opp"] or ""), lv=g["level"]) for g in p["game_logs"]]
        logs = f'<section class="card"><h2>Last {len(rows)} games of {p["season"]}</h2>{stat_table(rows, ["d","o","lv"] + lc, ["Date","Opp","Lvl"] + ll)}</section>'
    sc = ""
    if p["statcast"]:
        nice = {"expectedStatistics.avg": "xBA", "expectedStatistics.slg": "xSLG", "expectedStatistics.woba": "xwOBA", "expectedStatistics.era": "xERA",
                "sabermetrics.wRcPlus": "wRC+", "sabermetrics.war": "WAR", "sabermetrics.fip": "FIP", "sabermetrics.xfip": "xFIP", "sabermetrics.eraMinus": "ERA-", "sabermetrics.fipMinus": "FIP-"}
        blocks = ""
        for lvl, vals in p["statcast"].items():
            items = "".join(f'<div class="stat"><b>{(round(v,2) if isinstance(v,float) else E(v))}</b><span>{lab}</span></div>' for k, lab in nice.items() if (v := vals.get(k)) not in (None, ""))
            if items: blocks += f'<h3>{E(lvl)}</h3><div class="stats">{items}</div>'
        if blocks: sc = f'<section class="card"><h2>Advanced &amp; Statcast-based</h2>{blocks}<p class="note">Statcast-based numbers exist only for MLB and Triple-A.</p></section>'
    moves = feed_html(list(reversed(p["transactions"]))[:15], show_player=False, depth=1) if p["transactions"] else '<p class="note">No transactions on file.</p>'
    flags = ""
    if p.get("uncertain"):
        flags = '<div class="warn">' + "".join(f"<p>{E(u)}</p>" for u in p["uncertain"]) + "</div>"
    srcs = ""
    if p.get("sources") and p["manual"]:
        srcs = "<p class='note'>Sources: " + ", ".join(f'<a href="{E(u)}" rel="noopener">{i+1}</a>' for i, u in enumerate(p["sources"])) + "</p>"
    bt = f"B/T {p.get('bats')}/{p.get('throws')}" if p.get("bats") else ""
    meta = " · ".join(x for x in [p["position"], bt, f"Age {p['age']}" if p.get("age") else "", p.get("hometown"), f"MLB debut {fmt_date(p['mlb_debut'])}" if p.get("mlb_debut") else ""] if x)
    body = f"""<p class="crumb"><a href="../index.html">← All Pirates in the Pros</a></p>
<section class="phero"><div class="avatar">{E(''.join(w[0] for w in p['name'].split()[:2]))}</div><div>
<h1>{E(p['name'])}</h1><p class="meta">{E(meta)}</p>
<p class="now"><span class="lvl">{E(p['level'] or '')}</span> {E(p['team'] or '')}{f' · {E(p["org"])}' if p.get('org') and p.get('org') != p.get('team') else ''} {badge(p)}</p>
{f'<p class="note">{E(p["status_note"])}</p>' if p.get('status_note') else ''}{f'<p class="note">{E(p["note"])}</p>' if p.get('note') else ''}
</div></section>{flags}
<section class="card"><h2>{p['season']} season</h2><p class="big">{E(key_line(p))} {f'<span class="sub">({p["season_line_label"]})</span>' if p.get('season_line_label') else ''}</p>{season or '<p class="note">No affiliated stats this season.</p>'}</section>
<section class="card"><h2>Career path: Greenville to {E(p['highest_level'] or 'the pros')}</h2><ol class="path">{timeline}</ol></section>
{sc}{logs}
<section class="card"><h2>Moves &amp; transactions</h2>{moves}</section>
{f'<section class="card"><h2>Year by year</h2>{yby}</section>' if yby else ''}{srcs}
{newsletter()}"""
    return page(f"{p['name']} | {SITE}", body, depth=1, desc=f"{p['name']}, former ECU Pirate, now {p['level']} {p['team']}. Stats, career path and moves.")

CSS = r"""
:root{--purple:#4b1f78;--purple2:#592a8a;--gold:#fdc82f;--ink:#1d1430;--muted:#6b6280;--bg:#f6f3fa;--card:#fff;--line:#e6e0ef}
*{box-sizing:border-box}body{margin:0;font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:var(--ink);background:var(--bg)}
a{color:var(--purple2)}.wrap{max-width:1100px;margin:0 auto;padding:0 16px}
.top{background:var(--purple);color:#fff;border-bottom:4px solid var(--gold);position:sticky;top:0;z-index:5}
.top .wrap{display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:56px;flex-wrap:wrap}
.brand{color:#fff;text-decoration:none;font-weight:800;font-size:1.15rem;letter-spacing:.2px}.mark{color:var(--gold)}
nav a{color:#fff;text-decoration:none;margin-left:16px;font-weight:600;opacity:.9}nav a:hover{color:var(--gold)}
.hero{padding:28px 0 8px}.hero h1{font-size:clamp(1.6rem,4vw,2.4rem);line-height:1.15;margin:0 0 8px;color:var(--purple)}
.hero p{color:var(--muted);max-width:700px;margin:0 0 16px}
.stats{display:flex;flex-wrap:wrap;gap:10px;margin:8px 0}.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 14px;min-width:88px}
.stat b{display:block;font-size:1.4rem;color:var(--purple)}.stat span{font-size:.8rem;color:var(--muted)}.stat.total{background:var(--purple);border-color:var(--purple)}.stat.total b{color:var(--gold)}.stat.total span{color:#fff}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;margin:18px 0;box-shadow:0 1px 2px rgba(40,10,80,.05)}
.card h2{margin:0 0 12px;font-size:1.25rem;color:var(--purple)}.card h3{margin:12px 0 6px;font-size:1rem}
.tablehead{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px}
.filters{display:flex;gap:8px;flex-wrap:wrap}select{font:inherit;padding:8px 10px;border:1px solid var(--line);border-radius:8px;background:#fff}
.tablewrap{overflow-x:auto;-webkit-overflow-scrolling:touch}
table{width:100%;border-collapse:collapse;font-size:.95rem}th,td{text-align:left;padding:10px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:.8rem;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);white-space:nowrap}
#roster-table th{cursor:pointer;user-select:none}#roster-table th:after{content:" ↕";opacity:.35}#roster-table th.asc:after{content:" ↑";opacity:1}#roster-table th.desc:after{content:" ↓";opacity:1}
tbody tr:hover{background:#faf7fd}td a{font-weight:700;text-decoration:none}
.sub{color:var(--muted);font-size:.8rem}.pos{font-size:.75rem;color:var(--muted);font-weight:600}
.lvl{display:inline-block;padding:2px 8px;border-radius:999px;font-size:.78rem;font-weight:700;background:#efe8f7;color:var(--purple);white-space:nowrap}
.lvl.l0{background:var(--gold);color:var(--ink)}.lvl.l1{background:#5e3591;color:#fff}.lvl.l2{background:#7a52aa;color:#fff}
.badge{display:inline-block;padding:2px 8px;border-radius:6px;font-size:.75rem;font-weight:700;background:#e7f6ec;color:#17663a}
.st-released,.st-free-agent,.st-retired,.st-inactive{background:#fde8e8;color:#9b1c1c}.st-unknown{background:#fff4d6;color:#7a5a00}
.flag{display:inline-block;width:18px;height:18px;line-height:18px;text-align:center;border-radius:50%;background:#fff4d6;color:#7a5a00;font-size:.7rem;font-weight:800}
.note{color:var(--muted);font-size:.85rem}
.feed{list-style:none;margin:0;padding:0}.feed li{display:grid;grid-template-columns:110px 130px 1fr;gap:10px;padding:9px 0;border-bottom:1px solid var(--line);font-size:.93rem}
.feed time{color:var(--muted);font-size:.85rem}.kind{font-size:.75rem;font-weight:700;padding:2px 8px;border-radius:6px;background:#eee;justify-self:start;height:fit-content}
.k-up{background:var(--gold);color:var(--ink)}.k-down{background:#fde8e8;color:#9b1c1c}.k-il{background:#eef0f4;color:#3c4656}.k-new{background:#efe8f7;color:var(--purple)}
.news{display:grid;grid-template-columns:1fr 1fr;gap:18px;align-items:center;background:linear-gradient(135deg,var(--purple),#2c1149);color:#fff;border:0}
.news h2{color:var(--gold)}.news form{display:flex;flex-wrap:wrap;gap:8px}.news input{flex:1;min-width:200px;font:inherit;padding:12px;border-radius:8px;border:0}
.news button{font:inherit;font-weight:800;padding:12px 18px;border:0;border-radius:8px;background:var(--gold);color:var(--ink);cursor:pointer}.formmsg{flex-basis:100%;margin:0;color:var(--gold)}
.sr{position:absolute;left:-9999px}
.crumb{margin:16px 0 0}.phero{display:flex;gap:18px;align-items:center;padding:18px 0 4px}
.avatar{flex:0 0 84px;height:84px;border-radius:50%;background:var(--purple);color:var(--gold);display:grid;place-items:center;font-size:2rem;font-weight:800;border:4px solid var(--gold)}
.phero h1{margin:0;color:var(--purple);font-size:clamp(1.6rem,4vw,2.2rem)}.meta{margin:2px 0;color:var(--muted)}.now{margin:6px 0;font-weight:600}
.big{font-size:1.2rem;font-weight:700;margin:0 0 10px}
.path{list-style:none;margin:0;padding:0 0 0 8px;border-left:3px solid var(--line)}.path li{position:relative;padding:6px 0 12px 20px;display:grid;grid-template-columns:110px 1fr auto;gap:8px}
.path .dot{position:absolute;left:-10px;top:10px;width:16px;height:16px;border-radius:50%;background:#fff;border:3px solid var(--purple2)}
.path li.now .dot{background:var(--gold);border-color:var(--purple)}.path b{color:var(--purple)}.path time{color:var(--muted);font-size:.85rem}
table.mini{font-size:.85rem}table.mini td,table.mini th{padding:6px;white-space:nowrap}
.warn{background:#fff8e1;border:1px solid #f3d27a;border-radius:10px;padding:4px 14px;margin:12px 0;font-size:.9rem}
footer{background:#21102f;color:#d9cfe6;margin-top:30px;padding:18px 0;font-size:.85rem}footer a{color:var(--gold)}
@media (max-width:700px){
 body{font-size:15px}nav a{margin-left:10px;font-size:.9rem}.news{grid-template-columns:1fr}
 #roster-table thead{display:none}#roster-table tr{display:grid;grid-template-columns:1fr auto;gap:2px 10px;padding:10px 0;border-bottom:1px solid var(--line)}
 #roster-table td{border:0;padding:2px 0}#roster-table td:nth-child(1){grid-column:1}#roster-table td:nth-child(2){grid-column:2;grid-row:1;text-align:right}
 #roster-table td:nth-child(3){grid-column:1 / span 2;font-size:.85rem}#roster-table td:nth-child(4){grid-column:1;font-size:.85rem}#roster-table td:nth-child(5){grid-column:2;grid-row:3;text-align:right}
 .feed li{grid-template-columns:1fr auto}.feed .desc{grid-column:1 / span 2}
 .path li{grid-template-columns:1fr;gap:0}.phero{align-items:flex-start}.avatar{flex-basis:64px;height:64px;font-size:1.5rem}
}
"""
JS = r"""
(function(){var t=document.getElementById('roster-table');if(!t)return;var tb=t.tBodies[0];
var fl=document.getElementById('fLevel'),ft=document.getElementById('fType'),fs=document.getElementById('fStatus');
function apply(){[].forEach.call(tb.rows,function(r){var ok=(!fl.value||r.dataset.level===fl.value)&&(!ft.value||r.dataset.type===ft.value)&&(!fs.value||(fs.value==='released'?r.dataset.status!=='active':r.dataset.status===fs.value));r.style.display=ok?'':'none';});}
[fl,ft,fs].forEach(function(e){e.addEventListener('change',apply)});apply();
[].forEach.call(t.tHead.rows[0].cells,function(th,i){th.addEventListener('click',function(){var asc=!th.classList.contains('asc');[].forEach.call(t.tHead.rows[0].cells,function(c){c.classList.remove('asc','desc')});th.classList.add(asc?'asc':'desc');
var rows=[].slice.call(tb.rows);rows.sort(function(a,b){var x=a.cells[i].dataset.v,y=b.cells[i].dataset.v;var nx=parseFloat(x),ny=parseFloat(y);var c=(!isNaN(nx)&&!isNaN(ny))?nx-ny:(x||'~').localeCompare(y||'~');return asc?c:-c});rows.forEach(function(r){tb.appendChild(r)});});});})();
function pipSignup(f){var m=f.querySelector('.formmsg'),b=f.querySelector('button');if(f.getAttribute('action')==='#'){m.textContent="Thanks! Sign-ups open soon.";return false}b.disabled=true;fetch(f.action,{method:'POST',mode:'no-cors',body:new FormData(f)}).then(function(){m.textContent="You're in! Check your inbox to confirm.";f.reset()}).catch(function(){m.textContent="Hmm, that didn't go through. Try again?"}).finally(function(){b.disabled=false});return false}
"""

def main():
    if os.path.exists(OUT): shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, "players")); os.makedirs(os.path.join(OUT, "assets"))
    open(os.path.join(OUT, "assets/style.css"), "w").write(CSS)
    open(os.path.join(OUT, "assets/app.js"), "w").write(JS)
    open(os.path.join(OUT, "index.html"), "w").write(home())
    for p in D["players"]:
        open(os.path.join(OUT, "players", p["slug"] + ".html"), "w").write(player_page(p))
    shutil.copy(os.path.join(ROOT, "data/players.json"), os.path.join(OUT, "players.json"))
    print("built", OUT, len(D["players"]), "player pages")
main()
