import Link from "next/link";
import type { Course } from "@/lib/courses";

export function CourseCard({ course }: { course: Course }) {
  const latestGrade = course.grades[0];

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
      <h2 className="text-lg font-semibold text-slate-950">
        <Link href={`/cursos/${course.slug}/`} className="hover:text-brand-700">
          {course.courseName}
        </Link>
      </h2>
      {course.institutionName && <p className="mt-2 text-sm text-slate-600">{course.institutionName}</p>}
      {(course.institutionSigla || course.cycle) && (
        <div className="mt-2 flex flex-wrap gap-2 text-xs font-medium uppercase tracking-wide text-slate-500">
          {course.institutionSigla && <span className="rounded-full bg-slate-100 px-3 py-1">{course.institutionSigla}</span>}
          {course.cycle && <span className="rounded-full bg-slate-100 px-3 py-1">{course.cycle}</span>}
        </div>
      )}
      {latestGrade ? (
        <p className="mt-3 text-sm text-slate-600">Nota mais recente disponível: {latestGrade.grade} ({latestGrade.year}{latestGrade.phase ? `, ${latestGrade.phase}` : ""})</p>
      ) : (
        <p className="mt-3 text-sm text-slate-600">Notas de entrada não disponíveis.</p>
      )}
      <Link href={`/cursos/${course.slug}/`} className="mt-4 inline-flex text-sm font-semibold text-brand-700 hover:text-brand-900">
        Ver detalhes →
      </Link>
    </article>
  );
}
