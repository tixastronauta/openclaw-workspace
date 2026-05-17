import fs from "node:fs";
import path from "node:path";
import Papa from "papaparse";
import { slugify } from "./slug";

export type AdmissionGrade = {
  year: string;
  phase?: string;
  grade: string;
};

export type VacancyHistoryPoint = {
  year: string;
  phase: string;
  vacancies: number;
};

export type CourseMetrics = {
  unemploymentRate?: number;
  unemployedCount?: number;
  graduatesCount?: number;
  finalAverage?: number;
  menShare?: number;
  womenShare?: number;
  foreignerShare?: number;
  ageAverage?: number;
  entryGradeAverage?: number;
};

export type GradeDistributionItem = {
  grade: string;
  students: number;
  percentage: number;
};

export type AgeDistributionItem = {
  age: string;
  students: number;
  percentage: number;
};

export type GenderData = {
  men: number;
  women: number;
};

export type NationalityData = {
  portuguese: number;
  foreign: number;
};

export type Course = {
  slug: string;
  courseCode?: string;
  courseName: string;
  cycle?: string;
  institutionCode?: string;
  institutionName?: string;
  institutionSigla?: string;
  institutionUrl?: string;
  courseUrl?: string;
  cidade?: string;
  distrito?: string;
  morada?: string;
  reference?: string;
  grades: AdmissionGrade[];
  vacancies?: VacancyHistoryPoint[];
  courseDescription?: string;
  infoCursosUrl?: string;
  dgesUrl?: string;
  metrics?: CourseMetrics;
  finalGradesDistribution?: GradeDistributionItem[];
  ageDistribution?: AgeDistributionItem[];
  genderData?: GenderData;
  nationalityData?: NationalityData;
  parentInstitutionName?: string;
  parentInstitutionAcronym?: string;
  areaCnaef?: string;
  duracao?: string;
  tipoEnsino?: string;
  ects?: string;
  provasIngresso?: { sets: { code: string; name: string }[][] };
};

type CsvRow = Record<string, string | undefined>;

const CSV_PATH = path.join(process.cwd(), "data", "courses.csv");
let allCoursesCache: Course[] | undefined;

function clean(value: string | undefined): string | undefined {
  const trimmed = value?.trim();
  return trimmed ? trimmed : undefined;
}

function getFirst(row: CsvRow, keys: string[]): string | undefined {
  for (const key of keys) {
    const value = clean(row[key]);
    if (value) return value;
  }
  return undefined;
}

function phaseLabel(phase: string): string {
  const match = phase.match(/^(\d+)a$/i);
  if (match) return `${match[1]}.ª fase`;
  return phase;
}

function extractGrades(row: CsvRow): AdmissionGrade[] {
  const raw = clean(row.nota_ult_col_json);
  if (!raw) return [];

  try {
    const parsed = JSON.parse(raw) as Record<string, Record<string, unknown> | unknown>;

    return Object.entries(parsed)
      .flatMap(([year, phases]) => {
        if (!/^\d{4}$/.test(year) || typeof phases !== "object" || phases === null || Array.isArray(phases)) return [];

        const grades: AdmissionGrade[] = [];

        for (const [phase, value] of Object.entries(phases as Record<string, unknown>)) {
          const grade = clean(String(value ?? ""));
          if (!grade) continue;

          grades.push({
            year,
            phase: phaseLabel(phase),
            grade
          });
        }

        return grades;
      })
      .sort((a, b) => Number(a.year) - Number(b.year) || (a.phase ?? "").localeCompare(b.phase ?? "", "pt"));
  } catch {
    return [];
  }
}

function yearOrder(value: string): number {
  const match = value.match(/\d{4}/);
  return match ? Number(match[0]) : 0;
}

