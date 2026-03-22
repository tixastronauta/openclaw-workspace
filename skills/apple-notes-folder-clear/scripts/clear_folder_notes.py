#!/usr/bin/env python3
import argparse
import subprocess
import sys


def run_osascript(script: str) -> str:
    proc = subprocess.run(["osascript", "-"], input=script, text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "osascript failed")
    return proc.stdout.strip()


def apple_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def list_notes(folder_name: str):
    script = f'''
tell application "Notes"
  set targetFolder to missing value
  repeat with acc in accounts
    repeat with f in folders of acc
      try
        if (name of f) is equal to "{apple_escape(folder_name)}" then
          set targetFolder to f
          exit repeat
        end if
      end try
    end repeat
    if targetFolder is not missing value then exit repeat
  end repeat

  if targetFolder is missing value then error "Folder not found: {apple_escape(folder_name)}"

  set outLines to {{}}
  repeat with n in notes of targetFolder
    try
      copy (name of n) to end of outLines
    end try
  end repeat

  if (count of outLines) is 0 then return ""
  set AppleScript's text item delimiters to linefeed
  return outLines as text
end tell
'''
    raw = run_osascript(script)
    return [line for line in raw.splitlines() if line.strip()]


def delete_notes(folder_name: str):
    script = f'''
tell application "Notes"
  set targetFolder to missing value
  repeat with acc in accounts
    repeat with f in folders of acc
      try
        if (name of f) is equal to "{apple_escape(folder_name)}" then
          set targetFolder to f
          exit repeat
        end if
      end try
    end repeat
    if targetFolder is not missing value then exit repeat
  end repeat

  if targetFolder is missing value then error "Folder not found: {apple_escape(folder_name)}"

  set noteNames to {{}}
  repeat with n in notes of targetFolder
    try
      copy (name of n) to end of noteNames
    end try
  end repeat

  repeat with n in notes of targetFolder
    try
      delete n
    end try
  end repeat

  if (count of noteNames) is 0 then return ""
  set AppleScript's text item delimiters to linefeed
  return noteNames as text
end tell
'''
    raw = run_osascript(script)
    return [line for line in raw.splitlines() if line.strip()]


def main():
    ap = argparse.ArgumentParser(description="Delete all Apple Notes inside a named folder")
    ap.add_argument("--folder", required=True)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--force", action="store_true")
    args = ap.parse_args()

    notes = list_notes(args.folder)
    print(f"Found {len(notes)} notes in folder {args.folder}.")
    for name in notes:
        print(f"- {name}")

    if args.dry_run or not args.force:
        print("Dry run only. No notes deleted.")
        return 0

    deleted = delete_notes(args.folder)
    print(f"Deleted {len(deleted)} notes from folder {args.folder}.")
    for name in deleted:
        print(f"- {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
