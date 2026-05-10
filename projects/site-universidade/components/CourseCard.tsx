import Link from "next/link";
import type { Course } from "@/lib/courses";

export function CourseCard({ course }: { course: Course }) {
  const institutionLabel = [course.institutionName, course.institutionSigla ? `(${course.institutionSigla})` : undefined].filter(Boolean).join(" ");

  return (
    <Link href={`/cursos/${course.slug}/`} className="block rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
      <h2 className="text-lg font-semibold text-slate-950">
        <span className="hover:text-brand-700">{course.courseName}</span>
      </h2>
      {institutionLabel && <p className="mt-2 text-sm text-slate-600">{institutionLabel}</p>}
      {course.cycle && (
        <div className="mt-2 flex flex-wrap gap-2 text-xs font-medium uppercase tracking-wide text-slate-500">
          <span className="rounded-full bg-slate-100 px-3 py-1">{course.cycle}</span>
        </div>
      )}
      <span className="mt-4 inline-flex text-sm font-semibold text-brand-700 hover:text-brand-900">
        Ver detalhes →
      </span>
    </Link>
  );
}