function extractVacancies(row: CsvRow): VacancyHistoryPoint[] | undefined {
  const raw = clean(row.Vagas);
  if (!raw) return undefined;

  try {
    const parsed = JSON.parse(raw) as {
      current?: { year?: unknown; vagas?: unknown };
      historical?: Record<string, Record<string, unknown> | unknown>;
    };

    const history: VacancyHistoryPoint[] = [];

    if (parsed.historical && typeof parsed.historical === "object") {
      for (const [year, phases] of Object.entries(parsed.historical)) {
        if (!/^\d{4}$/.test(year) || typeof phases !== "object" || phases === null || Array.isArray(phases)) continue;

        for (const [phase, value] of Object.entries(phases as Record<string, unknown>)) {
          const vacancies = numberValue(value);
          if (vacancies === undefined) continue;

          history.push({
            year,
            phase: phaseLabel(phase),
            vacancies
          });
        }
      }
    }

    if (history.length === 0) return undefined;

    return history.sort((a, b) => yearOrder(a.year) - yearOrder(b.year) || a.phase.localeCompare(b.phase, "pt"));
  } catch {
    return undefined;
  }
}

function parseJsonObject(value: string | undefined): Record<string, unknown> | undefined {
  const raw = clean(value);
  if (!raw) return undefined;

  try {
    const parsed = JSON.parse(raw) as unknown;
    if (typeof parsed === "object" && parsed !== null && !Array.isArray(parsed)) return parsed as Record<string, unknown>;
  } catch {
    return undefined;
  }

  return undefined;
}

function rowsFromJson(value: string | undefined): Record<string, unknown>[] {
  const parsed = parseJsonObject(value);
  const rows = parsed?.rows;
  if (!Array.isArray(rows)) return [];
  return rows.filter((row): row is Record<string, unknown> => typeof row === "object" && row !== null && !Array.isArray(row));
}

function numberValue(value: unknown): number | undefined {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number.parseFloat(value.replace(",", "."));
    if (Number.isFinite(parsed)) return parsed;
  }
  return undefined;
}

function weightedFinalAverage(row: CsvRow): number | undefined {
  const rows = rowsFromJson(row.infocursos_classificacoes_finais_json);
  let totalWeight = 0;
  let total = 0;

  for (const item of rows) {
    const grade = numberValue(item["Nota final"]);
    const students = numberValue(item.Alunos);
    const percentage = numberValue(item.Percentagem);
    const weight = students && students > 0 ? students : percentage;
    if (grade === undefined || weight === undefined || weight <= 0) continue;
    total += grade * weight;
    totalWeight += weight;
  }

  return totalWeight > 0 ? total / totalWeight : undefined;
}

function ageMidpoint(age: unknown): number | undefined {
  if (typeof age !== "string") return undefined;
  if (age === "<=18") return 18;
  if (age === ">=40") return 40;
  const range = age.match(/^(\d+)-(\d+)$/);
  if (range) return (Number(range[1]) + Number(range[2])) / 2;
  return numberValue(age);
}

function weightedAgeAverage(row: CsvRow): number | undefined {
  const rows = rowsFromJson(row.infocursos_idades_json);
  let totalWeight = 0;
  let total = 0;

  for (const item of rows) {
    const age = ageMidpoint(item.Idade);
    const students = numberValue(item.Alunos);
    const percentage = numberValue(item.Percentagem);
    const weight = students && students > 0 ? students : percentage;
    if (age === undefined || weight === undefined || weight <= 0) continue;
    total += age * weight;
    totalWeight += weight;
  }

  return totalWeight > 0 ? total / totalWeight : undefined;
}

function extractFinalGradesDistribution(row: CsvRow): GradeDistributionItem[] | undefined {
  const rows = rowsFromJson(row.infocursos_classificacoes_finais_json);
  if (rows.length === 0) return undefined;
  const items: GradeDistributionItem[] = rows
    .map((item) => ({
      grade: String(item["Nota final"] ?? ""),
      students: numberValue(item.Alunos) ?? 0,
      percentage: numberValue(item.Percentagem) ?? 0
    }))
    .filter((item) => item.grade !== "");
  return items.length > 0 ? items : undefined;
}

