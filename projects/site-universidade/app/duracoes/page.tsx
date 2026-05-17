import type { Metadata } from "next";
import Link from "next/link";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";
import { getDuracoes, getCoursesByDuracao } from "@/lib/courses";
import { slugify } from "@/lib/slug";

export const metadata: Metadata = {
  title: "Cursos por duração",
  description: "Explora cursos do ensino superior em Portugal por duração: semestres, trimestres ou anos.",
  alternates: { canonical: "/duracoes/" }
};

export default function DuracoesPage() {
  const duracoes = getDuracoes();

  return (
    <Container className="py-10">
      <Breadcrumbs items={[{ label: "Duração" }]} />
      <section>
        <h1 className="text-4xl font-bold tracking-tight text-slate-950">Cursos por duração</h1>
        <p className="mt-4 text-slate-700">
          Filtra cursos do ensino superior em Portugal pela sua duração.
        </p>
      </section>

      <section className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {duracoes.map((duracao) => {
          const count = getCoursesByDuracao(slugify(duracao)).length;
          return (
            <Link
              key={duracao}
              href={`/duracoes/${slugify(duracao)}/`}
              className="group flex h-full flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
            >
              <h2 className="text-lg font-semibold text-slate-950 group-hover:text-brand-700">{duracao}</h2>
              <p className="mt-2 text-sm text-slate-600">{count} curso{count === 1 ? "" : "s"}</p>
              <span className="mt-auto pt-4 text-sm font-semibold text-brand-700 group-hover:text-brand-900">Ver cursos →</span>
            </Link>
          );
        })}
      </section>
    </Container>
  );
}
