---
name: apple-notes-folder-clear
description: Delete all Apple Notes inside a specified folder or smart folder by name. Use when asked to clear a Notes folder such as `RTF Reembolsos`, bulk-delete all notes in a folder, or wipe the contents of a specific Apple Notes folder after confirmation.
---

# Apple Notes Folder Clear

Use this skill to delete all notes inside a specified Apple Notes folder or smart folder.

## Safety rule

- Always start with `--dry-run` unless the user is explicitly asking you to delete now.
- For destructive deletion, only run without `--dry-run` when the user clearly asked for it.
- Report how many notes were found and list their names before deletion when practical.

## Workflow

1. Run the bundled script in `scripts/clear_folder_notes.py --folder "<name>" --dry-run`.
2. Confirm the target folder contents from the dry run.
3. If the user clearly wants deletion, rerun with `--force`.
4. Report how many notes were deleted.

## Commands

Dry run:

```bash
python3 skills/apple-notes-folder-clear/scripts/clear_folder_notes.py --folder "RTF Reembolsos" --dry-run
```

Real deletion:

```bash
python3 skills/apple-notes-folder-clear/scripts/clear_folder_notes.py --folder "RTF Reembolsos" --force
```

## Notes

- This deletes notes found directly inside the specified folder or smart folder.
- Use exact folder names.
- The script uses Apple Notes via AppleScript on macOS.
- If AppleScript access is blocked, tell the user permissions are needed.
