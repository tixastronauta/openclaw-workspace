# OpenClaw Release Watch

Daily watcher for new stable OpenClaw releases.

## Files

- `scripts/check-openclaw-release.sh` — fetches latest stable GitHub release metadata; pass `--key <target>` to deduplicate notifications per delivery target
- `state/latest_release.json` — raw recent releases payload cache
- `state/latest_release_meta.json` — latest stable release metadata cache
- `state/last_stable_release_<key>.json` — last release already notified for each target
- `state/last_stable_release.json` — legacy fallback marker
