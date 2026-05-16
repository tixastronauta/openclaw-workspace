#!/usr/bin/env bash
set -euo pipefail

cd /data/.openclaw/workspace

TARGET="channel:1485664101756833902"
RUN_LOG="projects/dges/data/backfill_course_details_runner.log"

send_discord() {
  openclaw message send --channel discord --target "$TARGET" --message "$1" >/dev/null 2>&1 || true
}

send_discord "DGES detalhes_do_curso: acelerei o backfill. Retoma a partir das linhas já escritas; novo ritmo: batches de 40, ~2-5s por linha e 20-60s entre batches."

set +e
stdbuf -oL -eL python3 projects/dges/backfill_course_details.py \
  --batch-size 40 \
  --row-gap-low 2 \
  --row-gap-high 5 \
  --batch-rest-low 20 \
  --batch-rest-high 60 2>&1 | tee -a "$RUN_LOG" | while IFS= read -r line; do
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
set -e

msg="$(
  STATUS="$status" python3 - <<'PY'
import json
import os

status = int(os.environ["STATUS"])
path = "projects/dges/data/backfill_course_details_progress.json"

if os.path.exists(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    pct = data.get("percent", "?")
    processed = data.get("processed", "?")
    total = data.get("total", "?")
    written = data.get("written", "?")
    errors = data.get("errors", "?")
    area = data.get("area_cnaef_count", "?")
    if status == 0:
        print(f"DGES detalhes_do_curso: concluído. {pct}% processed={processed}/{total} written={written} errors={errors} area_cnaef_count={area}")
    else:
        print(f"[blocked] DGES detalhes_do_curso: falhou com exit={status}. latest={pct}% processed={processed}/{total} written={written} errors={errors}")
else:
    print(f"[blocked] DGES detalhes_do_curso: falhou com exit={status}; progress file missing.")
PY
)"
send_discord "$msg"
exit "$status"
