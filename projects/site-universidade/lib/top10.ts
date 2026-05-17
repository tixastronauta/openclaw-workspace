import type { Course } from "./courses";
import { getAllCourses } from "./courses";

export type Top10Metric = {
  id: string;
  title: string;
  shortTitle: string;
  description: string;
  valueLabel: string;
  items: Array<{
    course: Course;
    value: number;
  }>;
};

type MetricKey = NonNullable<Course["metrics"]> extends infer Metrics
  ? keyof NonNullable<Metrics>
  : never;

function rankCourses(
  courses: Course[],
  key: MetricKey,
  direction: "asc" | "desc",
  include?: (item: { course: Course; value: number }) => boolean,
) {
  return courses
    .map((course) => ({ course, value: course.metrics?.[key] }))
    .filter((item): item is { course: Course; value: number } => typeof item.value === "number" && Number.isFinite(item.value))
    .filter((item) => (include ? include(item) : true))
    .sort((a, b) => direction === "asc" ? a.value - b.value : b.value - a.value)
    .slice(0, 10);
}

export function formatPercent(value: number) {
  return `${(value * 100).toLocaleString("pt-PT", { maximumFractionDigits: 1 })}%`;
}

export function formatDecimal(value: number) {
  return value.toLocaleString("pt-PT", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}

export function getTop10Metrics(): Top10Metric[] {
  const courses = getAllCourses();

  return [
    {
      id: "media-entrada-mais-alta",
      title: "Top 10 cursos com média de entrada mais alta",
      shortTitle: "Com média de entrada mais alta",
      description: "Cursos com nota de entrada mais elevada, calculada a partir das notas do ano mais recente disponível.",
      valueLabel: "Nota de entrada",
      items: rankCourses(courses, "entryGradeAverage", "desc")
    },
    {
      id: "media-entrada-mais-baixa",
      title: "Top 10 cursos com média de entrada mais baixa",
      shortTitle: "Com média de entrada mais baixa",
      description: "Cursos com nota de entrada mais baixa, calculada a partir das notas do ano mais recente disponível.",
      valueLabel: "Nota de entrada",
      items: rankCourses(courses, "entryGradeAverage", "asc")
    },
    {
      id: "mais-homens",
      title: "Top 10 cursos com mais homens",
      shortTitle: "Com mais homens",
      description: "Cursos com maior percentagem de estudantes homens.",
      valueLabel: "Homens",
      items: rankCourses(courses, "menShare", "desc")
    },
    {
      id: "mais-mulheres",
      title: "Top 10 cursos com mais mulheres",
      shortTitle: "Com mais mulheres",
      description: "Cursos com maior percentagem de estudantes mulheres.",
      valueLabel: "Mulheres",
      items: rankCourses(courses, "womenShare", "desc")
    },
    {
      id: "media-mais-alta",
      title: "Top 10 cursos com média final mais alta",
      shortTitle: "Com média final mais alta",
      description: "Cursos com média ponderada mais alta nas classificações finais.",
      valueLabel: "Média final",
      items: rankCourses(courses, "finalAverage", "desc")
    },
    {
      id: "media-mais-baixa",
      title: "Top 10 cursos com média final mais baixa",
      shortTitle: "Com média final mais baixa",
      description: "Cursos com média ponderada mais baixa nas classificações finais.",
      valueLabel: "Média final",
      items: rankCourses(courses, "finalAverage", "asc")
    },
    {
      id: "melhor-empregabilidade",
      title: "Top 10 cursos com melhor empregabilidade",
      shortTitle: "Com melhor empregabilidade",
      description: "Cursos com a melhor taxa de empregabilidade registada no IEFP.",
      valueLabel: "Empregabilidade",
      items: rankCourses(courses, "unemploymentRate", "asc").map((item) => ({ ...item, value: 1 - item.value }))
    },
    {
      id: "pior-empregabilidade",
      title: "Top 10 cursos com pior empregabilidade",
      shortTitle: "Com pior empregabilidade",
      description: "Cursos com a pior taxa de desemprego registada no IEFP.",
      valueLabel: "Desemprego",
      items: rankCourses(courses, "unemploymentRate", "desc")
    },
    {
      id: "mais-estrangeiros",
      title: "Top 10 cursos com mais estrangeiros",
      shortTitle: "Com mais estrangeiros",
      description: "Cursos com maior percentagem de estudantes estrangeiros.",
      valueLabel: "Estrangeiros",
      items: rankCourses(courses, "foreignerShare", "desc", ({ value }) => value < 1)
    },
    {
      id: "perfil-etario-mais-elevado",
      title: "Top 10 cursos com perfil etário mais elevado",
      shortTitle: "Com perfil etário mais elevado",
      description: "Cursos com idade média dos alunos mais elevada.",
      valueLabel: "Idade média",
      items: rankCourses(courses, "ageAverage", "desc")
    }
  ];
}

export function formatTop10Value(metricId: string, value: number) {
  if (["mais-estrangeiros", "mais-homens", "mais-mulheres", "melhor-empregabilidade", "pior-empregabilidade"].includes(metricId)) {
    return formatPercent(value);
  }

  return formatDecimal(value);
}
