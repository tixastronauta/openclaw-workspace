import type { Metadata } from "next";
import Link from "next/link";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";
import { getTop10Metrics } from "@/lib/top10";
import { TOP10_ICONS } from "@/lib/top10Icons";

export const metadata: Metadata = {
  title: "Top 10 cursos",
  description: "Rankings Top 10 de cursos do ensino superior em Portugal por nacionalidade, sexo, médias finais, empregabilidade e perfil etário.",
  alternates: { canonical: "/top-10-cursos/" }
};

export default function Top10IndexPage() {
  const metrics = getTop10Metrics();

  return (
    <Container className="py-10">
      <Breadcrumbs items={[{ label: "Top 10 cursos" }]} />
      <section>
        <h1 className="text-4xl font-bold tracking-tight text-slate-950">Top 10 cursos</h1>
        <p className="mt-4 text-slate-700">
          Rankings calculados a partir dos dados estatísticos disponíveis para cada curso. Quando não há dados suficientes, o curso não entra nesse ranking.
        </p>
      </section>

      <div className="mt-10 grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
        {metrics.map((metric) => {
          const Icon = TOP10_ICONS[metric.id];
          return (
            <Link
              key={metric.id}
              href={`/top-10-cursos/${metric.id}/`}
              className="group flex flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
            >
              {Icon && (
                <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-brand-600 transition group-hover:bg-brand-100">
                  <Icon className="h-5 w-5" />
                </div>
              )}
              <h2 className="text-lg font-semibold text-slate-950 group-hover:text-brand-700">
                {metric.shortTitle}
              </h2>
              <p className="mt-2 text-sm text-slate-500">{metric.description}</p>
            </Link>
          );
        })}
      </div>
    </Container>
  );
}
