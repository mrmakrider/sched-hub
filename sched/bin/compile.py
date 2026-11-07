#!/usr/bin/env python3
import os, sys, datetime as dt
import yaml
from zoneinfo import ZoneInfo
BASE = os.environ.get("SCHED_HOME", os.path.expanduser("~/agent/sched"))
H = int(os.environ.get("HORIZON_H", "48"))
DAYS = ["mon","tue","wed","thu","fri","sat","sun"]
cfg = yaml.safe_load(open(f"{BASE}/schedule.yaml")) or {}
dtz = cfg.get("timezone","UTC"); dfl = cfg.get("defaults",{})
now = dt.datetime.now(dt.timezone.utc)
lo, hi = now - dt.timedelta(hours=H), now + dt.timedelta(hours=H)
rows, seen = [], set()
def one_line(s): return " ".join(str(s).replace("\t"," ").split())
for j in cfg.get("jobs",[]):
    if not j.get("enabled", True): continue
    jid = j["id"]
    if jid in seen: sys.exit(f"duplicate job id: {jid}")
    seen.add(jid)
    tz = ZoneInfo(j.get("tz", dtz))
    s, a = j["schedule"], j["action"]
    kind = s["type"]; occ = []
    if kind == "once":
        t = dt.datetime.fromisoformat(str(s["at"])); occ=[t if t.tzinfo else t.replace(tzinfo=tz)]
    elif kind in ("daily","weekly"):
        hh, mm = map(int, str(s["time"]).split(":"))
        days = {DAYS.index(d[:3]) for d in s["days"]} if kind=="weekly" else set(range(7))
        d0 = lo.astimezone(tz).date()
        for i in range(H//24*2+4):
            d = d0 + dt.timedelta(days=i)
            if d.weekday() in days: occ.append(dt.datetime(d.year,d.month,d.day,hh,mm,tzinfo=tz))
    elif kind == "interval":
        step = dt.timedelta(minutes=int(s["every_minutes"]))
        anc = dt.datetime.fromisoformat(str(s["anchor"])); anc = anc if anc.tzinfo else anc.replace(tzinfo=tz)
        k = max(0, int((lo-anc)/step)); t = anc + k*step
        while t <= hi: occ.append(t); t += step
    else: sys.exit(f"unknown schedule type: {kind}")
    catchup = j.get("catchup", dfl.get("catchup","skip"))
    grace = 172800 if catchup=="run" else int(j.get("grace_minutes", dfl.get("grace_minutes",120)))*60
    payload = a.get("text") or a.get("prompt") or a.get("cmd") or j.get("title", jid)
    for t in occ:
        if lo <= t <= hi: rows.append((int(t.timestamp()), jid, a["type"], grace, one_line(payload)))
rows.sort()
tmp = f"{BASE}/due.tsv.tmp"
with open(tmp,"w") as f:
    for r in rows: f.write("\t".join(map(str,r))+"\n")
os.replace(tmp, f"{BASE}/due.tsv")
print(f"compiled {len(rows)} occurrences")
