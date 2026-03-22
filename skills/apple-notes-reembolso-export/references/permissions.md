# Permissions and caveats

This skill depends on macOS UI scripting for the final PDF export step.

## Required permissions

- Notes automation access
- Accessibility access for the host app that runs `osascript` (often Terminal, iTerm, or the controlling app)
- In some setups, System Events may also need permission approval

## Symptom

If export fails with an error like `osascript is not allowed assistive access (-1719)`, grant Accessibility access in:

System Settings → Privacy & Security → Accessibility

Then retry the export.

## Practical caveat

The export step uses the English menu label `Export as PDF…`. If the macOS UI language differs, the script may need a localized menu label.
