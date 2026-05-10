import type { Metadata } from "next";
import Link from "next/link";
import { ADS_ENABLED, AdSlot } from "@/components/AdSlot";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";
import { getAllFaculties } from "@/lib/courses";

export const metadata: Metadata = {
  title: "Faculdades e instituições",
  description: "Lista de faculdades e instituições de ensino superior em Portugal com cursos disponíveis no Universidade.pt.",
  alternates: { canonical: "/faculdades/" }
};

export default function FacultiesPage() {
  const faculties = getAllFaculties();
  const grouped = faculties.reduce<Record<string, typeof faculties>>((acc, faculty) => {
    const initial = faculty.institutionName[0]?.toLocaleUpperCase("pt") ?? "#";
    acc[initial] = [...(acc[initial] ?? []), faculty];
    return acc;
  }, {});

  return (
    <Container className="py-10">
      <Breadcrumbs items={[{ label: "Faculdades" }]} />
      <section>
        <h1 className="text-4xl font-bold tracking-tight text-slate-950">Faculdades e instituições</h1>
        <p className="mt-4 max-w-3xl text-slate-700">
          Consulta instituições de ensino superior e vê os cursos disponíveis em cada uma.
        </p>
      </section>

      {ADS_ENABLED && (
        <div className="mt-10">
          <AdSlot label="Faculdades — topo" />
        </div>
      )}

      <section className="mt-10 grid gap-10">
        {Object.entries(grouped).map(([initial, items]) => (
          <div key={initial} id={initial}>
            <h2 className="mb-4 border-b border-slate-200 pb-2 text-2xl font-semibold text-slate-950">{initial}</h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {items.map((faculty) => (
                <article key={faculty.slug} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
                  <h2 className="text-lg font-semibold text-slate-950">
                    <Link href={`/faculdades/${faculty.slug}/`} className="hover:text-brand-700">
                      {faculty.institutionName}
                    </Link>
                  </h2>
                  {faculty.institutionSigla && (
                    <div className="mt-2 flex flex-wrap gap-2 text-xs font-medium uppercase tracking-wide text-slate-500">
                      <span className="rounded-full bg-slate-100 px-3 py-1">{faculty.institutionSigla}</span>
                    </div>
                  )}
                  <p className="mt-2 text-sm text-slate-600">{faculty.courses.length} curso{faculty.courses.length === 1 ? "" : "s"} {faculty.courses.length === 1 ? "disponível" : "disponíveis"}</p>
                  <Link href={`/faculdades/${faculty.slug}/`} className="mt-4 inline-flex text-sm font-semibold text-brand-700 hover:text-brand-900">
                    Ver cursos →
                  </Link>
                </article>
              ))}
            </div>
          </div>
        ))}
      </section>
    </Container>
  );
}
