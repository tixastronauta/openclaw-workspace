"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { loadIndex, runSearch, type SearchResult, type SearchResults } from "@/lib/search";

function UniversityIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5" aria-hidden="true">
      <path d="M10.75 2.75a.75.75 0 00-1.5 0v1.18l-6.4 2.843a.75.75 0 00.305 1.432h1.095v6.04h-.75a.75.75 0 000 1.5h13a.75.75 0 000-1.5h-.75V8.205h1.095a.75.75 0 00.305-1.432l-6.4-2.843V2.75zM7 8.205h1.5v6.04H7v-6.04zm4.5 0h1.5v6.04h-1.5v-6.04z" />
    </svg>
  );
}

function FacultyIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5" aria-hidden="true">
      <path fillRule="evenodd" d="M9.664 1.319a.75.75 0 01.672 0 41.059 41.059 0 018.198 5.424.75.75 0 01-.254 1.285 31.372 31.372 0 00-7.86 3.83.75.75 0 01-.84 0 31.508 31.508 0 00-2.08-1.287V9.48a31.525 31.525 0 00-1.66-1.02.75.75 0 01-.254-1.285 41.059 41.059 0 018.198-5.424zM14.5 9.5a30.025 30.025 0 00-4.5 2.203A30.025 30.025 0 005.5 9.5v.5a29.5 29.5 0 014 2.07V18h1V12.07a29.5 29.5 0 014-2.07v-.5z" clipRule="evenodd" />
    </svg>
  );
}

function CourseIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5" aria-hidden="true">
      <path fillRule="evenodd" d="M4.25 3A2.25 2.25 0 002 5.25v9.5A2.25 2.25 0 004.25 17h11.5A2.25 2.25 0 0018 14.75v-9.5A2.25 2.25 0 0015.75 3H4.25zm1.5 2a.75.75 0 000 1.5h8.5a.75.75 0 000-1.5h-8.5zm0 3a.75.75 0 000 1.5h8.5a.75.75 0 000-1.5h-8.5zm0 3a.75.75 0 000 1.5h5.5a.75.75 0 000-1.5h-5.5z" clipRule="evenodd" />
    </svg>
  );
}

function ResultRow({ result }: { result: SearchResult }) {
  return (
    <li>
      <Link href={result.href} className="flex items-start gap-3 rounded-xl px-4 py-3 hover:bg-brand-50">
        <span className="mt-0.5 shrink-0 text-slate-400" aria-hidden="true">
          {result.type === "university" && <UniversityIcon />}
          {result.type === "faculty" && <FacultyIcon />}
          {result.type === "course" && <CourseIcon />}
        </span>
        <span className="flex min-w-0 flex-col gap-0.5">
          <span className="font-medium text-slate-900">
            {result.title}
            {result.acronym && <span className="ml-1.5 font-semibold text-slate-400">({result.acronym})</span>}
          </span>
          {result.subtitle && <span className="text-sm text-slate-500">{result.subtitle}</span>}
        </span>
      </Link>
    </li>
  );
}

function ResultSection({ title, results }: { title: string; results: SearchResult[] }) {
  if (results.length === 0) return null;
  return (
    <section className="mt-8">
      <h2 className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-400">
        {title} <span className="ml-1 text-slate-300">({results.length})</span>
      </h2>
      <ul className="-mx-4 divide-y divide-slate-100">
        {results.map((r) => <ResultRow key={r.key} result={r} />)}
      </ul>
    </section>
  );
}

export function SearchResultsClient() {
  const searchParams = useSearchParams();
  const q = searchParams.get("q") ?? "";
  const [results, setResults] = useState<SearchResults | null>(null);

  useEffect(() => {
    if (!q.trim()) {
      setResults({ universities: [], faculties: [], courses: [] });
      return;
    }
    loadIndex().then((entries) => setResults(runSearch(entries, q)));
  }, [q]);

  const total = results
    ? results.universities.length + results.faculties.length + results.courses.length
    : null;

  return (
    <div>
      <h1 className="text-3xl font-bold tracking-tight text-slate-950">
        {q ? <>Resultados para <span className="text-brand-700">«{q}»</span></> : "Pesquisa"}
      </h1>

      {results === null && (
        <p className="mt-6 text-slate-500">A pesquisar…</p>
      )}

      {results !== null && total === 0 && (
        <p className="mt-6 text-slate-500">
          {q ? "Sem resultados para esta pesquisa." : "Introduz um termo de pesquisa."}
        </p>
      )}

      {results !== null && total !== null && total > 0 && (
        <>
          <p className="mt-2 text-sm text-slate-500">
            {total} resultado{total === 1 ? "" : "s"}
          </p>
          <ResultSection title="Universidades" results={results.universities} />
          <ResultSection title="Faculdades" results={results.faculties} />
          <ResultSection title="Cursos" results={results.courses} />
        </>
      )}
    </div>
  );
}
