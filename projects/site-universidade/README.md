# site-universidade

Static-first MVP for **universidade.pt**: an independent directory of higher-education courses in Portugal generated from spreadsheet data.

Started: 2026-05-10

## Stack

- Next.js App Router
- TypeScript
- Tailwind CSS
- Static export with `output: "export"`
- CSV build-time data loading with Papa Parse
- Cloudflare Pages deployment serving the generated `out/` directory

## Routes

- `/` — homepage with search and introductory content
- `/cursos/` — crawlable course index grouped alphabetically
- `/cursos/[slug]/` — static course detail pages generated from CSV rows
- `/faculdades/` — faculty/institution index generated from institution fields
- `/faculdades/[slug]/` — static faculty pages listing that institution's courses
- `/distritos/` — district index with counts for institutions and courses
- `/distritos/[slug]/` — static district pages listing institutions and courses in that district
- `/sobre/`
- `/contacto/`
- `/privacidade/`
- `/termos/`
- `/fontes-oficiais/`
- `/sitemap.xml`
- `/robots.txt`

## Data contract

The v0.1 source of truth is `data/courses.csv`, exported from this Google Sheet:

<https://docs.google.com/spreadsheets/d/1m7LzrYoYTrCHYr3vBiaeK62ZOw-4GQVCbXse6d5FE6E/edit?gid=13716#gid=13716>

Current spreadsheet columns:

```csv
updated_at,course_code,course_name,cycle,institution_code,institution_name,institution_sigla,reference,estatisticas_do_curso,detalhes_do_curso,nota_ult_col_2023_1a,nota_ult_col_2023_2a,nota_ult_col_2024_1a,nota_ult_col_2024_2a,nota_ult_col_2025_1a,nota_ult_col_2025_2a,infocursos_iefp_desemprego_json,infocursos_taxa_conclusao_json,infocursos_classificacoes_finais_json,infocursos_sexo_curso_json,infocursos_nacionalidade_curso_json,infocursos_idades_json,course_description,nota_ult_col_json,cidade,distrito,morada
```

The loader also accepts common aliases for the course name and official URL columns. Grade columns are detected when they follow the DGES spreadsheet format `nota_ult_col_YYYY_1a` / `nota_ult_col_YYYY_2a`, or simpler fallback patterns such as `entryGrade2024`, `entry_grade2024`, `grade2024`, `nota2024`, or `nota_entrada2024`.

If a value is missing, the site omits it rather than inventing content. `institution_sigla` is loaded for search matching but intentionally not displayed in the UI.

## Local development

```bash
npm install
npm run dev
```

Open <http://localhost:3000>.

## Updating spreadsheet data

Use `gog` to read the Google Sheet through OAuth and update `data/courses.csv`:

```bash
npm run import:sheet
```

Optional overrides:

```bash
GOG_ACCOUNT="you@example.com" GOOGLE_SHEET_ID="..." GOOGLE_SHEET_NAME="dges_cursos_2026" npm run import:sheet
```

If `gog` is not available in an environment, export/download the sheet manually as CSV and replace `data/courses.csv`.

## Page generation

At build time, `lib/courses.ts` reads `data/courses.csv`, normalizes rows into a minimal `Course` model, creates deterministic slugs, and exposes:

- `getAllCourses()` for the homepage, course index, sitemap, and static params
- `getCourseBySlug()` for course detail pages
- `getRelatedCourses()` for internal links prioritizing same course name, same institution, and same cycle
- `getAllFaculties()` for the faculty index, sitemap, and static params
- `getFacultyBySlug()` for faculty detail pages
- `getAllDistricts()` for district pages, sitemap, and the homepage map
- `getDistrictBySlug()` / `getCoursesByDistrict()` for district detail pages

Course, faculty, cycle, and district pages are generated statically via `generateStaticParams()`.

## SEO basics included

- Human-readable course URLs
- Unique page titles and meta descriptions
- Canonical metadata
- Open Graph basics
- H1/H2 page structure
- Breadcrumb UI
- Static sitemap and robots.txt
- Course schema JSON-LD on detail pages
- Crawlable links in course, faculty, and related-course sections

## Ads

Ad slot placements are kept in the code through `components/AdSlot.tsx`, but they do not render by default.

To render internal ad placeholders in a future environment, set:

```bash
NEXT_PUBLIC_ENABLE_AD_SLOTS=true
```

No ad network code is integrated yet.

## Build

```bash
npm run typecheck
npm run lint
npm run build
```

The static site is emitted to `out/`.

## Cloudflare Pages deployment

Recommended Cloudflare Pages settings:

- Framework preset: Next.js (static export) or None
- Build command: `npm run build`
- Build output directory: `out`
- Node version: `22`

`wrangler.toml` includes:

```toml
name = "site-universidade"
pages_build_output_dir = "out"
compatibility_date = "2026-05-10"
```

No runtime database, authentication, API server, SSR, or long-running process is required for v0.1.
