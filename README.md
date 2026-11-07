# Agent Scheduler Hub

Shareable web dashboard for the AndroidHarness scheduler
([scheduling-reminders](../.. skill) running at `agent/sched`).

- `sched/` — the scheduler itself (schedule.yaml, compile.py, runner.sh).
- `docs/` — static dashboard published to GitHub Pages:
  - `index.html` — the interface
  - `state.json` — snapshot of schedule, next runs, heartbeat, recent events
- `scripts/make_snapshot.py` — regenerates `docs/state.json` from the current
  scheduler state:
  ```bash
  python3 sched-hub/scripts/make_snapshot.py
  ```

## Update & publish

```bash
cd sched-hub
python3 scripts/make_snapshot.py
git add -A && git commit -m "refresh snapshot" && git push
```

The dashboard is served by GitHub Pages from `/docs` (see repo settings).

## Notes

- State is a snapshot taken at push time; it is not live.
- Runner health: heartbeat file age (<90 s = alive).
- To pause/stop/restart the runner, use the flag files (see `sched/README.md`
  or the skill).