function extractAgeDistribution(row: CsvRow): AgeDistributionItem[] | undefined {
  const rows = rowsFromJson(row.infocursos_idades_json);
  if (rows.length === 0) return undefined;
  const items: AgeDistributionItem[] = rows
    .map((item) => ({
      age: String(item.Idade ?? ""),
      students: numberValue(item.Alunos) ?? 0,
      percentage: numberValue(item.Percentagem) ?? 0
    }))
    .filter((item) => item.age !== "");
  return items.length > 0 ? items : undefined;
}

function extractGenderData(row: CsvRow): GenderData | undefined {
  const sexRow = rowsFromJson(row.infocursos_sexo_curso_json).find((item) => item.Sexo === "Curso");
  if (!sexRow) return undefined;
  const men = numberValue(sexRow.Homens);
  const women = numberValue(sexRow.Mulheres);
  if (men === undefined && women === undefined) return undefined;
  return { men: men ?? 0, women: women ?? 0 };
}

function latestEntryGradeAverage(row: CsvRow): number | undefined {
  const raw = clean(row.nota_ult_col_json);
  if (!raw) return undefined;
  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    const years = Object.keys(parsed)
      .filter((y) => /^\d{4}$/.test(y))
      .sort((a, b) => Number(b) - Number(a));
    for (const year of years) {
      const phases = parsed[year];
      if (typeof phases !== "object" || phases === null || Array.isArray(phases)) continue;
      const values = Object.values(phases as Record<string, unknown>)
        .map((v) => numberValue(String(v ?? "")))
        .filter((v): v is number => v !== undefined && v > 0);
      if (values.length === 0) continue;
      return values.reduce((sum, v) => sum + v, 0) / values.length / 10;
    }
  } catch {
    return undefined;
  }
  return undefined;
}

function extractNationalityData(row: CsvRow): NationalityData | undefined {
  const natRow = rowsFromJson(row.infocursos_nacionalidade_curso_json).find((item) => item.Nacionalidade === "Curso");
  if (!natRow) return undefined;
  const portuguese = numberValue(natRow.Portugueses);
  const foreign = numberValue(natRow.Estrangeiros);
  if (portuguese === undefined && foreign === undefined) return undefined;
  return { portuguese: portuguese ?? 0, foreign: foreign ?? 0 };
}

function extractMetrics(row: CsvRow): CourseMetrics {
  const unemployment = rowsFromJson(row.infocursos_iefp_desemprego_json).find((item) => item.Desemprego === "Curso");
  const sex = rowsFromJson(row.infocursos_sexo_curso_json).find((item) => item.Sexo === "Curso");
  const nationality = rowsFromJson(row.infocursos_nacionalidade_curso_json).find((item) => item.Nacionalidade === "Curso");

  return {
    unemploymentRate: numberValue(unemployment?.Taxa),
    unemployedCount: numberValue(unemployment?.Desempregados),
    graduatesCount: numberValue(unemployment?.Diplomados),
    finalAverage: weightedFinalAverage(row),
    menShare: numberValue(sex?.Homens),
    womenShare: numberValue(sex?.Mulheres),
    foreignerShare: numberValue(nationality?.Estrangeiros),
    ageAverage: weightedAgeAverage(row),
    entryGradeAverage: latestEntryGradeAverage(row)
  };
}

function extractProvasIngresso(row: CsvRow): { sets: { code: string; name: string }[][] } | undefined {
  const raw = clean(row["Provas de Ingresso"]);
  if (!raw) return undefined;
  try {
    const parsed = JSON.parse(raw) as { sets?: unknown };
    if (!Array.isArray(parsed.sets) || parsed.sets.length === 0) return undefined;
    const sets = (parsed.sets as unknown[][]).map((set) =>
      (Array.isArray(set) ? set : []).filter(
        (item): item is { code: string; name: string } =>
          typeof item === "object" && item !== null && typeof (item as Record<string, unknown>).name === "string"
      )
    ).filter((set) => set.length > 0);
    return sets.length > 0 ? { sets } : undefined;
  } catch {
    return undefined;
  }
}

