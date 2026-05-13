import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { ADS_ENABLED, AdSlot } from "@/components/AdSlot";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";
import { CourseCard } from "@/components/CourseCard";
import { MapEmbed } from "@/components/MapEmbed";
import { getAllFaculties, getFacultyBySlug, getUniversityForFaculty } from "@/lib/courses";

type PageProps = {
  params: Promise<{ slug: string }>;
};

export function generateStaticParams() {
  return getAllFaculties().map((faculty) => ({ slug: faculty.slug }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const faculty = getFacultyBySlug(slug);
  if (!faculty) return {};

  return {
    title: `${faculty.institutionName} — cursos`,
    description: `Cursos disponíveis em ${faculty.institutionName} no Universidade.pt.`,
    alternates: { canonical: `/faculdades/${faculty.slug}/` }
  };
}

function ExternalLinkIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="ml-1.5 inline-block h-3.5 w-3.5 shrink-0 opacity-60" aria-hidden="true">
      <path fillRule="evenodd" d="M4.25 5.5a.75.75 0 00-.75.75v8.5c0 .414.336.75.75.75h8.5a.75.75 0 00.75-.75v-4a.75.75 0 011.5 0v4A2.25 2.25 0 0112.75 17h-8.5A2.25 2.25 0 012 14.75v-8.5A2.25 2.25 0 014.25 4h5a.75.75 0 010 1.5h-5zm6.5-3a.75.75 0 01.75-.75h3.5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0V3.56l-4.72 4.72a.75.75 0 01-1.06-1.06l4.72-4.72h-1.69a.75.75 0 01-.75-.75z" clipRule="evenodd" />
    </svg>
  );
}

export default async function FacultyPage({ params }: PageProps) {
  const { slug } = await params;
  const faculty = getFacultyBySlug(slug);
  if (!faculty) notFound();

  const mapQuery = [faculty.morada, faculty.cidade, faculty.distrito, faculty.institutionName].filter(Boolean).join(", ");
  const university = getUniversityForFaculty(faculty);

  const breadcrumbs = [
    { label: "Universidades", href: "/universidades/" },
    // Only show university crumb when faculty has a distinct parent (not standalone)
    ...(faculty.parentInstitutionName && university
      ? [{ label: university.acronym ?? university.name, title: university.name, href: `/universidades/${university.slug}/` }]
      : []),
    { label: faculty.institutionName }
  ];

  return (
    <Container className="py-6 sm:py-10">
      <Breadcrumbs items={breadcrumbs} />
      <section>
        <h1 className="text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl lg:text-4xl">
          {faculty.institutionName}
          {faculty.institutionSigla ? <span className="ml-2 text-base font-semibold text-slate-500">({faculty.institutionSigla})</span> : null}
        </h1>
        {faculty.parentInstitutionName && university && (
          <p className="mt-1 text-base text-slate-500">
            <Link href={`/universidades/${university.slug}/`} className="hover:text-brand-700">
              {faculty.parentInstitutionName}
            </Link>
          </p>
        )}
        <div className="mt-3 flex flex-wrap gap-2 text-xs font-medium uppercase tracking-wide text-slate-500">
          <span className="rounded-full bg-slate-100 px-3 py-1">{faculty.courses.length} curso{faculty.courses.length === 1 ? "" : "s"}</span>
        </div>
        <p className="mt-4 text-slate-700">
          Cursos desta instituição de ensino superior.
        </p>
      </section>

      {ADS_ENABLED && (
        <div className="mt-10">
          <AdSlot label="Faculdade — antes da lista de cursos" />
        </div>
      )}

      <section className="mt-10 grid gap-8 lg:grid-cols-[1fr_300px]">
        <div className="min-w-0">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {faculty.courses.map((course) => <CourseCard key={course.slug} course={course} />)}
          </div>
        </div>
        <aside className="grid content-start gap-6">
          {faculty.institutionUrl && (
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-slate-950">Ligações úteis</h2>
              <a
                href={faculty.institutionUrl}
                rel="nofollow noopener noreferrer"
                target="_blank"
                className="mt-4 flex items-center rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 hover:border-brand-600 hover:text-brand-700"
              >
                Site da instituição
                <ExternalLinkIcon />
              </a>
            </section>
          )}
          <MapEmbed query={mapQuery} title={`Localização de ${faculty.institutionName}`} />
        </aside>
      </section>
    </Container>
  );
}
