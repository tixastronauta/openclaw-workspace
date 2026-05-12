import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ADS_ENABLED, AdSlot } from "@/components/AdSlot";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";
import { GradesChart } from "@/components/GradesChart";
import { InfoCursosBarChart } from "@/components/InfoCursosBarChart";
import { InfoCursosPieChart } from "@/components/InfoCursosPieChart";
import { MapEmbed } from "@/components/MapEmbed";
import { getAllCourses, getCourseBySlug, getFacultySlugByInstitution, getRelatedCourses } from "@/lib/courses";
import { slugify } from "@/lib/slug";
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
  const keywordTerms = [
    course.courseName,
    course.institutionName,
    course.cycle,
    ...course.courseName
      .split(/[^A-Za-z0-9À-ÿ]+/)
      .map((word) => word.trim())
      .filter((word) => word.length > 2),
  ].filter((term): term is string => Boolean(term));

  const keywords = Array.from(new Set(keywordTerms.map((term) => term.toLocaleLowerCase("pt-PT"))));

  return {
    title: course.institutionName ? `${course.courseName} - ${course.institutionName}` : course.courseName,
    description,
    keywords,
    alternates: { canonical: `/cursos/${course.slug}/` },
    openGraph: {
      title: `${course.courseName} | ${siteConfig.name}`,
      description,
      url: `/cursos/${course.slug}/`,
      type: "article"
    }
  };
}

// Icon: external link (opens in new tab)
function ExternalLinkIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="ml-1.5 inline-block h-3.5 w-3.5 shrink-0 opacity-60" aria-hidden="true">
      <path fillRule="evenodd" d="M4.25 5.5a.75.75 0 00-.75.75v8.5c0 .414.336.75.75.75h8.5a.75.75 0 00.75-.75v-4a.75.75 0 011.5 0v4A2.25 2.25 0 0112.75 17h-8.5A2.25 2.25 0 012 14.75v-8.5A2.25 2.25 0 014.25 4h5a.75.75 0 010 1.5h-5zm6.5-3a.75.75 0 01.75-.75h3.5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0V3.56l-4.72 4.72a.75.75 0 01-1.06-1.06l4.72-4.72h-1.69a.75.75 0 01-.75-.75z" clipRule="evenodd" />
    </svg>
  );
}

function UsefulLinks({ course }: { course: Awaited<ReturnType<typeof getCourseBySlug>> }) {
  if (!course) return null;
  const hasLinks = course.courseUrl || course.institutionUrl || course.infoCursosUrl || course.dgesUrl;
  if (!hasLinks) return null;

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-slate-950">Ligações úteis</h2>
      <div className="mt-4 flex flex-col gap-2">
        {course.courseUrl && (
          <a
            href={course.courseUrl}
            rel="nofollow noopener noreferrer"
            target="_blank"
            className="flex items-center rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 hover:border-brand-600 hover:text-brand-700"
          >
            Página do curso
            <ExternalLinkIcon />
          </a>
        )}
        {course.institutionUrl && (
          <a
            href={course.institutionUrl}
            rel="nofollow noopener noreferrer"
            target="_blank"
            className="flex items-center rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 hover:border-brand-600 hover:text-brand-700"
          >
            Site da instituição
            <ExternalLinkIcon />
          </a>
        )}
        {course.infoCursosUrl && (
          <a
            href={course.infoCursosUrl}
            rel="nofollow noopener noreferrer"
            target="_blank"
            className="flex items-center rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 hover:border-brand-600 hover:text-brand-700"
          >
            InfoCursos oficial
            <ExternalLinkIcon />
          </a>
        )}
        {course.dgesUrl && (
          <a
            href={course.dgesUrl}
            rel="nofollow noopener noreferrer"
            target="_blank"
            className="flex items-center rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 hover:border-brand-600 hover:text-brand-700"
          >
            DGES oficial
            <ExternalLinkIcon />
          </a>
        )}
      </div>
    </section>
  );
}

