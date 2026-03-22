---
name: apple-notes-reembolso-export
description: Export Apple Notes tagged with reimbursement markers like #reembolso to PDF files in Dropbox using the note date and note name in the filename. Use when asked to automate exporting reimbursement receipt notes from Apple Notes, save tagged notes as PDFs, or batch-export Apple Notes receipt scans into Dropbox.
---

# Apple Notes Reembolso Export

Use this skill to export Apple Notes that contain a reimbursement tag such as `#reembolso` into Dropbox as PDF files.

## Workflow

1. Run the bundled script in `scripts/export_reembolso_notes.py`.
2. Start with `--dry-run` to confirm which notes match and what filenames will be generated.
3. If the dry run looks correct, run without `--dry-run` to export PDFs.
4. If the export fails with an Accessibility or UI scripting error, tell the user to grant Accessibility access to `osascript` / Terminal and retry.

## Default behavior

- Search the specified Apple Notes account for notes whose HTML body contains the reimbursement marker text case-insensitively.
- Treat Apple Notes tag text pragmatically: match the marker text even if Notes exposes it oddly in the HTML body.
- Use the note creation date for filenames by default.
- Sanitize the note name for safe filenames.
- Save files under Dropbox, defaulting to `~/Dropbox/Reticências Fenomenais/Documentos para a contabilidade/<YEAR>/`.
- Place each export inside the proper year folder derived from the note date.
- Filename format: `YYYY-MM-DD_note-name.pdf`

## Commands

Dry run:

```bash
python3 skills/apple-notes-reembolso-export/scripts/export_reembolso_notes.py --dry-run
```

Real export:

```bash
python3 skills/apple-notes-reembolso-export/scripts/export_reembolso_notes.py
```

Custom tag / destination:

```bash
python3 skills/apple-notes-reembolso-export/scripts/export_reembolso_notes.py \
  --tag "#reembolso" \
  --dest "$HOME/Dropbox/Reembolsos"
```

## Notes

- This workflow exports the **entire note as a PDF**. That is the practical way to preserve scanned receipts from Apple Notes.
- It relies on Notes UI scripting for the final export step.
- Required macOS permissions may include:
  - Automation access for Notes
  - Accessibility access for Terminal / your shell / `osascript`
- If Dropbox exists in both `~/Dropbox` and `~/Library/CloudStorage/Dropbox`, prefer `~/Dropbox` unless the user says otherwise.
