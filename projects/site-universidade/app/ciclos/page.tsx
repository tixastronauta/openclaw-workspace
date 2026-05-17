import type { Metadata } from "next";
import Link from "next/link";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";
import { getCoursesByCycle, getCycles } from "@/lib/courses";
import { slugify } from "@/lib/slug";

export const metadata: Metadata = {
  title: "Ciclos de estudo",
  description: "Explora cursos do ensino superior em Portugal por ciclo de estudo: licenciatura, mestrado, doutoramento e outros.",
  alternates: { canonical: "/ciclos/" }
};

export default function CyclesPage() {
  const cycles = getCycles();

  return (
    <Container className="py-10">
      <Breadcrumbs items={[{ label: "Ciclos" }]} />
      <section>
        <h1 className="text-4xl font-bold tracking-tight text-slate-950">Ciclos de estudo</h1>
        <p className="mt-4 text-slate-700">
          Explora cursos do ensino superior em Portugal por tipo de ciclo.
        </p>
      </section>

      <section className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {cycles.map((cycle) => {
          const count = getCoursesByCycle(cycle).length;
          return (
            <Link
              key={cycle}
              href={`/ciclos/${slugify(cycle)}/`}
              className="group flex h-full flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
            >
              <div>
                <h2 className="text-lg font-semibold text-slate-950 group-hover:text-brand-700">{cycle}</h2>
                <p className="mt-2 text-sm text-slate-600">{count} curso{count === 1 ? "" : "s"}</p>
              </div>
              <span className="mt-auto pt-4 text-sm font-semibold text-brand-700 group-hover:text-brand-900">Ver cursos →</span>
            </Link>
          );
        })}
      </section>
    </Container>
  );
}
