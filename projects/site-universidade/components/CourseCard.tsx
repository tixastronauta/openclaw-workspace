import Link from "next/link";
import type { Course } from "@/lib/courses";

type CycleKind = "licenciatura" | "mestrado" | "prep";

function getCycleKind(cycle?: string): CycleKind {
  const normalized = cycle?.toLocaleLowerCase("pt") ?? "";
  if (normalized.includes("prep") || normalized.includes("preparat")) return "prep";
  if (normalized.includes("mestrado")) return "mestrado";
  if (normalized.includes("licenciatura")) return "licenciatura";
  return "prep";
}

function CycleIcon({ cycle }: { cycle?: string }) {
  const kind = getCycleKind(cycle);
  const label = kind === "licenciatura" ? "Licenciatura" : kind === "mestrado" ? "Mestrado" : "Preparatório";

  return (
    <span className="group/badge relative inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-100 text-slate-500" title={label} aria-label={label}>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4" aria-hidden="true">
        {kind === "licenciatura" && (
          <>
            <path d="M7 4.5h8.5A2.5 2.5 0 0118 7v12H8a3 3 0 01-3-3V6.5a2 2 0 012-2z" />
            <path d="M8 16h10" />
            <path d="M9 8h5" />
          </>
        )}
        {kind === "mestrado" && (
          <>
            <path d="M3 8l9-4 9 4-9 4-9-4z" />
            <path d="M7 10.2V15c0 1.2 2.2 3 5 3s5-1.8 5-3v-4.8" />
            <path d="M21 8v5" />
          </>
        )}
        {kind === "prep" && (
          <>
            <circle cx="12" cy="12" r="8" />
            <path d="M14.8 9.2l-1.7 4-3.9 1.6 1.7-3.9 3.9-1.7z" />
          </>
        )}
      </svg>
      <span className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 hidden -translate-x-1/2 whitespace-nowrap rounded-lg bg-slate-950 px-2 py-1 text-xs font-medium text-white shadow-lg group-hover/badge:inline-flex group-focus-visible/badge:inline-flex">
        {label}
      </span>
    </span>
  );
}

export function CourseCard({ course }: { course: Course }) {
  return (
    <Link href={`/cursos/${course.slug}/`} className="group flex h-full flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
      <div>
        <h2 className="text-lg font-semibold text-slate-950 group-hover:text-brand-700">{course.courseName}</h2>
        {course.institutionName && (
          <div className="mt-2 text-sm text-slate-600">
            <p>
              {course.institutionName}
              {course.institutionSigla ? ` (${course.institutionSigla})` : null}
            </p>
            {course.parentInstitutionName && course.parentInstitutionName !== course.institutionName && (
              <p className="text-slate-400">{course.parentInstitutionName}</p>
            )}
          </div>
        )}
      </div>
      <div className="mt-auto flex items-center justify-between pt-4">
        <CycleIcon cycle={course.cycle} />
        <span className="text-sm font-semibold text-brand-700 group-hover:text-brand-900">Ver detalhes →</span>
      </div>
    </Link>
  );
}
