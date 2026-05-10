import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ADS_ENABLED, AdSlot } from "@/components/AdSlot";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";
import { GradesChart } from "@/components/GradesChart";
import { getAllCourses, getCourseBySlug, getFacultySlugByInstitution, getRelatedCourses } from "@/lib/courses";
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

// Icon: external link (opens in new tab)
function ExternalLinkIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="ml-1.5 inline-block h-3.5 w-3.5 shrink-0 opacity-60" aria-hidden="true">
      <path fillRule="evenodd" d="M4.25 5.5a.75.75 0 00-.75.75v8.5c0 .414.336.75.75.75h8.5a.75.75 0 00.75-.75v-4a.75.75 0 011.5 0v4A2.25 2.25 0 0112.75 17h-8.5A2.25 2.25 0 012 14.75v-8.5A2.25 2.25 0 014.25 4h5a.75.75 0 010 1.5h-5zm6.5-3a.75.75 0 01.75-.75h3.5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0V3.56l-4.72 4.72a.75.75 0 01-1.06-1.06l4.72-4.72h-1.69a.75.75 0 01-.75-.75z" clipRule="evenodd" />
    </svg>
  );
}

function OfficialSources({ course }: { course: Awaited<ReturnType<typeof getCourseBySlug>> }) {
  if (!course) return null;
  const hasLinks = course.infoCursosUrl || course.dgesUrl;
  if (!hasLinks) return null;

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-slate-950">Fontes oficiais</h2>
      <p className="mt-2 text-sm leading-6 text-slate-600">
        Confirma sempre dados e candidaturas nas fontes oficiais.
      </p>
      <div className="mt-4 flex flex-col gap-2">
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
  const facultySlug = getFacultySlugByInstitution(course.institutionName, course.institutionCode);

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
      ? [{ label: course.institutionName, href: `/faculdades/${facultySlug}/` }]
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
            facultySlug
              ? <Link href={`/faculdades/${facultySlug}/`} className="mt-3 block text-lg font-medium text-slate-700 hover:text-brand-700">{course.institutionName}</Link>
              : <p className="mt-3 text-lg font-medium text-slate-700">{course.institutionName}</p>
          )}
          <div className="mt-3 flex flex-wrap gap-2 text-xs font-medium uppercase tracking-wide text-slate-500">
            {course.cycle && <span className="rounded-full bg-slate-100 px-3 py-1">{course.cycle}</span>}
            {course.courseCode && <span className="rounded-full bg-slate-100 px-3 py-1">Curso {course.courseCode}</span>}
            {course.reference && <span className="rounded-full bg-slate-100 px-3 py-1">Ref. {course.reference}</span>}
          </div>
          <p className="mt-4 max-w-3xl text-slate-700">
            Consulta as notas de entrada disponíveis para este curso e confirma sempre a informação atualizada nas fontes oficiais indicadas.
          </p>

          <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-2xl font-semibold text-slate-950">Notas de entrada</h2>
            {course.grades.length > 0 ? (
              <>
                <GradesChart grades={course.grades} />
                <div className="mt-6 overflow-x-auto">
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
              </>
            ) : (
              <p className="mt-4 text-sm text-slate-600">Não existem notas de entrada disponíveis para este curso.</p>
            )}
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

        {/* Right column */}
        <aside className="grid content-start gap-6">
          <OfficialSources course={course} />
          {ADS_ENABLED && <AdSlot label="Página de curso — lateral" />}
        </aside>
      </article>
    </Container>
  );
}
