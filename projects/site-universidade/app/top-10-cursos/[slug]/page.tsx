import type { Metadata } from "next";
import Link from "next/link";
import { Trophy } from "lucide-react";
import { notFound } from "next/navigation";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";
import { DistrictMiniMap } from "@/components/DistrictMiniMap";
import { getFacultySlugByInstitution } from "@/lib/courses";
import { formatTop10Value, getTop10Metrics } from "@/lib/top10";
import { TOP10_ICONS } from "@/lib/top10Icons";
import { siteConfig } from "@/lib/site";

type PageProps = {
  params: Promise<{ slug: string }>;
};

export function generateStaticParams() {
  return getTop10Metrics().map((m) => ({ slug: m.id }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const metric = getTop10Metrics().find((m) => m.id === slug);
  if (!metric) return {};

  return {
    title: metric.title,
    description: metric.description,
    alternates: { canonical: `/top-10-cursos/${slug}/` },
    openGraph: {
      title: `${metric.title} | ${siteConfig.name}`,
      description: metric.description,
      url: `/top-10-cursos/${slug}/`,
      type: "article"
    }
  };
}

export default async function Top10MetricPage({ params }: PageProps) {
  const { slug } = await params;
  const metrics = getTop10Metrics();
  const metric = metrics.find((m) => m.id === slug);
  if (!metric) notFound();

  return (
    <Container className="py-10">
      <Breadcrumbs items={[
        { label: "Top 10 cursos", href: "/top-10-cursos/" },
        { label: metric.shortTitle }
      ]} />

      <section>
        <h1 className="text-4xl font-bold tracking-tight text-slate-950">{metric.title}</h1>
        <p className="mt-4 text-slate-700">{metric.description}</p>
      </section>

      <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        {metric.items.length > 0 ? (
          <ol className="divide-y divide-slate-100">
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
          <p className="text-sm text-slate-600">Ainda não há dados suficientes para este ranking.</p>
        )}
      </section>

      {metrics.filter((m) => m.id !== slug).length > 0 && (
        <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-400">Outros top 10</h2>
          <ul className="mt-2 divide-y divide-slate-100">
            {metrics.filter((m) => m.id !== slug).map((m) => (
              <li key={m.id}>
                <Link href={`/top-10-cursos/${m.id}/`} className="group -mx-3 flex items-start gap-3 rounded-xl px-3 py-4 transition hover:bg-brand-50">
                  {(() => { const Icon = TOP10_ICONS[m.id]; return Icon ? <Icon className="mt-0.5 size-4 shrink-0 text-slate-300 transition group-hover:text-slate-400" /> : null; })()}
                  <div className="flex-1">
                    <p className="font-semibold text-slate-900 group-hover:text-brand-700">{m.shortTitle}</p>
                    <p className="mt-0.5 text-sm text-slate-500">{m.description}</p>
                  </div>
                  <span className="mt-0.5 shrink-0 text-slate-300 transition group-hover:text-brand-500">→</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </Container>
  );
}
