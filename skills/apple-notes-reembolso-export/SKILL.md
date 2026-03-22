---
name: apple-notes-reembolso-export
description: Export Apple Notes from the smart folder `RTF Reembolsos` to PDF files in Dropbox using the note date and note name in the filename. Use when asked to automate exporting reimbursement receipt notes from Apple Notes, save reimbursement notes as PDFs, or batch-export Apple Notes receipt scans into Dropbox.
---

# Apple Notes Reembolso Export

Use this skill to export Apple Notes from the smart folder `RTF Reembolsos` into Dropbox as PDF files.

## Workflow

1. Run the bundled script in `scripts/export_reembolso_notes.py`.
2. Start with `--dry-run` to confirm which notes are in the smart folder and what filenames will be generated.
3. If the dry run looks correct, run without `--dry-run` to export PDFs.
4. If the export fails with an Accessibility or UI scripting error, tell the user to grant Accessibility access to `osascript` / Terminal and retry.

## Default behavior

- Use the Apple Notes smart folder `RTF Reembolsos` as the source of truth.
- Enumerate notes directly from that smart folder.
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

Custom smart folder / destination root:

```bash
python3 skills/apple-notes-reembolso-export/scripts/export_reembolso_notes.py \
  --folder "RTF Reembolsos" \
  --dest-root "$HOME/Dropbox/Reticências Fenomenais/Documentos para a contabilidade"
```

## Notes

- This workflow exports the **entire note as a PDF**. That is the practical way to preserve scanned receipts from Apple Notes.
- It relies on Notes UI scripting for the final export step.
- Required macOS permissions may include:
  - Automation access for Notes
  - Accessibility access for Terminal / your shell / `osascript`
- If Dropbox exists in both `~/Dropbox` and `~/Library/CloudStorage/Dropbox`, prefer `~/Dropbox` unless the user says otherwise.
