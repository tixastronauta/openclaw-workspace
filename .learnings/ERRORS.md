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
