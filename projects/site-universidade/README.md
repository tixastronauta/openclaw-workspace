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

Current CSV columns are kept in this order. When the Google Sheet adds columns,
the sync script appends those new columns to the end of `data/courses.csv`
instead of reordering or renaming existing CSV columns:

```csv
updated_at,course_code,course_name,course_description,cycle,institution_code,parent_institution_name,parent_institution_acronym,institution_name,institution_sigla,institution_name_full,reference,estatisticas_do_curso,detalhes_do_curso,infocursos_iefp_desemprego_json,infocursos_classificacoes_finais_json,infocursos_sexo_curso_json,infocursos_nacionalidade_curso_json,infocursos_idades_json,nota_ult_col_json,cidade,distrito,morada,institution_url,course_url,Telefone,Area CNAEF,Duração,ECTS,Tipo de Ensino,Concurso,Vagas,Provas de Ingresso,Classificações Mínimas
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

Use `gog` to read the Google Sheet through OAuth, update `data/courses.csv`, validate `course_description`, and regenerate `public/search-index.json`:

```bash
npm run sync:courses
```

`npm run import:sheet` is kept as an alias for the same sync.

Optional overrides:

```bash
GOG_ACCOUNT="you@example.com" GOOGLE_SHEET_ID="..." GOOGLE_SHEET_NAME="dges_cursos_2026" npm run sync:courses
```

If `gog` is not available in an environment, export/download the sheet manually as CSV and replace `data/courses.csv`, then run `node scripts/generate-search-index.mjs`.

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

### First-time setup (once per machine)

```bash
npm install -g wrangler
wrangler login                          # opens browser, saves credentials locally
wrangler pages project create site-universidade   # when prompted, set production branch to: main
```

### Deploy to staging

Staging deploys go to a preview URL (`https://staging.site-universidade.pages.dev`). The final domain is not affected.

```bash
NEXT_PUBLIC_SITE_URL=https://staging.site-universidade.pages.dev npm run build
wrangler pages deploy out --branch staging
```

`NEXT_PUBLIC_SITE_URL` must be set so that `og:image` and other absolute URLs resolve to the staging domain instead of production. The deploy command prints the preview URL on completion.

### Deploy to production

Production deploys go to the `main` branch, which serves the custom domain once it is wired up in the Cloudflare Pages dashboard.

```bash
npm run build
wrangler pages deploy out --branch main
```

### Cloudflare Pages dashboard settings

If building via the dashboard instead of Wrangler CLI:

- Framework preset: **None** (static export, not Next.js SSR)
- Build command: `npm run build`
- Build output directory: `out`
- Node.js version: `22`

`wrangler.toml` is already configured:

```toml
name = "site-universidade"
pages_build_output_dir = "out"
compatibility_date = "2026-05-10"
```

No runtime database, authentication, API server, SSR, or long-running process is required.
