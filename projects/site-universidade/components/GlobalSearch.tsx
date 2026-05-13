"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import Link from "next/link";
import { slugify } from "@/lib/slug";

type SearchEntry = {
  slug: string;
  n: string;   // courseName
  i?: string;  // institutionName
  s?: string;  // institutionSigla
  ic?: string; // institutionCode
};

type SearchResult =
  | { type: "course"; key: string; href: string; title: string; subtitle?: string }
  | { type: "institution"; key: string; href: string; title: string; subtitle?: string };

// Module-level cache — fetched once per page load
let indexCache: SearchEntry[] | null = null;
let indexPromise: Promise<SearchEntry[]> | null = null;

function loadIndex(): Promise<SearchEntry[]> {
  if (indexCache) return Promise.resolve(indexCache);
  if (indexPromise) return indexPromise;
  indexPromise = fetch("/search-index.json")
    .then((r) => r.json() as Promise<SearchEntry[]>)
    .then((data) => {
      indexCache = data;
      return data;
    });
  return indexPromise;
}

export function GlobalSearch() {
  const [results, setResults] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [hasValue, setHasValue] = useState(false);
  const [, startTransition] = useTransition();
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const pendingQuery = useRef<string | null>(null);

  function runSearch(entries: SearchEntry[], raw: string) {
    const normalized = raw.trim().toLocaleLowerCase("pt");
    if (!normalized) {
      setResults([]);
      return;
    }

    const institutionResults: SearchResult[] = [];
    const seenInstitutions = new Set<string>();

    for (const entry of entries) {
      if (!entry.i) continue;
      const searchable = `${entry.i} ${entry.s ?? ""}`.toLocaleLowerCase("pt");
      if (!searchable.includes(normalized)) continue;
      const institutionSlug = slugify([entry.i, entry.ic].filter(Boolean).join(" "));
      if (seenInstitutions.has(institutionSlug)) continue;
      seenInstitutions.add(institutionSlug);
      institutionResults.push({
        type: "institution",
        key: `institution-${institutionSlug}`,
        href: `/faculdades/${institutionSlug}/`,
        title: entry.i,
        subtitle: entry.s,
      });
    }

    startTransition(() => {
      setResults(
        [
          ...institutionResults,
          ...entries
            .filter((e) =>
              `${e.n} ${e.i ?? ""} ${e.s ?? ""}`.toLocaleLowerCase("pt").includes(normalized)
            )
            .map((e) => ({
              type: "course" as const,
              key: `course-${e.slug}`,
              href: `/cursos/${e.slug}/`,
              title: e.n,
              subtitle: e.i,
            })),
        ].slice(0, 10)
      );
    });
  }

  function search(raw: string) {
    setHasValue(raw.length > 0);
    if (!raw.trim()) {
      setResults([]);
      return;
    }

    if (indexCache) {
      runSearch(indexCache, raw);
    } else {
      pendingQuery.current = raw;
      loadIndex().then((entries) => {
        if (pendingQuery.current === raw) runSearch(entries, raw);
      });
    }
  }

  function onFocus() {
    setOpen(true);
    // prefetch on first focus so the index is ready before the user types
    if (!indexCache) loadIndex();
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
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, []);

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
    <div ref={containerRef} className="relative w-full sm:max-w-sm">
      <label className="sr-only" htmlFor="global-search">Pesquisar cursos e instituições</label>
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
          onFocus={onFocus}
          onInput={(e) => {
            search((e.target as HTMLInputElement).value);
            setOpen(true);
          }}
          placeholder="Pesquisar cursos ou instituições..."
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
            {results.map((result) => (
              <li key={result.key} role="option" aria-selected="false">
                <Link
                  href={result.href}
                  onClick={() => { clear(); }}
                  className="flex items-start gap-2.5 px-4 py-3 text-sm hover:bg-brand-50"
                >
                  <span className="mt-0.5 text-slate-400" aria-hidden="true">
                    {result.type === "institution" ? (
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
                        <path d="M10.75 2.75a.75.75 0 00-1.5 0v1.18l-6.4 2.843a.75.75 0 00.305 1.432h1.095v6.04h-.75a.75.75 0 000 1.5h13a.75.75 0 000-1.5h-.75V8.205h1.095a.75.75 0 00.305-1.432l-6.4-2.843V2.75zM7 8.205h1.5v6.04H7v-6.04zm4.5 0h1.5v6.04h-1.5v-6.04z" />
                      </svg>
                    ) : (
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
                        <path fillRule="evenodd" d="M4.25 3A2.25 2.25 0 002 5.25v9.5A2.25 2.25 0 004.25 17h11.5A2.25 2.25 0 0018 14.75v-9.5A2.25 2.25 0 0015.75 3H4.25zm1.5 2a.75.75 0 000 1.5h8.5a.75.75 0 000-1.5h-8.5zm0 3a.75.75 0 000 1.5h8.5a.75.75 0 000-1.5h-8.5zm0 3a.75.75 0 000 1.5h5.5a.75.75 0 000-1.5h-5.5z" clipRule="evenodd" />
                      </svg>
                    )}
                  </span>
                  <span className="flex min-w-0 flex-col gap-0.5">
                    <span className="font-medium text-slate-900">{result.title}</span>
                    {result.subtitle && (
                      <span className="text-xs text-slate-500">{result.subtitle}</span>
                    )}
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
