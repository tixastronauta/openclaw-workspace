# Project Instructions

Scope: this file applies to the `site-universidade` project only. Keep changes inside this project unless the user explicitly asks otherwise.

## Project Summary

- Static-first Next.js site for universidade.pt.
- Source of truth is `data/courses.csv`, generated from spreadsheet data.
- The app is exported statically to `out/` and deployed on Cloudflare Pages.

## Working Rules

- Prefer small, focused changes that preserve the current structure and SEO behavior.
- Do not invent course, institution, district, or grade data; omit missing values instead.
- Keep routes crawlable and static. Avoid adding runtime APIs, SSR, or long-running services.
- Use the existing stack: Next.js App Router, TypeScript, Tailwind CSS, Papa Parse, and Recharts.
- When adding or changing data logic, keep the CSV contract in sync with `README.md`.

## Common Commands

- `npm run dev` for local development.
- `npm run typecheck` for TypeScript validation.
- `npm run lint` for linting.
- `npm run build` to verify the static export.

## Editing Guidance

- Prefer minimal edits to the owning file or component.
- Keep metadata, sitemap, robots, breadcrumbs, and canonical URLs intact unless the task explicitly changes SEO behavior.
- If a change affects generated pages or data loading, validate the narrowest relevant path first, then run a broader build check if needed.