#!/bin/sh
BASE="${SCHED_HOME:-$HOME/agent/sched}"
MAX_RUN="${1:-3300}"; TICK=30
LOCK="$BASE/runner.lock"; DONE="$BASE/done.log"; DUE="$BASE/due.tsv"
LOG="$BASE/logs/sched.log"; OUT="$BASE/outbox"
TAB="$(printf '\t')"
log() { printf '%s %s %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$1" "$2" >> "$LOG"; }
if ! mkdir "$LOCK" 2>/dev/null; then
  hb=$(cat "$BASE/heartbeat" 2>/dev/null || echo 0)
  if [ $(( $(date +%s) - hb )) -lt 120 ]; then exit 0; fi
  log WARN "stale lock (hb=$hb), taking over"; rm -rf "$LOCK"; mkdir "$LOCK" || exit 1
fi
echo $$ > "$BASE/runner.pid"; trap 'rm -rf "$LOCK"' EXIT INT TERM
emit() {
  f="$OUT/$(printf '%s' "$1" | tr -c 'A-Za-z0-9._-' '_').txt"
  printf 'key: %s\nkind: %s\nscheduled_epoch: %s\nlate_seconds: %s\npayload: %s\n' \
    "$1" "$2" "$3" "$4" "$5" > "$f.tmp" && mv "$f.tmp" "$f"
  command -v termux-notification >/dev/null 2>&1 && \
    termux-notification --title "Reminder" --content "$5" 2>/dev/null
}
fire() {
  ep="$1"; id="$2"; kind="$3"; grace="$4"; payload="$5"
  key="$id@$ep"; now=$(date +%s); late=$((now - ep))
  grep -qxF "$key" "$DONE" 2>/dev/null && return
  if [ "$late" -gt "$grace" ]; then
    emit "$key" missed "$ep" "$late" "MISSED ($id): $payload"
    echo "$key" >> "$DONE"; log WARN "missed $key late=${late}s"; return
  fi
  case "$kind" in
    notify|agent_task)
      emit "$key" "$kind" "$ep" "$late" "$payload"
      echo "$key" >> "$DONE"; log INFO "fired $key kind=$kind late=${late}s" ;;
    shell)
      echo "$key" >> "$DONE"
      timeout 300 sh -c "$payload" >> "$BASE/logs/job-$id.log" 2>&1; rc=$?
      log INFO "shell $key rc=$rc"
      [ "$rc" -ne 0 ] && emit "$key" shell_failed "$ep" "$late" "Job $id failed rc=$rc" ;;
    *) log ERROR "unknown kind '$kind' for $key" ;;
  esac
}
run_due() {
  now=$(date +%s)
  while IFS="$TAB" read -r ep id kind grace payload; do
    [ -n "$ep" ] || continue
    [ "$ep" -le "$now" ] && fire "$ep" "$id" "$kind" "$grace" "$payload"
  done < "$DUE"
}
end=$(( $(date +%s) + MAX_RUN )); last_prune=0
log INFO "runner start pid=$$ max=${MAX_RUN}s"
while [ "$(date +%s)" -lt "$end" ]; do
  now=$(date +%s); echo "$now" > "$BASE/heartbeat"
  [ -f "$BASE/STOP" ] && { log INFO "STOP flag, exiting"; break; }
  if [ ! -f "$BASE/PAUSE" ]; then
    if [ "$BASE/schedule.yaml" -nt "$DUE" ] || [ $(( now - $(stat -c %Y "$DUE" 2>/dev/null || echo 0) )) -gt 900 ]; then
      python3 "$BASE/bin/compile.py" >> "$LOG" 2>&1
    fi
    run_due
  fi
  if [ $(( now - last_prune )) -gt 3600 ]; then
    cut=$(( now - 604800 )); awk -F@ -v c="$cut" '$NF >= c' "$DONE" > "$DONE.tmp" && mv "$DONE.tmp" "$DONE"
    [ "$(wc -c < "$LOG")" -gt 524288 ] && mv "$LOG" "$LOG.1"
    last_prune=$now
  fi
  sleep "$TICK"
done
rm -rf "$LOCK"; trap - EXIT
[ -f "$BASE/STOP" ] || { nohup sh "$0" "$MAX_RUN" >> "$LOG" 2>&1 & }