function normalizeDuracao(value: string | undefined): string | undefined {
  if (!value) return undefined;
  return value.replace(/\b\w/g, (c) => c.toLocaleUpperCase("pt"));
}

function uniqueSlugs(courses: Omit<Course, "slug">[]): Course[] {
  const seen = new Map<string, number>();

  return courses.map((course) => {
    const baseSlug = slugify([course.courseName, course.institutionName, course.courseCode, course.institutionCode].filter(Boolean).join(" "));
    const count = seen.get(baseSlug) ?? 0;
    seen.set(baseSlug, count + 1);

    return {
      ...course,
      slug: count === 0 ? baseSlug : `${baseSlug}-${count + 1}`
    };
  });
}

export function getAllCourses(): Course[] {
  if (allCoursesCache) return allCoursesCache;

  const csv = fs.readFileSync(CSV_PATH, "utf8");
  const parsed = Papa.parse<CsvRow>(csv, {
    header: true,
    skipEmptyLines: true
  });

  const courses: Omit<Course, "slug">[] = [];

  for (const row of parsed.data) {
    const courseName = getFirst(row, ["courseName", "course_name", "nome", "nomeCurso", "curso"]);
    if (!courseName) continue;

    courses.push({
      courseCode: getFirst(row, ["courseCode", "course_code", "codc"]),
      courseName,
      cycle: getFirst(row, ["cycle", "ciclo"]),
      institutionCode: getFirst(row, ["institutionCode", "institution_code", "code"]),
      institutionName: getFirst(row, ["institutionName", "institution_name", "instituicao"]),
      institutionSigla: getFirst(row, ["institutionSigla", "institution_sigla", "sigla"]),
      institutionUrl: getFirst(row, ["institutionUrl", "institution_url", "url_instituicao"]),
      courseUrl: getFirst(row, ["courseUrl", "course_url", "url_curso"]),
      parentInstitutionName: getFirst(row, ["parent_institution_name", "parentInstitutionName"]),
      parentInstitutionAcronym: getFirst(row, ["parent_institution_acronym", "parentInstitutionAcronym"]),
      cidade: getFirst(row, ["cidade"]),
      distrito: getFirst(row, ["distrito"]),
      morada: getFirst(row, ["morada"]),
      reference: getFirst(row, ["reference", "referencia"]),
      grades: extractGrades(row),
      vacancies: extractVacancies(row),
      courseDescription: getFirst(row, ["courseDescription", "course_description"]),
      infoCursosUrl: getFirst(row, ["infoCursosUrl", "infocursosUrl", "info_cursos_url", "InfoCursos", "estatisticas_do_curso"]),
      dgesUrl: getFirst(row, ["dgesUrl", "dges_url", "DGES", "detalhes_do_curso"]),
      metrics: extractMetrics(row),
      finalGradesDistribution: extractFinalGradesDistribution(row),
      ageDistribution: extractAgeDistribution(row),
      genderData: extractGenderData(row),
      nationalityData: extractNationalityData(row),
      areaCnaef: getFirst(row, ["Area CNAEF"]),
      duracao: normalizeDuracao(getFirst(row, ["Duração"])),
      tipoEnsino: getFirst(row, ["Tipo de Ensino"]),
      ects: getFirst(row, ["ECTS"]),
      provasIngresso: extractProvasIngresso(row)
    });
  }

  courses.sort((a, b) =>
    a.courseName.localeCompare(b.courseName, "pt") ||
    (a.institutionName ?? "").localeCompare(b.institutionName ?? "", "pt")
  );

  allCoursesCache = uniqueSlugs(courses);
  return allCoursesCache;
}

export function getCourseBySlug(slug: string): Course | undefined {
  return getAllCourses().find((course) => course.slug === slug);
}

