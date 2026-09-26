#!/usr/bin/env bash
set -euo pipefail

LABEL="com.shunlp.shunri-reel-worker"
UID_NOW="$(id -u)"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
OUT_LOG="$HOME/Library/Logs/shunri-reel-worker.log"
ERR_LOG="$HOME/Library/Logs/shunri-reel-worker-error.log"

echo "Shunri Reel worker status"
echo "- plist: $PLIST"

if [[ ! -f "$PLIST" ]]; then
  echo "- installed: no"
  exit 1
fi

echo "- installed: yes"

if launchctl print "gui/$UID_NOW/$LABEL" >/dev/null 2>&1; then
  echo "- launchd: loaded"
else
  echo "- launchd: not loaded"
  exit 1
fi

echo "- interval: 60s"
echo "- stdout: $OUT_LOG"
echo "- stderr: $ERR_LOG"

if [[ -f "$OUT_LOG" ]]; then
  echo
  echo "Latest stdout:"
  tail -n 8 "$OUT_LOG" || true
fi

if [[ -s "$ERR_LOG" ]]; then
  echo
  echo "Latest stderr:"
  tail -n 8 "$ERR_LOG" || true
fi
