# Errors

Use this file for meaningful failures that Nyx should learn from.

Log here only when the failure is repeatable, costly, confusing, or likely to happen again.
Do not flood this file with every harmless transient hiccup.

## Entry template

## [ERR-YYYYMMDD-XXX] short-title

- Logged: ISO-8601 timestamp
- Status: pending | mitigated | resolved | ignored
- Area: permissions | messaging | files | automation | tools | platform
- Severity: low | medium | high
- Reproducible: yes | no | unknown
- Summary: one-line description of the failure
- Action: concrete mitigation or next step
- Promote to: AGENTS.md | TOOLS.md | none
- See also: optional related IDs

### Context
What was attempted, what failed, and under which conditions.

### Error
Paste the relevant error text or summarize it exactly.

---

## [ERR-20260323-001] wrote-daily-memory-to-wrong-date-file

- Logged: 2026-03-23T14:47:00+00:00
- Status: pending
- Area: files
- Severity: medium
- Reproducible: yes
- Summary: Wrote 2026-03-23 notes into `memory/2026-03-22.md` instead of today's file.
- Action: When writing daily memory, verify today's date first and create/use the matching `memory/YYYY-MM-DD.md` file.
- Promote to: AGENTS.md
- See also: none

### Context
After creating the setup todo and lightweight learning system, I appended 2026-03-23 notes into the previous day's daily memory file because I did not verify the date before writing.

### Error
Used `memory/2026-03-22.md` for events that happened on 2026-03-23.

---