export function getRelatedCourses(course: Course, limit = 4): Course[] {
  const allCourses = getAllCourses().filter((item) => item.slug !== course.slug);
  const sameCourse = allCourses.filter((item) => item.courseName === course.courseName);
  const sameInstitution = allCourses.filter((item) => item.institutionName && item.institutionName === course.institutionName && item.courseName !== course.courseName);
  const sameCycle = allCourses.filter((item) => item.cycle && item.cycle === course.cycle && !sameCourse.some((same) => same.slug === item.slug) && !sameInstitution.some((same) => same.slug === item.slug));
  const fallback = allCourses.filter((item) => ![...sameCourse, ...sameInstitution, ...sameCycle].some((same) => same.slug === item.slug));

  return [...sameCourse, ...sameInstitution, ...sameCycle, ...fallback].slice(0, limit);
}

export function getCourseInitials(): string[] {
  return Array.from(new Set(getAllCourses().map((course) => course.courseName[0]?.toLocaleUpperCase("pt")).filter(Boolean))).sort((a, b) => a.localeCompare(b, "pt"));
}

export function getCycles(): string[] {
  return Array.from(new Set(getAllCourses().map((course) => course.cycle).filter((cycle): cycle is string => Boolean(cycle)))).sort((a, b) => a.localeCompare(b, "pt"));
}

export function getCoursesByCycle(cycle: string): Course[] {
  return getAllCourses().filter((course) => course.cycle === cycle);
}

export type Faculty = {
  slug: string;
  institutionCode?: string;
  institutionName: string;
  institutionSigla?: string;
  institutionUrl?: string;
  cidade?: string;
  distrito?: string;
  morada?: string;
  courses: Course[];
  parentInstitutionName?: string;
  parentInstitutionAcronym?: string;
};

export type University = {
  slug: string;
  name: string;
  acronym?: string;
  url?: string;
  faculties: Faculty[];
  courses: Course[];
};

export function getAllFaculties(): Faculty[] {
  const grouped = new Map<string, Course[]>();

  for (const course of getAllCourses()) {
    if (!course.institutionName) continue;
    const key = `${course.institutionName}::${course.institutionCode ?? ""}`;
    grouped.set(key, [...(grouped.get(key) ?? []), course]);
  }

  return Array.from(grouped.values())
    .map((courses) => {
      const first = courses[0];
      return {
        slug: slugify([first.institutionName, first.institutionCode].filter(Boolean).join(" ")),
        institutionCode: first.institutionCode,
        institutionName: first.institutionName as string,
        institutionSigla: first.institutionSigla,
        institutionUrl: first.institutionUrl,
        cidade: first.cidade,
        distrito: first.distrito,
        morada: first.morada,
        courses: courses.sort((a, b) => a.courseName.localeCompare(b.courseName, "pt")),
        parentInstitutionName: first.parentInstitutionName,
        parentInstitutionAcronym: first.parentInstitutionAcronym
      };
    })
    .sort((a, b) => a.institutionName.localeCompare(b.institutionName, "pt"));
}

export function getFacultySlugByInstitution(institutionName?: string, institutionCode?: string): string | undefined {
  if (!institutionName) return undefined;
  return slugify([institutionName, institutionCode].filter(Boolean).join(" "));
}

export function getFacultyBySlug(slug: string): Faculty | undefined {
  return getAllFaculties().find((faculty) => faculty.slug === slug);
}

// ── Universities ─────────────────────────────────────────────────────────────

