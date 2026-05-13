import type { Metadata } from "next";
import Link from "next/link";
import { Trophy } from "lucide-react";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";
import { DistrictMiniMap } from "@/components/DistrictMiniMap";
import { getFacultySlugByInstitution } from "@/lib/courses";
import { formatTop10Value, getTop10Metrics } from "@/lib/top10";

export const metadata: Metadata = {
  title: "Top 10 cursos",
  description: "Rankings Top 10 de cursos do ensino superior em Portugal por nacionalidade, sexo, médias finais, empregabilidade e perfil etário.",
  alternates: { canonical: "/top-10/" }
};

export default function Top10Page() {
  const metrics = getTop10Metrics();

  return (
    <Container className="py-10">
      <Breadcrumbs items={[{ label: "Top 10" }]} />
      <section>
        <h1 className="text-4xl font-bold tracking-tight text-slate-950">Top 10 cursos</h1>
        <p className="mt-4 text-slate-700">
          Rankings calculados a partir dos dados estatísticos disponíveis para cada curso. Quando não há dados suficientes, o curso não entra nesse ranking.
        </p>
      </section>

      <nav className="mt-8 flex flex-wrap gap-2" aria-label="Navegação dos rankings Top 10">
        {metrics.map((metric) => (
          <a key={metric.id} href={`#${metric.id}`} className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 hover:border-brand-600 hover:text-brand-700">
            {metric.title.replace("Top 10 cursos ", "")}
          </a>
        ))}
      </nav>

      <section className="mt-10 grid gap-10">
        {metrics.map((metric) => (
          <section key={metric.id} id={metric.id} className="scroll-mt-24 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="border-b border-slate-100 pb-4">
              <h2 className="text-2xl font-semibold text-slate-950">{metric.title}</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">{metric.description}</p>
            </div>

            {metric.items.length > 0 ? (
              <ol className="mt-4 divide-y divide-slate-100">
                {metric.items.map(({ course, value }, index) => {
                  const facultySlug = getFacultySlugByInstitution(course.institutionName, course.institutionCode);
                  const institutionLabel = [course.institutionName, course.institutionSigla ? `(${course.institutionSigla})` : undefined].filter(Boolean).join(" ");

                  return (
                    <li key={course.slug} className="grid gap-3 rounded-xl px-2 py-4 transition-colors hover:bg-slate-50 sm:grid-cols-[3rem_1fr_auto_auto] sm:items-center">
                      {index === 0 ? (
                        <div className="flex flex-col items-center gap-0.5">
                          <Trophy className="h-6 w-6 text-yellow-400" strokeWidth={1.5} />
                          <span className="text-xs font-bold text-yellow-400">1</span>
                        </div>
                      ) : index === 1 ? (
                        <div className="flex flex-col items-center gap-0.5">
                          <Trophy className="h-6 w-6 text-slate-400" strokeWidth={1.5} />
                          <span className="text-xs font-bold text-slate-400">2</span>
                        </div>
                      ) : index === 2 ? (
                        <div className="flex flex-col items-center gap-0.5">
                          <Trophy className="h-6 w-6 text-amber-600" strokeWidth={1.5} />
                          <span className="text-xs font-bold text-amber-600">3</span>
                        </div>
                      ) : (
                        <span className="block text-center text-[20px] font-bold tabular-nums text-slate-300">{index + 1}</span>
                      )}
                      <div>
                        <Link href={`/cursos/${course.slug}/`} className="font-semibold text-slate-950 hover:text-brand-700">
                          {course.courseName}
                        </Link>
                        {institutionLabel && (
                          <p className="mt-1 text-sm text-slate-500">
                            {facultySlug ? (
                              <Link href={`/faculdades/${facultySlug}/`} className="hover:text-brand-700">{institutionLabel}</Link>
                            ) : institutionLabel}
                          </p>
                        )}
                      </div>
                      <DistrictMiniMap districtName={course.distrito} />
                      <div className="rounded-xl bg-brand-50 px-3 py-2 text-left sm:text-right">
                        <p className="text-xs font-medium uppercase tracking-wide text-brand-700">{metric.valueLabel}</p>
                        <p className="text-lg font-bold tabular-nums text-brand-900">{formatTop10Value(metric.id, value)}</p>
                      </div>
                    </li>
                  );
                })}
              </ol>
            ) : (
              <p className="mt-4 text-sm text-slate-600">Ainda não há dados suficientes para este ranking.</p>
            )}
          </section>
        ))}
      </section>
    </Container>
  );
}
