#!/usr/bin/env bash
set -o pipefail

TARGET="channel:1485664101756833902"
PROGRESS_FILE="projects/dges/data/backfill_course_details_progress.json"

send_discord() {
  openclaw message send --channel discord --target "$TARGET" --message "$1" >/dev/null 2>&1 || true
}

while true; do
  sleep 5
  printf "[monitor] alive\n"
done &
keepalive_pid="$!"
trap 'kill "$keepalive_pid" >/dev/null 2>&1 || true' EXIT

stdbuf -oL -eL python3 projects/dges/backfill_course_details.py \
  --batch-size 40 \
  --row-gap-low 2 \
  --row-gap-high 5 \
  --batch-rest-low 20 \
  --batch-rest-high 60 2>&1 | while IFS= read -r line; do
    printf "%s\n" "$line"
    if [[ "$line" =~ progress[[:space:]]+([0-9]+([.][0-9]+)?)%[[:space:]]+::[[:space:]]+processed=([0-9]+)/([0-9]+)[[:space:]]+written=([0-9]+)[[:space:]]+errors=([0-9]+) ]]; then
      pct="${BASH_REMATCH[1]}"
      processed="${BASH_REMATCH[3]}"
      total="${BASH_REMATCH[4]}"
      written="${BASH_REMATCH[5]}"
      errors="${BASH_REMATCH[6]}"
      send_discord "DGES detalhes_do_curso: ${pct}% complete. processed=${processed}/${total} written=${written} errors=${errors}"
    fi
  done

status="${PIPESTATUS[0]}"

if [[ "$status" -eq 0 ]]; then
  msg=$(python3 - <<'PY'
import json, os

p = "projects/dges/data/backfill_course_details_progress.json"
if not os.path.exists(p):
    print("DGES detalhes_do_curso backfill complete, but progress file is missing.")
    raise SystemExit

with open(p, encoding="utf-8") as fh:
    d = json.load(fh)

pct = d.get("percent", d.get("completion_percent", d.get("progress_percent", "?")))
processed = d.get("processed", "?")
total = d.get("total", "?")
written = d.get("written", "?")
errors = d.get("errors", "?")
area = d.get("area_cnaef_count", "?")
print(f"DGES detalhes_do_curso backfill complete: {pct}% processed={processed}/{total} written={written} errors={errors} area_cnaef_count={area}")
PY
)
  send_discord "$msg"
else
  msg=$(STATUS="$status" python3 - <<'PY'
import json, os

status = os.environ.get("STATUS")
p = "projects/dges/data/backfill_course_details_progress.json"
if os.path.exists(p):
    with open(p, encoding="utf-8") as fh:
        d = json.load(fh)
    pct = d.get("percent", d.get("completion_percent", d.get("progress_percent", "?")))
    processed = d.get("processed", "?")
    total = d.get("total", "?")
    written = d.get("written", "?")
    errors = d.get("errors", "?")
    print(f"[blocked] DGES detalhes_do_curso backfill failed: exit={status} latest={pct}% processed={processed}/{total} written={written} errors={errors}")
else:
    print(f"[blocked] DGES detalhes_do_curso backfill failed: exit={status}; progress file missing.")
PY
)
  send_discord "$msg"
fi

exit "$status"
