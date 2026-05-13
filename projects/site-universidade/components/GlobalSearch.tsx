"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import Link from "next/link";
import { loadIndex, runSearch, type SearchResult } from "@/lib/search";

function UniversityIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4" aria-hidden="true">
      <path d="M10.75 2.75a.75.75 0 00-1.5 0v1.18l-6.4 2.843a.75.75 0 00.305 1.432h1.095v6.04h-.75a.75.75 0 000 1.5h13a.75.75 0 000-1.5h-.75V8.205h1.095a.75.75 0 00.305-1.432l-6.4-2.843V2.75zM7 8.205h1.5v6.04H7v-6.04zm4.5 0h1.5v6.04h-1.5v-6.04z" />
    </svg>
  );
}

function FacultyIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4" aria-hidden="true">
      <path fillRule="evenodd" d="M9.664 1.319a.75.75 0 01.672 0 41.059 41.059 0 018.198 5.424.75.75 0 01-.254 1.285 31.372 31.372 0 00-7.86 3.83.75.75 0 01-.84 0 31.508 31.508 0 00-2.08-1.287V9.48a31.525 31.525 0 00-1.66-1.02.75.75 0 01-.254-1.285 41.059 41.059 0 018.198-5.424zM14.5 9.5a30.025 30.025 0 00-4.5 2.203A30.025 30.025 0 005.5 9.5v.5a29.5 29.5 0 014 2.07V18h1V12.07a29.5 29.5 0 014-2.07v-.5z" clipRule="evenodd" />
    </svg>
  );
}

function CourseIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4" aria-hidden="true">
      <path fillRule="evenodd" d="M4.25 3A2.25 2.25 0 002 5.25v9.5A2.25 2.25 0 004.25 17h11.5A2.25 2.25 0 0018 14.75v-9.5A2.25 2.25 0 0015.75 3H4.25zm1.5 2a.75.75 0 000 1.5h8.5a.75.75 0 000-1.5h-8.5zm0 3a.75.75 0 000 1.5h8.5a.75.75 0 000-1.5h-8.5zm0 3a.75.75 0 000 1.5h5.5a.75.75 0 000-1.5h-5.5z" clipRule="evenodd" />
    </svg>
  );
}

// Module-level cache reference (the real cache lives in lib/search.ts)
let cachedEntries: Awaited<ReturnType<typeof loadIndex>> | null = null;

export function GlobalSearch() {
  const [results, setResults] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [hasValue, setHasValue] = useState(false);
  const [, startTransition] = useTransition();
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const pendingQuery = useRef<string | null>(null);

  function updateDropdown(entries: Awaited<ReturnType<typeof loadIndex>>, raw: string) {
    const { universities, faculties, courses } = runSearch(entries, raw);
    startTransition(() => {
      setResults([
        ...universities.slice(0, 3),
        ...faculties.slice(0, 3),
        ...courses,
      ].slice(0, 10));
    });
  }

  function search(raw: string) {
    setHasValue(raw.length > 0);
    if (!raw.trim()) { setResults([]); return; }
    if (cachedEntries) {
      updateDropdown(cachedEntries, raw);
    } else {
      pendingQuery.current = raw;
      loadIndex().then((entries) => {
        cachedEntries = entries;
        if (pendingQuery.current === raw) updateDropdown(entries, raw);
      });
    }
  }

  function onFocus() {
    setOpen(true);
    if (!cachedEntries) loadIndex().then((e) => { cachedEntries = e; });
  }

  function clear() {
    if (inputRef.current) inputRef.current.value = "";
    setResults([]);
    setHasValue(false);
    setOpen(false);
    pendingQuery.current = null;
    inputRef.current?.focus();
  }

  useEffect(() => {
    function onPointerDown(e: PointerEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, []);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") { setOpen(false); inputRef.current?.blur(); }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div ref={containerRef} className="relative w-full sm:max-w-sm">
      <label className="sr-only" htmlFor="global-search">Pesquisar cursos, faculdades e universidades</label>
      <form action="/pesquisa" onSubmit={() => setOpen(false)}>
        <div className="relative">
          <button type="submit" aria-label="Pesquisar" className="absolute left-2 top-1/2 -translate-y-1/2 rounded p-0.5 text-slate-400 hover:text-slate-700">
            <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fillRule="evenodd" d="M9 3a6 6 0 100 12A6 6 0 009 3zM1 9a8 8 0 1114.32 4.906l3.387 3.387a1 1 0 01-1.414 1.414l-3.387-3.387A8 8 0 011 9z" clipRule="evenodd" />
            </svg>
          </button>
          <input
            ref={inputRef}
            id="global-search"
            name="q"
            type="text"
            inputMode="search"
            onFocus={onFocus}
            onInput={(e) => { search((e.target as HTMLInputElement).value); setOpen(true); }}
            placeholder="Pesquisar cursos, faculdades..."
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="off"
            spellCheck={false}
            className="w-full rounded-xl border border-slate-300 bg-white py-2 pl-9 pr-8 text-sm outline-none ring-brand-600 transition focus:ring-2"
          />
          {hasValue && (
            <button type="button" aria-label="Limpar pesquisa" onMouseDown={(e) => { e.preventDefault(); clear(); }} className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-0.5 text-slate-400 hover:text-slate-700">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4" aria-hidden="true">
                <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
              </svg>
            </button>
          )}
        </div>
      </form>

      {open && results.length > 0 && (
        <div className="absolute left-0 right-0 top-[calc(100%+6px)] z-50 max-h-[70vh] overflow-y-auto rounded-2xl border border-slate-200 bg-white shadow-xl">
          <ul role="listbox">
            {results.map((result) => (
              <li key={result.key} role="option" aria-selected="false">
                <Link href={result.href} onClick={() => { clear(); }} className="flex items-start gap-2.5 px-4 py-3 text-sm hover:bg-brand-50">
                  <span className="mt-0.5 text-slate-400" aria-hidden="true">
                    {result.type === "university" && <UniversityIcon />}
                    {result.type === "faculty" && <FacultyIcon />}
                    {result.type === "course" && <CourseIcon />}
                  </span>
                  <span className="flex min-w-0 flex-col gap-0.5">
                    <span className="font-medium text-slate-900">
                      {result.title}
                      {result.acronym && <span className="ml-1.5 font-semibold text-slate-400">({result.acronym})</span>}
                    </span>
                    {result.subtitle && <span className="text-xs text-slate-500">{result.subtitle}</span>}
                  </span>
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
