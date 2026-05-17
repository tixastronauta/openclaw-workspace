import type { Metadata } from "next";
import Link from "next/link";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";
import { getTiposEnsino, getCoursesByTipoEnsino } from "@/lib/courses";
import { slugify } from "@/lib/slug";

export const metadata: Metadata = {
  title: "Tipos de ensino",
  description: "Explora cursos do ensino superior em Portugal por tipo de ensino: universitário, politécnico ou militar e policial.",
  alternates: { canonical: "/tipos-ensino/" }
};

const TIPO_DESCRIPTIONS: Record<string, string> = {
  "Ensino Superior Público Universitário": "Universidades públicas com formação académica e científica de base.",
  "Ensino Superior Público Politécnico": "Institutos politécnicos com formação técnica e profissionalizante.",
  "Ensino Superior Público Militar e Policial Universitário": "Instituições militares e policiais de ensino superior universitário.",
};

export default function TiposEnsinoPage() {
  const tipos = getTiposEnsino();

  return (
    <Container className="py-10">
      <Breadcrumbs items={[{ label: "Tipos de ensino" }]} />
      <section>
        <h1 className="text-4xl font-bold tracking-tight text-slate-950">Tipos de ensino</h1>
        <p className="mt-4 text-slate-700">
          Filtra cursos do ensino superior em Portugal pelo tipo de instituição.
        </p>
      </section>

      <section className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {tipos.map((tipo) => {
          const count = getCoursesByTipoEnsino(slugify(tipo)).length;
          const description = TIPO_DESCRIPTIONS[tipo];
          return (
            <Link
              key={tipo}
              href={`/tipos-ensino/${slugify(tipo)}/`}
              className="group flex h-full flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
            >
              <h2 className="text-lg font-semibold leading-snug text-slate-950 group-hover:text-brand-700">{tipo}</h2>
              {description && <p className="mt-2 text-sm text-slate-500 leading-relaxed">{description}</p>}
              <p className="mt-3 text-sm text-slate-600">{count} curso{count === 1 ? "" : "s"}</p>
              <span className="mt-auto pt-4 text-sm font-semibold text-brand-700 group-hover:text-brand-900">Ver cursos →</span>
            </Link>
          );
        })}
      </section>
    </Container>
  );
}
