import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ADS_ENABLED, AdSlot } from "@/components/AdSlot";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";
import { getAllCourses, getCourseBySlug, getRelatedCourses } from "@/lib/courses";
import { siteConfig } from "@/lib/site";

type PageProps = {
  params: Promise<{ slug: string }>;
};

export function generateStaticParams() {
  return getAllCourses().map((course) => ({ slug: course.slug }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const course = getCourseBySlug(slug);
  if (!course) return {};

  const description = `Notas de entrada disponíveis para ${course.courseName}${course.institutionName ? ` em ${course.institutionName}` : ""} e ligações para fontes oficiais DGES e InfoCursos.`;

  return {
    title: course.institutionName ? `${course.courseName} - ${course.institutionName}` : course.courseName,
    description,
    alternates: { canonical: `/cursos/${course.slug}/` },
    openGraph: {
      title: `${course.courseName} | ${siteConfig.name}`,
      description,
      url: `/cursos/${course.slug}/`,
      type: "article"
    }
  };
}

export default async function CourseDetailPage({ params }: PageProps) {
  const { slug } = await params;
  const course = getCourseBySlug(slug);
  if (!course) notFound();

  const relatedCourses = getRelatedCourses(course);
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Course",
    name: course.institutionName ? `${course.courseName} - ${course.institutionName}` : course.courseName,
    url: `${siteConfig.url}/cursos/${course.slug}/`,
    provider: {
      "@type": "Organization",
      name: siteConfig.name,
      url: siteConfig.url
    }
  };

  return (
    <Container className="py-10">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <Breadcrumbs items={[{ label: "Cursos", href: "/cursos/" }, { label: course.courseName }]} />

      <article className="grid gap-8 lg:grid-cols-[1fr_320px]">
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-slate-950">{course.courseName}</h1>
          {course.institutionName && <p className="mt-3 text-lg font-medium text-slate-700">{course.institutionName}</p>}
          <div className="mt-3 flex flex-wrap gap-2 text-xs font-medium uppercase tracking-wide text-slate-500">
            {course.cycle && <span className="rounded-full bg-slate-100 px-3 py-1">{course.cycle}</span>}
            {course.courseCode && <span className="rounded-full bg-slate-100 px-3 py-1">Curso {course.courseCode}</span>}
            {course.reference && <span className="rounded-full bg-slate-100 px-3 py-1">Ref. {course.reference}</span>}
          </div>
          <p className="mt-4 max-w-3xl text-slate-700">
            Consulta as notas de entrada disponíveis para este curso/instituição e confirma sempre a informação atualizada nas fontes oficiais indicadas.
          </p>

          <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-2xl font-semibold text-slate-950">Notas de entrada</h2>
            {course.grades.length > 0 ? (
              <div className="mt-5 overflow-x-auto">
                <table className="w-full min-w-72 text-left text-sm">
                  <thead className="bg-slate-50 text-slate-700">
                    <tr>
                      <th className="rounded-l-lg px-4 py-3 font-semibold">Ano</th>
                      <th className="px-4 py-3 font-semibold">Fase</th>
                      <th className="rounded-r-lg px-4 py-3 font-semibold">Nota</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {course.grades.map((grade) => (
                      <tr key={`${grade.year}-${grade.phase ?? "sem-fase"}`}>
                        <td className="px-4 py-3 text-slate-700">{grade.year}</td>
                        <td className="px-4 py-3 text-slate-700">{grade.phase ?? "—"}</td>
                        <td className="px-4 py-3 font-semibold text-slate-950">{grade.grade}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="mt-4 text-sm text-slate-600">Não existem notas de entrada disponíveis para este curso.</p>
            )}
          </section>

          <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-2xl font-semibold text-slate-950">Fontes oficiais</h2>
            <p className="mt-3 text-sm leading-6 text-slate-700">
              Universidade.pt não é uma fonte oficial. Usa estes links para confirmar dados, regras de candidatura e informação atualizada.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              {course.infoCursosUrl && (
                <a href={course.infoCursosUrl} rel="nofollow noopener noreferrer" target="_blank" className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:border-brand-600 hover:text-brand-700">
                  InfoCursos oficial
                </a>
              )}
              {course.dgesUrl && (
                <a href={course.dgesUrl} rel="nofollow noopener noreferrer" target="_blank" className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:border-brand-600 hover:text-brand-700">
                  DGES oficial
                </a>
              )}
            </div>
          </section>

          {ADS_ENABLED && (
            <section className="mt-8">
              <AdSlot label="Página de curso — conteúdo intermédio" />
            </section>
          )}

          {relatedCourses.length > 0 && (
            <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-2xl font-semibold text-slate-950">Cursos relacionados</h2>
              <div className="mt-4 grid gap-2 sm:grid-cols-2">
                {relatedCourses.map((related) => (
                  <Link key={related.slug} href={`/cursos/${related.slug}/`} className="rounded-lg px-3 py-2 text-sm font-medium text-slate-700 hover:bg-brand-50 hover:text-brand-700">
                    <span className="block">{related.courseName}</span>
                    {related.institutionName && <span className="block text-xs font-normal text-slate-500">{related.institutionName}</span>}
                  </Link>
                ))}
              </div>
            </section>
          )}
        </div>

        <aside className="grid content-start gap-6">
          {ADS_ENABLED && <AdSlot label="Página de curso — lateral" />}
          <div className="rounded-2xl border border-brand-100 bg-brand-50 p-5 text-sm leading-6 text-brand-900">
            <h2 className="font-semibold">Nota importante</h2>
            <p className="mt-2">As notas históricas ajudam a comparar anos anteriores, mas não garantem resultados futuros.</p>
          </div>
        </aside>
      </article>
    </Container>
  );
}
