#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="/data/.openclaw/workspace/projects/openclaw-release-watch/state"
CHANNEL_KEY="global"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --key|--channel)
      CHANNEL_KEY="${2:-}"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [[ ! "$CHANNEL_KEY" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "Invalid key: $CHANNEL_KEY" >&2
  exit 2
fi

LAST_FILE="$STATE_DIR/last_stable_release_${CHANNEL_KEY}.json"
LEGACY_LAST_FILE="$STATE_DIR/last_stable_release.json"
TMP_JSON="$STATE_DIR/latest_release.json"
TMP_META="$STATE_DIR/latest_release_meta.json"
mkdir -p "$STATE_DIR"

curl -fsSL \
  -H 'Accept: application/vnd.github+json' \
  -H 'X-GitHub-Api-Version: 2022-11-28' \
  'https://api.github.com/repos/openclaw/openclaw/releases?per_page=20' > "$TMP_JSON"

python3 - <<'PY' "$TMP_JSON" "$TMP_META" "$LAST_FILE" "$LEGACY_LAST_FILE"
import json, sys, os
from pathlib import Path

json_path, meta_path, last_path, legacy_last_path = sys.argv[1:5]
releases = json.load(open(json_path, 'r', encoding='utf-8'))
stable = None
for rel in releases:
    if rel.get('draft') or rel.get('prerelease'):
        continue
    stable = rel
    break
if not stable:
    print('NO_STABLE_RELEASE')
    raise SystemExit(0)

tag = stable.get('tag_name') or ''
name = stable.get('name') or tag
url = stable.get('html_url') or 'https://github.com/openclaw/openclaw/releases'
published = stable.get('published_at') or ''
body = stable.get('body') or ''
payload = {
    'tag_name': tag,
    'name': name,
    'html_url': url,
    'published_at': published,
    'body': body,
}
Path(meta_path).write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')

def read_last(path):
    if not os.path.exists(path):
        return None
    try:
        return json.load(open(path, 'r', encoding='utf-8')).get('tag_name')
    except Exception:
        return None

# Backwards compatibility: if a channel-specific marker does not exist yet,
# seed it from the legacy marker. After that, each notification target gets its
# own durable marker so a release can be announced once per target, never again
# on following days.
last_tag = read_last(last_path)
if last_tag is None:
    last_tag = read_last(legacy_last_path)

if last_tag == tag:
    print('NO_CHANGE')
else:
    marker = {
        'tag_name': tag,
        'name': name,
        'html_url': url,
        'published_at': published,
        'notified_at': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
    }
    tmp_marker_path = f'{last_path}.tmp'
    Path(tmp_marker_path).write_text(json.dumps(marker, ensure_ascii=False), encoding='utf-8')
    os.replace(tmp_marker_path, last_path)
    print('NEW_RELEASE')
PY
