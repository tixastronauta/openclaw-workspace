"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import Link from "next/link";

type SearchCourse = {
  slug: string;
  courseName: string;
  institutionName?: string;
  institutionSigla?: string;
};

export function GlobalSearch({ courses }: { courses: SearchCourse[] }) {
  // search results state — input value is uncontrolled (owned by the browser)
  const [results, setResults] = useState<SearchCourse[]>([]);
  const [open, setOpen] = useState(false);
  const [hasValue, setHasValue] = useState(false);
  const [, startTransition] = useTransition();
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  function search(raw: string) {
    const normalized = raw.trim().toLocaleLowerCase("pt");
    setHasValue(raw.length > 0);
    if (!normalized) {
      setResults([]);
      return;
    }
    startTransition(() => {
      setResults(
        courses
          .filter((c) =>
            `${c.courseName} ${c.institutionName ?? ""} ${c.institutionSigla ?? ""}`
              .toLocaleLowerCase("pt")
              .includes(normalized)
          )
          .slice(0, 10)
      );
    });
  }

  function clear() {
    if (inputRef.current) inputRef.current.value = "";
    setResults([]);
    setHasValue(false);
    setOpen(false);
    inputRef.current?.focus();
  }

  // Close on click outside
  useEffect(() => {
    function onPointerDown(e: PointerEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, []);

  // Close on Escape
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setOpen(false);
        inputRef.current?.blur();
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div ref={containerRef} className="relative w-full max-w-xs sm:max-w-sm">
      <label className="sr-only" htmlFor="global-search">Pesquisar cursos</label>
      <div className="relative">
        <svg
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
          width="16" height="16" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"
        >
          <path fillRule="evenodd" d="M9 3a6 6 0 100 12A6 6 0 009 3zM1 9a8 8 0 1114.32 4.906l3.387 3.387a1 1 0 01-1.414 1.414l-3.387-3.387A8 8 0 011 9z" clipRule="evenodd" />
        </svg>
        <input
          ref={inputRef}
          id="global-search"
          type="text"
          inputMode="search"
          // uncontrolled — no value/onChange; browser owns the text
          onFocus={() => setOpen(true)}
          onInput={(e) => {
            search((e.target as HTMLInputElement).value);
            setOpen(true);
          }}
          placeholder="Pesquisar cursos..."
          autoComplete="off"
          autoCorrect="off"
          autoCapitalize="off"
          spellCheck={false}
          className="w-full rounded-xl border border-slate-300 bg-white py-2 pl-9 pr-8 text-sm outline-none ring-brand-600 transition focus:ring-2"
        />
        {hasValue && (
          <button
            type="button"
            aria-label="Limpar pesquisa"
            onMouseDown={(e) => { e.preventDefault(); clear(); }}
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-0.5 text-slate-400 hover:text-slate-700"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4" aria-hidden="true">
              <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
            </svg>
          </button>
        )}
      </div>

      {open && results.length > 0 && (
        <div className="absolute left-0 right-0 top-[calc(100%+6px)] z-50 max-h-[70vh] overflow-y-auto rounded-2xl border border-slate-200 bg-white shadow-xl">
          <ul role="listbox">
            {results.map((course) => (
              <li key={course.slug} role="option" aria-selected="false">
                <Link
                  href={`/cursos/${course.slug}/`}
                  onClick={() => { clear(); }}
                  className="flex flex-col gap-0.5 px-4 py-3 text-sm hover:bg-brand-50"
                >
                  <span className="font-medium text-slate-900">{course.courseName}</span>
                  {course.institutionName && (
                    <span className="text-xs text-slate-500">{course.institutionName}</span>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}

      {open && hasValue && results.length === 0 && (
        <div className="absolute left-0 right-0 top-[calc(100%+6px)] z-50 rounded-2xl border border-slate-200 bg-white shadow-xl">
          <p className="px-4 py-3 text-sm text-slate-500">Sem resultados para esta pesquisa.</p>
        </div>
      )}
    </div>
  );
}
