import type { Metadata } from "next";
import Link from "next/link";
import { ADS_ENABLED, AdSlot } from "@/components/AdSlot";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";
import { getAllUniversities } from "@/lib/courses";

export const metadata: Metadata = {
  title: "Universidades e institutos",
  description: "Lista de universidades e institutos de ensino superior em Portugal com cursos disponíveis no Universidade.pt.",
  alternates: { canonical: "/universidades/" }
};

export default function UniversitiesPage() {
  const universities = getAllUniversities().sort((a, b) => {
    const totalA = a.faculties.length > 0 ? a.faculties.reduce((sum, f) => sum + f.courses.length, 0) : a.courses.length;
    const totalB = b.faculties.length > 0 ? b.faculties.reduce((sum, f) => sum + f.courses.length, 0) : b.courses.length;
    return totalB - totalA;
  });

  return (
    <Container className="py-10">
      <Breadcrumbs items={[{ label: "Universidades" }]} />
      <section>
        <h1 className="text-4xl font-bold tracking-tight text-slate-950">Universidades e institutos</h1>
        <p className="mt-4 text-slate-700">
          Consulta universidades e institutos de ensino superior e vê as faculdades e cursos disponíveis em cada um.
        </p>
      </section>

      {ADS_ENABLED && (
        <div className="mt-10">
          <AdSlot label="Universidades — topo" />
        </div>
      )}

      <section className="mt-10 grid gap-10">
        {universities.map((university) => {
          const hasFaculties = university.faculties.length > 0;
          const totalCourses = hasFaculties
            ? university.faculties.reduce((sum, f) => sum + f.courses.length, 0)
            : university.courses.length;
          const facultyCount = university.faculties.length;

          return (
            <div key={university.slug}>
              <h2 className="text-xl font-bold text-slate-950">
                <Link href={`/universidades/${university.slug}/`} className="hover:text-brand-700">
                  {university.name}
                  {university.acronym ? <span className="ml-2 text-base font-semibold text-slate-500">({university.acronym})</span> : null}
                </Link>
              </h2>

              <p className="mt-1 text-sm text-slate-500">
                {hasFaculties
                  ? `${totalCourses} curso${totalCourses === 1 ? "" : "s"} em ${facultyCount} faculdade${facultyCount === 1 ? "" : "s"}`
                  : `${totalCourses} curso${totalCourses === 1 ? "" : "s"}`}
              </p>

              {hasFaculties && (
                <ul className="mt-3 grid gap-1">
                  {university.faculties.map((faculty) => (
                    <li key={faculty.slug}>
                      <Link
                        href={`/faculdades/${faculty.slug}/`}
                        className="flex items-center justify-between rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-brand-50 hover:text-brand-700"
                      >
                        <span>
                          {faculty.institutionName}
                          {faculty.institutionSigla ? <span className="ml-1.5 text-slate-400">({faculty.institutionSigla})</span> : null}
                        </span>
                        <span className="mx-3 min-w-4 flex-1 self-end border-b border-dotted border-slate-300 pb-[3px]" aria-hidden="true" />
                        <span className="shrink-0 text-xs text-slate-400">
                          {faculty.courses.length} curso{faculty.courses.length === 1 ? "" : "s"}
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          );
        })}
      </section>
    </Container>
  );
}
