# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**universidade.pt** — a static directory of Portuguese higher-education courses, built from a Google Sheets–sourced CSV and deployed to Cloudflare Pages as a fully static Next.js export.

## Commands

```bash
npm run dev          # local dev server at localhost:3000
npm run typecheck    # TypeScript validation (no emit)
npm run lint         # ESLint
npm run build        # static export → out/
npm run import:sheet # pull latest data from Google Sheet into data/courses.csv (requires gog CLI)
```

Build produces `out/`. There are no tests. The primary correctness check is `npm run typecheck && npm run lint && npm run build`.

## Architecture

### Data flow

`data/courses.csv` is the single source of truth. At build time (and during `dev`), `lib/courses.ts` reads and parses it synchronously via Papa Parse. The CSV contains JSON-encoded columns (`nota_ult_col_json`, `infocursos_*_json`) that are decoded by the loader into typed sub-models. There is no database, no API, and no runtime data fetching.

All derived entities — `Faculty`, `District` — are computed from `Course` rows in `lib/courses.ts`. Slugs are deterministic (derived from course name + institution name + codes via `lib/slug.ts`) with a counter suffix to disambiguate collisions.

### Page generation

All pages use Next.js App Router with `generateStaticParams()` so the entire site renders at build time. The output format is `"export"` (set in `next.config.ts`); SSR and middleware are not available.

Entity hierarchy: **Course** → grouped by institution into **Faculty** → grouped by `distrito` into **District**.

### Key library files

- `lib/courses.ts` — CSV parsing, normalization, all data-access functions (`getAllCourses`, `getAllFaculties`, `getAllDistricts`, `getRelatedCourses`, etc.)
- `lib/top10.ts` — ranking logic over `Course.metrics` for the `/top-10` page
- `lib/site.ts` — shared site metadata constants
- `lib/slug.ts` — `slugify()` utility used for all URL generation
- `lib/portugalDistrictPaths.ts` — SVG path data for the interactive district map

### Constraints

- Keep routes **static and crawlable**. Do not add SSR, runtime APIs, or middleware.
- Missing data is **omitted**, never invented. If a CSV field is absent, the UI hides that section.
- The CSV contract (column names and JSON shapes) is documented in `README.md`. Keep it in sync when changing the loader.
- `institution_sigla` is loaded for search matching but intentionally not shown in the UI.
- Ad placements exist in `components/AdSlot.tsx` but render only when `NEXT_PUBLIC_ENABLE_AD_SLOTS=true`.

### Updating data

Do **not** run `npm run import:sheet` directly. The script requires the `gog` CLI and OAuth credentials only available inside the container. Always sync via:

```bash
docker compose exec openclaw-1 /usr/local/bin/node /data/.openclaw/workspace/projects/site-universidade/scripts/sync-courses-from-sheet.mjs
```

Default sheet: `dges_cursos_2026` in spreadsheet `1m7LzrYoYTrCHYr3vBiaeK62ZOw-4GQVCbXse6d5FE6E`.
