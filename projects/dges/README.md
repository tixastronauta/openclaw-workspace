# DGES

Started: 2026-04-22

Project for DGES-related crawling, extraction, and processing work. It contains the project scripts plus the source and generated data used to analyze DGES course and admissions materials.

## Working spreadsheet

The crawl/enrichment work writes to the shared Google Sheets spreadsheet used as the working data store:

- Spreadsheet: `1m7LzrYoYTrCHYr3vBiaeK62ZOw-4GQVCbXse6d5FE6E`
- Main sheet/range used by the scripts: `dges_cursos_2026`
- URL: <https://docs.google.com/spreadsheets/d/1m7LzrYoYTrCHYr3vBiaeK62ZOw-4GQVCbXse6d5FE6E/edit?gid=13716>

When updating it from scripts, prefer narrow row/column range updates and avoid overwriting entire rows, because other processes may be enriching different columns at the same time.

## InfoCursos enrichment

InfoCursos scraping requirements are documented in `infocursos_requirements.md`.
The reusable updater script is `scrape_infocursos_to_sheet.py`; it updates only matching rows, writes InfoCursos JSON columns, and refreshes `updated_at` with date and time in Europe/Lisbon.

## Entry-score backfill

`backfill_entry_scores_from_2020.py` extends `nota_ult_col_json` with official DGES last-admitted scores from 2020 onward, using the historical DGES statistical PDFs and keeping the legacy note columns untouched.

## Course-detail backfill

`backfill_course_details.py` enriches the working sheet from each `detalhes_do_curso` URL. It appends the requested course-detail columns at the end of `dges_cursos_2026`, updates only those columns plus `updated_at`, keeps resumable state in `data/`, and maintains the `area_cnaef` tab as a unique list of CNAEF areas.
