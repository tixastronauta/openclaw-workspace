import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";
import { CourseCard } from "@/components/CourseCard";
import { DistrictMiniMap } from "@/components/DistrictMiniMap";
import { getAllDistricts, getCoursesByDistrict, getDistrictBySlug, getFacultySlugByInstitution } from "@/lib/courses";

const PREPOSITIONS: Record<string, string> = {
  Porto: "do",
  Guarda: "da",
};

const TITLE_OVERRIDES: Record<string, string> = {
  Açores: "Região Autónoma dos Açores",
  Madeira: "Região Autónoma da Madeira",
};

function districtTitle(name: string): string {
  if (TITLE_OVERRIDES[name]) return TITLE_OVERRIDES[name];
  const prep = PREPOSITIONS[name] ?? "de";
  return `Distrito ${prep} ${name}`;
}

type PageProps = { params: Promise<{ slug: string }> };

export function generateStaticParams() {
  return getAllDistricts().map((district) => ({ slug: district.slug }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const district = getDistrictBySlug(slug);
  if (!district) return {};
  return {
    title: `Cursos no ${districtTitle(district.name)}`,
    description: `${district.courseCount} cursos em ${district.faculties.length} instituições no ${districtTitle(district.name)}.`,
    alternates: { canonical: `/distritos/${district.slug}/` }
  };
}

export default async function DistritoPage({ params }: PageProps) {
  const { slug } = await params;
  const district = getDistrictBySlug(slug);
  if (!district) notFound();

  const courses = getCoursesByDistrict(slug);
  const byInstitution = new Map<string, typeof courses>();

  for (const course of courses) {
    const key = course.institutionName ?? "Sem instituição";
    byInstitution.set(key, [...(byInstitution.get(key) ?? []), course]);
  }

  const institutions = Array.from(byInstitution.entries()).sort(([a], [b]) => a.localeCompare(b, "pt"));

  return (
    <Container className="relative overflow-hidden py-10">
      <div className="pointer-events-none fixed right-32 top-[60px] z-0 hidden opacity-40 lg:block">
        <DistrictMiniMap districtName={district.name} className="h-[700px]" />
      </div>
      <div className="relative z-10">
      <Breadcrumbs items={[{ label: "Distritos", href: "/distritos/" }, { label: district.name }]} />

      <section className="relative mt-4 h-52 overflow-hidden rounded-2xl sm:h-72">
        <Image
          src={`/distrito/${district.slug}.jpg`}
          alt={`Paisagem do ${districtTitle(district.name)}`}
          fill
          className="object-cover"
          priority
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/65 via-black/20 to-transparent" />
        <div className="absolute bottom-0 left-0 p-6">
          <h1 className="text-3xl font-bold tracking-tight text-white drop-shadow sm:text-4xl">
            {districtTitle(district.name)}
          </h1>
          <div className="mt-2 flex flex-wrap gap-2 text-sm text-white/90">
            <span className="rounded-full bg-white/20 px-3 py-1 font-medium backdrop-blur-sm">
              {district.faculties.length} institui{district.faculties.length === 1 ? "ção" : "ções"}
            </span>
            <span className="rounded-full bg-white/20 px-3 py-1 font-medium backdrop-blur-sm">
              {district.courseCount} curso{district.courseCount === 1 ? "" : "s"}
            </span>
          </div>
        </div>
      </section>

      <section className="mt-10 grid gap-12">
        {institutions.map(([institutionName, institutionCourses]) => {
          const first = institutionCourses[0];
          const facultySlug = getFacultySlugByInstitution(first?.institutionName, first?.institutionCode);
          const institutionLabel = [institutionName, first?.institutionSigla ? `(${first.institutionSigla})` : undefined].filter(Boolean).join(" ");

          return (
            <div key={institutionName}>
              <h2 className="sticky top-16 z-20 -mx-2 mb-2 px-2 py-2 text-2xl font-semibold text-slate-950">
                {facultySlug ? (
                  <Link href={`/faculdades/${facultySlug}/`} className="hover:text-brand-700">{institutionLabel}</Link>
                ) : institutionLabel}
              </h2>
              {(first?.cidade || first?.morada) && (
                <p className="mb-4 text-sm text-slate-500">
                  {[first.cidade, first.morada].filter(Boolean).join(" · ")}
                </p>
              )}
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {institutionCourses.map((course) => <CourseCard key={course.slug} course={course} />)}
              </div>
            </div>
          );
        })}
      </section>
      </div>
    </Container>
  );
}