export function getAllUniversities(): University[] {
  const faculties = getAllFaculties();
  const grouped = new Map<string, { name: string; acronym?: string; url?: string; faculties: Faculty[] }>();

  for (const faculty of faculties) {
    if (faculty.parentInstitutionName) {
      const key = faculty.parentInstitutionName;
      if (!grouped.has(key)) {
        grouped.set(key, { name: key, acronym: faculty.parentInstitutionAcronym, url: faculty.institutionUrl, faculties: [] });
      }
      grouped.get(key)!.faculties.push(faculty);
    } else {
      // standalone institution — is its own university
      const key = `__standalone__${faculty.slug}`;
      grouped.set(key, { name: faculty.institutionName, acronym: faculty.institutionSigla, url: faculty.institutionUrl, faculties: [] });
    }
  }

  // Assign slugs with dedup counter
  const seen = new Map<string, number>();
  const universities: University[] = [];

  for (const [key, group] of grouped) {
    const baseSlug = key.startsWith("__standalone__")
      ? key.slice("__standalone__".length) // reuse existing faculty slug for standalone
      : slugify(group.name);
    const count = seen.get(baseSlug) ?? 0;
    seen.set(baseSlug, count + 1);
    const slug = count === 0 ? baseSlug : `${baseSlug}-${count + 1}`;

    const standaloneKey = key.startsWith("__standalone__") ? key.slice("__standalone__".length) : null;
    const standaloneFaculty = standaloneKey ? faculties.find((f) => f.slug === standaloneKey) : undefined;

    universities.push({
      slug,
      name: group.name,
      acronym: group.acronym,
      url: group.url,
      faculties: group.faculties.sort((a, b) => a.institutionName.localeCompare(b.institutionName, "pt")),
      courses: standaloneFaculty ? standaloneFaculty.courses : []
    });
  }

  return universities.sort((a, b) => a.name.localeCompare(b.name, "pt"));
}

export function getUniversityBySlug(slug: string): University | undefined {
  return getAllUniversities().find((u) => u.slug === slug);
}

export function getUniversityForFaculty(faculty: Faculty): University | undefined {
  return getAllUniversities().find((u) =>
    faculty.parentInstitutionName
      ? u.name === faculty.parentInstitutionName
      : u.slug === faculty.slug
  );
}

// ── Districts ────────────────────────────────────────────────────────────────

export type District = {
  slug: string;
  name: string;
  faculties: Faculty[];
  courseCount: number;
};

export function getAllDistricts(): District[] {
  const courses = getAllCourses();

  // group courses by district
  const byCourse = new Map<string, typeof courses>();
  for (const course of courses) {
    if (!course.distrito) continue;
    byCourse.set(course.distrito, [...(byCourse.get(course.distrito) ?? []), course]);
  }

  return Array.from(byCourse.entries())
    .map(([name, districtCourses]) => {
      // unique faculties in this district
      const facultyMap = new Map<string, Faculty>();
      for (const course of districtCourses) {
        if (!course.institutionName) continue;
        const key = `${course.institutionName}::${course.institutionCode ?? ""}`;
        if (!facultyMap.has(key)) {
          const fslug = slugify([course.institutionName, course.institutionCode].filter(Boolean).join(" "));
          facultyMap.set(key, {
            slug: fslug,
            institutionCode: course.institutionCode,
            institutionName: course.institutionName,
            institutionSigla: course.institutionSigla,
            institutionUrl: course.institutionUrl,
            cidade: course.cidade,
            distrito: course.distrito,
            morada: course.morada,
            courses: []
          });
        }
      }
      return {
        slug: slugify(name),
        name,
        faculties: Array.from(facultyMap.values()).sort((a, b) => a.institutionName.localeCompare(b.institutionName, "pt")),
        courseCount: districtCourses.length
      };
    })
    .sort((a, b) => a.name.localeCompare(b.name, "pt"));
}

export function getDistrictBySlug(slug: string): District | undefined {
  return getAllDistricts().find((d) => d.slug === slug);
}

export function getCoursesByDistrict(slug: string): Course[] {
  const district = getDistrictBySlug(slug);
  if (!district) return [];
  return getAllCourses().filter((c) => c.distrito && slugify(c.distrito) === slug);
}

// ── Área CNAEF ───────────────────────────────────────────────────────────────

