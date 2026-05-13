import { slugify } from "@/lib/slug";

export type SearchEntry = {
  slug: string;
  n: string;
  i?: string;
  s?: string;
  ic?: string;
  pi?: string;
  pa?: string;
};

export type SearchResult =
  | { type: "university"; key: string; href: string; title: string; acronym?: string; subtitle?: string }
  | { type: "faculty";    key: string; href: string; title: string; acronym?: string; subtitle?: string }
  | { type: "course";     key: string; href: string; title: string; acronym?: string; subtitle?: string };

export type SearchResults = {
  universities: SearchResult[];
  faculties: SearchResult[];
  courses: SearchResult[];
};

let indexCache: SearchEntry[] | null = null;
let indexPromise: Promise<SearchEntry[]> | null = null;

export function loadIndex(): Promise<SearchEntry[]> {
  if (indexCache) return Promise.resolve(indexCache);
  if (indexPromise) return indexPromise;
  indexPromise = fetch("/search-index.json")
    .then((r) => r.json() as Promise<SearchEntry[]>)
    .then((data) => { indexCache = data; return data; });
  return indexPromise;
}

export function normalize(s: string) {
  return s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLocaleLowerCase("pt");
}

export function runSearch(entries: SearchEntry[], raw: string): SearchResults {
  const q = normalize(raw.trim());
  if (!q) return { universities: [], faculties: [], courses: [] };
  const tokens = q.split(/\s+/).filter(Boolean);
  const matchesAll = (searchable: string) => tokens.every((t) => searchable.includes(t));

  const universities: SearchResult[] = [];
  const faculties: SearchResult[] = [];
  const courses: SearchResult[] = [];
  const seenUnivs = new Set<string>();
  const seenFaculties = new Set<string>();

  for (const entry of entries) {
    const univName = entry.pi ?? entry.i;
    const univAcronym = entry.pa ?? (entry.pi ? undefined : entry.s);
    if (univName) {
      const univSearchable = normalize(`${univName} ${univAcronym ?? ""}`);
      if (matchesAll(univSearchable)) {
        const univSlug = entry.pi
          ? slugify(entry.pi)
          : slugify([entry.i, entry.ic].filter(Boolean).join(" "));
        if (!seenUnivs.has(univSlug)) {
          seenUnivs.add(univSlug);
          universities.push({
            type: "university",
            key: `univ-${univSlug}`,
            href: `/universidades/${univSlug}/`,
            title: univName,
            subtitle: univAcronym,
          });
        }
      }
    }

    if (entry.pi && entry.i) {
      const facultySearchable = normalize(`${entry.i} ${entry.s ?? ""}`);
      if (matchesAll(facultySearchable)) {
        const facultySlug = slugify([entry.i, entry.ic].filter(Boolean).join(" "));
        if (!seenFaculties.has(facultySlug)) {
          seenFaculties.add(facultySlug);
          faculties.push({
            type: "faculty",
            key: `faculty-${facultySlug}`,
            href: `/faculdades/${facultySlug}/`,
            title: entry.i,
            acronym: entry.s,
            subtitle: entry.pa ? `${entry.pa} · ${entry.pi}` : entry.pi,
          });
        }
      }
    }

    if (matchesAll(normalize(`${entry.n} ${entry.i ?? ""} ${entry.s ?? ""}`))) {
      courses.push({
        type: "course",
        key: `course-${entry.slug}`,
        href: `/cursos/${entry.slug}/`,
        title: entry.n,
        subtitle: entry.i,
      });
    }
  }

  return { universities, faculties, courses };
}
