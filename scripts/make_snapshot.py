#!/usr/bin/env python3
"""Generate docs/state.json for the scheduler dashboard."""
import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCHED = os.environ.get("SCHED_HOME", os.path.join(ROOT, "..", "agent", "sched"))
OUT = os.path.join(ROOT, "docs", "state.json")


def load_yaml_simple(path):
    """Minimal YAML subset parser (no PyYAML dependency needed for our file)."""
    # Fallback: read jobs as text-ish is fragile; try pyyaml first.
    try:
        import yaml

        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        return {"jobs": []}


def main():
    sched = {
        "generated_at": datetime.now(ZoneInfo("UTC")).isoformat(timespec="seconds"),
        "sched_home": SCHED,
        "jobs": [],
        "upcoming": [],
        "log_tail": [],
        "digest_files": [],
    }

    sched_yaml = os.path.join(SCHED, "schedule.yaml")
    if os.path.exists(sched_yaml):
        cfg = load_yaml_simple(sched_yaml)
        sched["timezone"] = cfg.get("timezone", "UTC")
        sched["jobs"] = [
            {
                "id": j.get("id"),
                "title": j.get("title", j.get("id")),
                "schedule": j.get("schedule", {}),
                "enabled": j.get("enabled", True),
            }
            for j in cfg.get("jobs", [])
        ]
    else:
        sched["timezone"] = "UTC"

    due = os.path.join(SCHED, "due.tsv")
    now = datetime.now(ZoneInfo("UTC")).timestamp()
    tz = ZoneInfo(sched.get("timezone", "UTC"))
    if os.path.exists(due):
        with open(due, encoding="utf-8") as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 2:
                    continue
                try:
                    ep = int(parts[0])
                except ValueError:
                    continue
                label = datetime.fromtimestamp(ep, tz).strftime("%Y-%m-%d %H:%M %Z")
                sched["upcoming"].append(
                    {"epoch": ep, "id": parts[1], "local": label,
                     "due": ep <= now}
                )
    sched["upcoming"].sort(key=lambda r: r["epoch"])

    logf = os.path.join(SCHED, "logs", "sched.log")
    if os.path.exists(logf):
        with open(logf, encoding="utf-8", errors="replace") as f:
            sched["log_tail"] = f.readlines()[-15:]

    hb = os.path.join(SCHED, "heartbeat")
    if os.path.exists(hb):
        try:
            sched["heartbeat_age_s"] = int(now - int(open(hb).read().strip()))
        except ValueError:
            sched["heartbeat_age_s"] = None
    else:
        sched["heartbeat_age_s"] = None

    summaries = os.path.join(ROOT, "..", "summaries")
    abs_summaries = os.path.abspath(summaries)
    if os.path.isdir(abs_summaries):
        files = sorted(
            f for f in os.listdir(abs_summaries) if f.startswith("football_summary_")
        )
        sched["digest_files"] = files[-5:]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(sched, f, ensure_ascii=False, indent=2)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
