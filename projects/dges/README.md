# DGES

Started: 2026-04-22

Project for DGES-related crawling, extraction, and processing work. It contains the project scripts plus the source and generated data used to analyze DGES course and admissions materials.

## InfoCursos enrichment

InfoCursos scraping requirements are documented in `infocursos_requirements.md`.
The reusable updater script is `scrape_infocursos_to_sheet.py`; it updates only matching rows, writes InfoCursos JSON columns, and refreshes `updated_at` with date and time in Europe/Lisbon.
