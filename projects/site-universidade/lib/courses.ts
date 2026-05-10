import fs from "node:fs";
import path from "node:path";
import Papa from "papaparse";
import { slugify } from "./slug";

export type AdmissionGrade = {
  year: string;
  phase?: string;
  grade: string;
};

export type CourseMetrics = {
  unemploymentRate?: number;
  finalAverage?: number;
  menShare?: number;
  womenShare?: number;
  foreignerShare?: number;
  ageAverage?: number;
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
  courseDescription?: string;
  infoCursosUrl?: string;
  dgesUrl?: string;
  metrics?: CourseMetrics;
};

type CsvRow = Record<string, string | undefined>;

const CSV_PATH = path.join(process.cwd(), "data", "courses.csv");

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

function extractMetrics(row: CsvRow): CourseMetrics {
  const unemployment = rowsFromJson(row.infocursos_iefp_desemprego_json).find((item) => item.Desemprego === "Curso");
  const sex = rowsFromJson(row.infocursos_sexo_curso_json).find((item) => item.Sexo === "Curso");
  const nationality = rowsFromJson(row.infocursos_nacionalidade_curso_json).find((item) => item.Nacionalidade === "Curso");

  return {
    unemploymentRate: numberValue(unemployment?.Taxa),
    finalAverage: weightedFinalAverage(row),
    menShare: numberValue(sex?.Homens),
    womenShare: numberValue(sex?.Mulheres),
    foreignerShare: numberValue(nationality?.Estrangeiros),
    ageAverage: weightedAgeAverage(row)
  };
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
      cidade: getFirst(row, ["cidade"]),
      distrito: getFirst(row, ["distrito"]),
      morada: getFirst(row, ["morada"]),
      reference: getFirst(row, ["reference", "referencia"]),
      grades: extractGrades(row),
      courseDescription: getFirst(row, ["courseDescription", "course_description"]),
      infoCursosUrl: getFirst(row, ["infoCursosUrl", "infocursosUrl", "info_cursos_url", "InfoCursos", "estatisticas_do_curso"]),
      dgesUrl: getFirst(row, ["dgesUrl", "dges_url", "DGES", "detalhes_do_curso"]),
      metrics: extractMetrics(row)
    });
  }

  courses.sort((a, b) =>
    a.courseName.localeCompare(b.courseName, "pt") ||
    (a.institutionName ?? "").localeCompare(b.institutionName ?? "", "pt")
  );

  return uniqueSlugs(courses);
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
        courses: courses.sort((a, b) => a.courseName.localeCompare(b.courseName, "pt"))
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
