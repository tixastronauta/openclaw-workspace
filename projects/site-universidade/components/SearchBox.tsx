"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

type SearchCourse = {
  slug: string;
  courseName: string;
  institutionName?: string;
  institutionSigla?: string;
};

export function SearchBox({ courses, placeholder = "Pesquisar cursos..." }: { courses: SearchCourse[]; placeholder?: string }) {
  const [query, setQuery] = useState("");

  const results = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase("pt");
    if (!normalized) return courses.slice(0, 8);

    return courses
      .filter((course) => `${course.courseName} ${course.institutionName ?? ""} ${course.institutionSigla ?? ""}`.toLocaleLowerCase("pt").includes(normalized))
      .slice(0, 20);
  }, [courses, query]);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <label className="sr-only" htmlFor="course-search">Pesquisar cursos</label>
      <input
        id="course-search"
        type="search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder={placeholder}
        className="w-full rounded-xl border border-slate-300 px-4 py-3 text-base outline-none ring-brand-600 transition focus:ring-2"
      />
      <div className="mt-4 grid gap-2" aria-live="polite">
        {results.length > 0 ? (
          results.map((course) => (
            <Link key={course.slug} href={`/cursos/${course.slug}/`} className="rounded-lg px-3 py-2 text-sm font-medium text-slate-700 hover:bg-brand-50 hover:text-brand-700">
              <span className="block">{course.courseName}</span>
              {course.institutionName && <span className="block text-xs font-normal text-slate-500">{course.institutionName}</span>}
            </Link>
          ))
        ) : (
          <p className="px-3 py-2 text-sm text-slate-500">Sem resultados para esta pesquisa.</p>
        )}
      </div>
    </div>
  );
}
