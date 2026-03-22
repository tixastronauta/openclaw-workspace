#!/usr/bin/env python3
import argparse
import re
import subprocess
import sys
from pathlib import Path


def run_osascript(script: str) -> str:
    proc = subprocess.run(
        ["osascript", "-"],
        input=script,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "osascript failed")
    return proc.stdout.strip()


def default_dest_root() -> Path:
    candidates = [
        Path.home() / "Dropbox" / "Reticências Fenomenais" / "Documentos para a contabilidade",
        Path.home() / "Library/CloudStorage/Dropbox" / "Reticências Fenomenais" / "Documentos para a contabilidade",
    ]
    for p in candidates:
        if p.parent.exists():
            return p
    return candidates[0]


def sanitize_filename(text: str) -> str:
    text = text.strip().replace("/", "-")
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^\w\-.]+", "", text, flags=re.UNICODE)
    text = re.sub(r"_+", "_", text)
    return text[:180].strip("._-") or "note"


def apple_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def discover_notes(account: str, tag: str):
    script = f'''
on pad2(n)
  if n < 10 then
    return "0" & n
  end if
  return n as text
end pad2

tell application "Notes"
  set outLines to {{}}
  repeat with n in notes of account "{apple_escape(account)}"
    try
      set b to body of n
      if b contains "{apple_escape(tag)}" then
        set d to creation date of n
        set yyyy to year of d as integer
        set mm to my pad2(month of d as integer)
        set dd to my pad2(day of d as integer)
        set isoDate to (yyyy as text) & "-" & mm & "-" & dd
        copy ((name of n) & tab & isoDate) to end of outLines
      end if
    end try
  end repeat
  if (count of outLines) is 0 then
    return ""
  end if
  set AppleScript's text item delimiters to linefeed
  return outLines as text
end tell
'''
    raw = run_osascript(script)
    notes = []
    if not raw:
        return notes
    for line in raw.splitlines():
        if "\t" not in line:
            continue
        name, iso_date = line.split("\t", 1)
        notes.append({"name": name, "created": iso_date})
    return notes


def export_note(account: str, note_name: str, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    script = f'''
use scripting additions

tell application "Notes"
  activate
  set targetNote to missing value
  repeat with n in notes of account "{apple_escape(account)}"
    try
      if (name of n) is equal to "{apple_escape(note_name)}" then
        set targetNote to n
        exit repeat
      end if
    end try
  end repeat
  if targetNote is missing value then error "Note not found: {apple_escape(note_name)}"
  show targetNote
end tell

delay 1.2

tell application "System Events"
  tell process "Notes"
    click menu item "Export as PDF…" of menu "File" of menu bar item "File" of menu bar 1
    delay 1.0
    keystroke "{apple_escape(str(output_path))}"
    delay 0.5
    keystroke return
  end tell
end tell
'''
    run_osascript(script)


def main():
    ap = argparse.ArgumentParser(description="Export Apple Notes reimbursement-tag notes to Dropbox PDFs")
    ap.add_argument("--tag", default="#reembolso")
    ap.add_argument("--account", default="iCloud")
    ap.add_argument("--dest-root", default=str(default_dest_root()))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    dest_root = Path(args.dest_root).expanduser()
    notes = discover_notes(args.account, args.tag)

    if not notes:
        print("No matching notes found.")
        return 0

    planned = []
    for note in notes:
        year = note["created"][:4]
        filename = f"{note['created']}_{sanitize_filename(note['name'])}.pdf"
        planned.append((note["name"], dest_root / year / filename))

    print(f"Found {len(planned)} matching notes for tag {args.tag}.")
    for name, path in planned:
        print(f"- {name} -> {path}")

    if args.dry_run:
        return 0

    failures = []
    for name, path in planned:
        try:
            export_note(args.account, name, path)
            print(f"Exported: {path}")
        except Exception as e:
            failures.append((name, str(e)))
            print(f"FAILED: {name}: {e}", file=sys.stderr)

    if failures:
        print("\nSome exports failed.", file=sys.stderr)
        print("Most likely cause: macOS Accessibility permission is missing for osascript/System Events, or the Notes UI menu label differs.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