export function getAreas(): string[] {
  return Array.from(
    new Set(getAllCourses().map((c) => c.areaCnaef).filter((a): a is string => Boolean(a)))
  ).sort((a, b) => a.localeCompare(b, "pt"));
}

export function getAreaBySlug(slug: string): string | undefined {
  return getAreas().find((a) => slugify(a) === slug);
}

export function getCoursesByArea(slug: string): Course[] {
  return getAllCourses().filter((c) => c.areaCnaef && slugify(c.areaCnaef) === slug);
}

// ── Duração ──────────────────────────────────────────────────────────────────

export function getDuracoes(): string[] {
  return Array.from(
    new Set(getAllCourses().map((c) => c.duracao).filter((d): d is string => Boolean(d)))
  ).sort((a, b) => a.localeCompare(b, "pt"));
}

export function getDuracaoBySlug(slug: string): string | undefined {
  return getDuracoes().find((d) => slugify(d) === slug);
}

export function getCoursesByDuracao(slug: string): Course[] {
  return getAllCourses().filter((c) => c.duracao && slugify(c.duracao) === slug);
}

// ── Tipo de Ensino ───────────────────────────────────────────────────────────

export function getTiposEnsino(): string[] {
  return Array.from(
    new Set(getAllCourses().map((c) => c.tipoEnsino).filter((t): t is string => Boolean(t)))
  ).sort((a, b) => a.localeCompare(b, "pt"));
}

export function getTipoEnsinoBySlug(slug: string): string | undefined {
  return getTiposEnsino().find((t) => slugify(t) === slug);
}

export function getCoursesByTipoEnsino(slug: string): Course[] {
  return getAllCourses().filter((c) => c.tipoEnsino && slugify(c.tipoEnsino) === slug);
}

// ── Provas de Ingresso ───────────────────────────────────────────────────────

export type ProvaIngressoEntry = { code: string; name: string };

export function getAllProvasIngresso(): ProvaIngressoEntry[] {
  const seen = new Map<string, ProvaIngressoEntry>();
  for (const course of getAllCourses()) {
    if (!course.provasIngresso) continue;
    for (const set of course.provasIngresso.sets) {
      for (const prova of set) {
        if (!seen.has(prova.code)) seen.set(prova.code, prova);
      }
    }
  }
  return Array.from(seen.values()).sort((a, b) => a.name.localeCompare(b.name, "pt"));
}

export function getProvaIngressoBySlug(slug: string): ProvaIngressoEntry | undefined {
  return getAllProvasIngresso().find((p) => slugify(p.name) === slug);
}

export function getCoursesByProvaIngresso(slug: string): Course[] {
  return getAllCourses().filter((c) =>
    c.provasIngresso?.sets.some((set) => set.some((p) => slugify(p.name) === slug))
  );
}

// ── Conjuntos de provas ───────────────────────────────────────────────────────

export type ProvaSetEntry = {
  slug: string;
  provas: { code: string; name: string }[];
};

export function provaSetSlug(set: { code: string; name: string }[]): string {
  return [...set].sort((a, b) => a.code.localeCompare(b.code)).map((p) => slugify(p.name)).join("-e-");
}

export function getAllProvaSets(): ProvaSetEntry[] {
  const seen = new Map<string, ProvaSetEntry>();
  for (const course of getAllCourses()) {
    if (!course.provasIngresso) continue;
    for (const set of course.provasIngresso.sets) {
      if (set.length < 2) continue;
      const slug = provaSetSlug(set);
      if (!seen.has(slug)) seen.set(slug, { slug, provas: set });
    }
  }
  return Array.from(seen.values());
}

export function getProvaSetBySlug(slug: string): ProvaSetEntry | undefined {
  return getAllProvaSets().find((s) => s.slug === slug);
}

export function getCoursesByProvaSet(slug: string): Course[] {
  return getAllCourses().filter((c) =>
    c.provasIngresso?.sets.some((set) => provaSetSlug(set) === slug)
  );
}
