import type { Metadata } from "next";
import { existsSync } from "fs";
import { join } from "path";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ADS_ENABLED, AdSlot } from "@/components/AdSlot";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";
import { CourseCard } from "@/components/CourseCard";
import { MapEmbed } from "@/components/MapEmbed";
import { getAllUniversities, getUniversityBySlug } from "@/lib/courses";

type PageProps = {
  params: Promise<{ slug: string }>;
};

export function generateStaticParams() {
  return getAllUniversities().map((university) => ({ slug: university.slug }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const university = getUniversityBySlug(slug);
  if (!university) return {};

  const title = university.name + (university.acronym ? ` (${university.acronym})` : "");
  return {
    title: `${title} — cursos`,
    description: `Faculdades e cursos de ${university.name} disponíveis no Universidade.pt.`,
    alternates: { canonical: `/universidades/${university.slug}/` }
  };
}

function ExternalLinkIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="ml-1.5 inline-block h-3.5 w-3.5 shrink-0 opacity-60" aria-hidden="true">
      <path fillRule="evenodd" d="M4.25 5.5a.75.75 0 00-.75.75v8.5c0 .414.336.75.75.75h8.5a.75.75 0 00.75-.75v-4a.75.75 0 011.5 0v4A2.25 2.25 0 0112.75 17h-8.5A2.25 2.25 0 012 14.75v-8.5A2.25 2.25 0 014.25 4h5a.75.75 0 010 1.5h-5zm6.5-3a.75.75 0 01.75-.75h3.5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0V3.56l-4.72 4.72a.75.75 0 01-1.06-1.06l4.72-4.72h-1.69a.75.75 0 01-.75-.75z" clipRule="evenodd" />
    </svg>
  );
}

export default async function UniversityPage({ params }: PageProps) {
  const { slug } = await params;
  const university = getUniversityBySlug(slug);
  if (!university) notFound();

  const hasFaculties = university.faculties.length > 0;
  const logoFile = university.acronym ? `${university.acronym}.png` : null;
  const logoUrl = logoFile && existsSync(join(process.cwd(), "public", "logos", logoFile))
    ? `/logos/${logoFile}`
    : null;
  const displayName = university.name + (university.acronym ? ` (${university.acronym})` : "");

  // For map query, prefer first faculty location, else use university name
  const locationSource = university.faculties[0] ?? null;
  const mapQuery = locationSource
    ? [locationSource.morada, locationSource.cidade, locationSource.distrito, university.name].filter(Boolean).join(", ")
    : university.name;

  return (
    <Container className="py-6 sm:py-10">
      <Breadcrumbs items={[{ label: "Universidades", href: "/universidades/" }, { label: university.name }]} />

      <section>
        <h1 className="text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl lg:text-4xl">{displayName}</h1>
        <div className="mt-3 flex flex-wrap gap-2 text-xs font-medium uppercase tracking-wide text-slate-500">
          {hasFaculties
            ? <span className="rounded-full bg-slate-100 px-3 py-1">{university.faculties.length} faculdade{university.faculties.length === 1 ? "" : "s"}</span>
            : <span className="rounded-full bg-slate-100 px-3 py-1">{university.courses.length} curso{university.courses.length === 1 ? "" : "s"}</span>}
        </div>
      </section>

      {ADS_ENABLED && (
        <div className="mt-10">
          <AdSlot label="Universidade — antes da lista" />
        </div>
      )}

      <section className="mt-10 grid gap-8 lg:grid-cols-[1fr_300px]">
        <div className="min-w-0">
          {hasFaculties ? (
            <>
<div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {university.faculties.map((faculty) => (
                  <Link
                    key={faculty.slug}
                    href={`/faculdades/${faculty.slug}/`}
                    className="group flex h-full flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
                  >
                    <div>
                      <h3 className="text-base font-semibold text-slate-950 group-hover:text-brand-700">
                        {faculty.institutionName}
                        {faculty.institutionSigla ? <span className="ml-1.5 font-semibold text-slate-400">({faculty.institutionSigla})</span> : null}
                      </h3>
                      <p className="mt-2 text-sm text-slate-600">
                        {faculty.courses.length} curso{faculty.courses.length === 1 ? "" : "s"}
                      </p>
                    </div>
                    <span className="mt-auto pt-4 text-sm font-semibold text-brand-700 group-hover:text-brand-900">Ver cursos →</span>
                  </Link>
                ))}
              </div>
            </>
          ) : (
            <>
              <h2 className="mb-5 text-2xl font-semibold text-slate-950">Cursos</h2>
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {university.courses.map((course) => <CourseCard key={course.slug} course={course} />)}
              </div>
            </>
          )}
        </div>

        <aside className="grid content-start gap-6">
          {(logoUrl || university.url) && (
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              {logoUrl && (
                <div className={`flex items-center justify-center${university.url ? " mb-5" : ""}`}>
                  <Image
                    src={logoUrl}
                    alt={university.name}
                    width={280}
                    height={112}
                    className="max-h-28 w-auto object-contain"
                  />
                </div>
              )}
              {university.url && (
                <a
                  href={university.url}
                  rel="nofollow noopener noreferrer"
                  target="_blank"
                  className="flex items-center rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 hover:border-brand-600 hover:text-brand-700"
                >
                  Site da instituição
                  <ExternalLinkIcon />
                </a>
              )}
            </section>
          )}
          <MapEmbed query={mapQuery} title={`Localização de ${university.name}`} />
        </aside>
      </section>
    </Container>
  );
}