export default async function CourseDetailPage({ params }: PageProps) {
  const { slug } = await params;
  const course = getCourseBySlug(slug);
  if (!course) notFound();

  const relatedCourses = getRelatedCourses(course);
  const sameInstitutionCourses = getAllCourses()
    .filter((item) =>
      item.slug !== course.slug &&
      item.institutionName &&
      item.institutionName === course.institutionName &&
      item.institutionCode === course.institutionCode,
    )
    .slice(0, 4);
  const facultySlug = getFacultySlugByInstitution(course.institutionName, course.institutionCode);
  const institutionLabel = [course.institutionName, course.institutionSigla ? `(${course.institutionSigla})` : undefined].filter(Boolean).join(" ");
  const mapQuery = [course.morada, course.cidade, course.distrito, course.institutionName].filter(Boolean).join(", ");

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

  const breadcrumbs = [
    { label: "Cursos", href: "/cursos/" },
    ...(course.institutionName && facultySlug
      ? [{ label: institutionLabel, href: `/faculdades/${facultySlug}/` }]
      : []),
    { label: course.courseName }
  ];

  return (
    <Container className="py-10">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <Breadcrumbs items={breadcrumbs} />

      <article className="grid gap-8 lg:grid-cols-[1fr_300px]">
        {/* Left column */}
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-slate-950">{course.courseName}</h1>
          {course.institutionName && (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              {facultySlug
                ? <Link href={`/faculdades/${facultySlug}/`} className="text-lg font-medium text-slate-700 hover:text-brand-700">{institutionLabel}</Link>
                : <p className="text-lg font-medium text-slate-700">{institutionLabel}</p>}
            </div>
          )}
          <div className="mt-3 flex flex-wrap gap-2 text-xs font-medium uppercase tracking-wide text-slate-500">
            {course.cycle && (
              <Link href={`/ciclos/${slugify(course.cycle)}/`} className="rounded-full bg-slate-100 px-3 py-1 hover:bg-brand-100 hover:text-brand-700">{course.cycle}</Link>
            )}
          </div>

          {course.courseDescription && (
            <blockquote className="mt-6 rounded-2xl border-l-4 border-brand-600 bg-brand-50 px-6 py-5">
              <p className="text-base leading-7 text-slate-800">{course.courseDescription}</p>
            </blockquote>
          )}

          {/* Unemployment rate */}
          {course.metrics?.unemploymentRate !== undefined && (
            <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-2xl font-semibold text-slate-950">Taxa de desemprego</h2>
              <p className="mt-3 text-slate-700">
                Segundo os dados do IEFP, a taxa de desemprego dos diplomados neste curso é de{" "}
                <span className="font-bold text-brand-700">
                  {(course.metrics.unemploymentRate * 100).toFixed(1)}%
                </span>
                {course.metrics.graduatesCount !== undefined && (
                  <span>
                    {" "}(baseada em {Math.round(course.metrics.graduatesCount)} diplomados
                    {course.metrics.unemployedCount !== undefined &&
                      `, cerca de ${course.metrics.unemployedCount.toFixed(1)} desempregados`}
                    ).
                  </span>
                )}
              </p>
            </section>
          )}

          <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-2xl font-semibold text-slate-950">Notas de entrada</h2>
            <p className="mt-3 max-w-3xl text-slate-700">
              Consulta as notas de entrada disponíveis para este curso e confirma sempre a informação atualizada nas fontes oficiais.
            </p>
            {course.grades.length > 0 ? (
              <GradesChart grades={course.grades} />
            ) : (
              <p className="mt-4 text-sm text-slate-600">Não existem notas de entrada disponíveis para este curso.</p>
            )}
          </section>

          {ADS_ENABLED && (
            <section className="mt-8">
              <AdSlot label="Página de curso — conteúdo intermédio" />
            </section>
          )}

          {/* Final grades distribution */}
          {course.finalGradesDistribution && course.finalGradesDistribution.length > 0 && (
            <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-2xl font-semibold text-slate-950">Distribuição das classificações finais</h2>
              <p className="mt-1 text-sm text-slate-500">Percentagem de alunos por nota final de curso</p>
              <div className="mt-4">
                <InfoCursosBarChart
                  data={course.finalGradesDistribution.map((item) => ({
                    label: item.grade,
                    value: Math.round(item.percentage * 1000) / 10
                  }))}
                  unit="%"
                />
              </div>
            </section>
          )}

          {/* Gender and nationality */}
          {(course.genderData || course.nationalityData) && (
            <div className="mt-8 grid gap-6 sm:grid-cols-2">
              {course.genderData && (
                <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                  <h2 className="text-lg font-semibold text-slate-950">Género dos alunos</h2>
                  <InfoCursosPieChart
                    data={[
                      { name: "Homens", value: Math.round(course.genderData.men * 1000) / 10, color: "#2563eb" },
                      { name: "Mulheres", value: Math.round(course.genderData.women * 1000) / 10, color: "#db2777" }
                    ]}
                    unit="%"
                  />
                </section>
              )}
              {course.nationalityData && (
                <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                  <h2 className="text-lg font-semibold text-slate-950">Nacionalidade dos alunos</h2>
                  <InfoCursosPieChart
                    data={[
                      { name: "Portugueses", value: Math.round(course.nationalityData.portuguese * 1000) / 10, color: "#16a34a" },
                      { name: "Estrangeiros", value: Math.round(course.nationalityData.foreign * 1000) / 10, color: "#ea580c" }
                    ]}
                    unit="%"
                  />
                </section>
              )}
            </div>
          )}

          {/* Age distribution */}
          {course.ageDistribution && course.ageDistribution.length > 0 && (
            <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-2xl font-semibold text-slate-950">Distribuição por idades</h2>
              <p className="mt-1 text-sm text-slate-500">Percentagem de alunos por grupo etário</p>
              <div className="mt-4">
                <InfoCursosBarChart
                  data={course.ageDistribution.map((item) => ({
                    label: item.age,
                    value: Math.round(item.percentage * 1000) / 10
                  }))}
                  unit="%"
                  color="#7c3aed"
                />
              </div>
            </section>
          )}

          {sameInstitutionCourses.length > 0 && (
            <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-2xl font-semibold text-slate-950">Outros cursos da mesma instituição</h2>
              <div className="mt-4 grid gap-2 sm:grid-cols-2">
                {sameInstitutionCourses.map((sameCourse) => (
                  <Link key={sameCourse.slug} href={`/cursos/${sameCourse.slug}/`} className="rounded-lg px-3 py-2 text-sm font-medium text-slate-700 hover:bg-brand-50 hover:text-brand-700">
                    <span className="block">{sameCourse.courseName}</span>
                    {sameCourse.cycle && <span className="block text-xs font-normal text-slate-500">{sameCourse.cycle}</span>}
                  </Link>
                ))}
              </div>
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

        {/* Right column */}
        <aside className="grid content-start gap-6">
          <UsefulLinks course={course} />
          <MapEmbed query={mapQuery} title={`Localização de ${institutionLabel || course.courseName}`} />
          {ADS_ENABLED && <AdSlot label="Página de curso — lateral" />}
        </aside>
      </article>
    </Container>
  );
}
