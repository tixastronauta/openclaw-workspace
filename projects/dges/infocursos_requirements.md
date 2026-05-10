# InfoCursos scraping requirements

Started: 2026-05-10

This document records the current requirements for enriching the `dges_cursos_2026` Google Sheet with InfoCursos statistics.

## Target sheet

- Spreadsheet: `1m7LzrYoYTrCHYr3vBiaeK62ZOw-4GQVCbXse6d5FE6E`
- Tab: `dges_cursos_2026`

## Safety rules

- Never remove existing information from the sheet.
- Add new columns only at the end of the sheet unless Tiago explicitly says otherwise.
- When updating a course row, always update `updated_at` with date and time.
- Use Europe/Lisbon time for `updated_at`.
- Current timestamp format: `YYYY-MM-DD HH:MM:SS ZZZ` (example: `2026-05-10 19:44:24 WEST`).

## InfoCursos fields to scrape

Create/store these fields as JSON columns:

- `infocursos_iefp_desemprego_json`
- `infocursos_taxa_conclusao_json`
- `infocursos_classificacoes_finais_json`
- `infocursos_sexo_curso_json`
- `infocursos_nacionalidade_curso_json`
- `infocursos_idades_json`

## JSON shape

Do not store `source_url` inside the JSON cells; the sheet already has `estatisticas_do_curso`.

Use:

```json
{
  "available": true,
  "rows": []
}
```

When InfoCursos says the data is unavailable, use:

```json
{
  "available": false,
  "message": "Official InfoCursos message here"
}
```

If a specific chart exists but has no rows for the requested scope, use:

```json
{
  "available": false,
  "rows": []
}
```

## Description field

### course_description

For large-scale fills, derive `course_description` from official DGES course-detail fields in `detalhes_do_curso`.

Preferred concise shape:

- `<grau> de <duração> e <ects> ECTS na área <Área CNAEF>.`

This keeps the text factual and avoids inventing marketing copy when an institution-specific presentation page is not being scraped.

## Field-specific requirements

### IEFP unemployment

For `infocursos_iefp_desemprego_json`, store only the row where `Desemprego == "Curso"`.

Do not store comparison rows such as:

- `Área de formação (Público)`
- `Nacional (Público)`

### Sex distribution

For `infocursos_sexo_curso_json`, store only the `Curso` row.

### Nationality distribution

For `infocursos_nacionalidade_curso_json`, store only the `Curso` row.

### Completion rate

If the completion-rate chart is unavailable, preserve the official InfoCursos unavailability message with `available:false`.

## Pilot scope already used

Initial validation scope: 11 courses from `Universidade do Porto - Faculdade de Engenharia` / `FEUP`.
