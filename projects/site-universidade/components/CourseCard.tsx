import Link from "next/link";
import type { Course } from "@/lib/courses";

type CycleKind = "licenciatura" | "mestrado-integrado" | "outros";

function getCycleKind(cycle?: string): CycleKind {
  const normalized = cycle?.toLocaleLowerCase("pt") ?? "";
  if (normalized.includes("mestrado integrado")) return "mestrado-integrado";
  if (normalized.includes("licenciatura")) return "licenciatura";
  return "outros";
}

function CycleIcon({ cycle }: { cycle?: string }) {
  const kind = getCycleKind(cycle);
  const label = kind === "licenciatura" ? "Licenciatura" : kind === "mestrado-integrado" ? "Mestrado integrado" : "Outro ciclo";

  const icon = kind === "licenciatura"
    ? <path d="M4 5.5A2.5 2.5 0 016.5 3H18v14H6.5A2.5 2.5 0 014 14.5v-9zM6.5 5A.5.5 0 006 5.5v9a.5.5 0 00.5.5H16V5H6.5z" />
    : kind === "mestrado-integrado"
      ? <path d="M3 6.5L11 3l8 3.5-8 3.5-8-3.5zm3 3.3l5 2.2 5-2.2V14c0 1.1-2.2 2.5-5 2.5S6 15.1 6 14V9.8z" />
      : <path d="M6 4h8l4 4v8a2 2 0 01-2 2H6a2 2 0 01-2-2V6a2 2 0 012-2zm7 1.5V9h3.5" />;

  return (
    <span className="mt-3 inline-flex h-8 w-8 items-center justify-center rounded-full bg-slate-100 text-slate-500" title={label} aria-label={label}>
      <svg viewBox="0 0 22 22" fill="currentColor" className="h-4 w-4" aria-hidden="true">
        {icon}
      </svg>
    </span>
  );
}

export function CourseCard({ course }: { course: Course }) {
  const institutionLabel = [course.institutionName, course.institutionSigla ? `(${course.institutionSigla})` : undefined].filter(Boolean).join(" ");

  return (
    <Link href={`/cursos/${course.slug}/`} className="block rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
      <h2 className="text-lg font-semibold text-slate-950">
        <span className="hover:text-brand-700">{course.courseName}</span>
      </h2>
      {institutionLabel && <p className="mt-2 text-sm text-slate-600">{institutionLabel}</p>}
      <CycleIcon cycle={course.cycle} />
      <span className="mt-4 inline-flex text-sm font-semibold text-brand-700 hover:text-brand-900">
        Ver detalhes →
      </span>
    </Link>
  );
}
