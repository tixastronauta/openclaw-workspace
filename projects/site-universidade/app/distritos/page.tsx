import type { Metadata } from "next";
import Link from "next/link";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";
import { getAllDistricts } from "@/lib/courses";

export const metadata: Metadata = {
  title: "Cursos por distrito",
  description: "Explora cursos e faculdades do ensino superior em Portugal por distrito.",
  alternates: { canonical: "/distritos/" }
};

export default function DistritosPage() {
  const districts = getAllDistricts();

  return (
    <Container className="py-10">
      <Breadcrumbs items={[{ label: "Distritos" }]} />
      <section>
        <h1 className="text-4xl font-bold tracking-tight text-slate-950">Distritos</h1>
        <p className="mt-4 max-w-3xl text-slate-700">
          Explora faculdades e cursos do ensino superior em Portugal por distrito.
        </p>
      </section>

      <section className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {districts.map((district) => (
          <Link
            key={district.slug}
            href={`/distritos/${district.slug}/`}
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
          >
            <h2 className="text-lg font-semibold text-slate-950">{district.name}</h2>
            <p className="mt-1 text-sm text-slate-600">{district.faculties.length} institui{district.faculties.length === 1 ? "ção" : "ções"}</p>
            <p className="text-sm text-slate-500">{district.courseCount} curso{district.courseCount === 1 ? "" : "s"}</p>
            <span className="mt-3 inline-flex text-sm font-semibold text-brand-700">Ver →</span>
          </Link>
        ))}
      </section>
    </Container>
  );
}
