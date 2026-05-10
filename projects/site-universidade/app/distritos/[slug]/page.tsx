import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";
import { CourseCard } from "@/components/CourseCard";
import { getAllDistricts, getCoursesByDistrict, getDistrictBySlug, getFacultySlugByInstitution } from "@/lib/courses";

type PageProps = { params: Promise<{ slug: string }> };

export function generateStaticParams() {
  return getAllDistricts().map((district) => ({ slug: district.slug }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const district = getDistrictBySlug(slug);
  if (!district) return {};
  return {
    title: `Cursos no distrito de ${district.name}`,
    description: `${district.courseCount} cursos em ${district.faculties.length} instituições no distrito de ${district.name}.`,
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
    <Container className="py-10">
      <Breadcrumbs items={[{ label: "Distritos", href: "/distritos/" }, { label: district.name }]} />

      <section>
        <h1 className="text-4xl font-bold tracking-tight text-slate-950">Distrito de {district.name}</h1>
        <div className="mt-3 flex flex-wrap gap-3 text-sm text-slate-600">
          <span className="rounded-full bg-slate-100 px-3 py-1 font-medium">{district.faculties.length} institui{district.faculties.length === 1 ? "ção" : "ções"}</span>
          <span className="rounded-full bg-slate-100 px-3 py-1 font-medium">{district.courseCount} curso{district.courseCount === 1 ? "" : "s"}</span>
        </div>
      </section>

      <section className="mt-10 grid gap-12">
        {institutions.map(([institutionName, institutionCourses]) => {
          const first = institutionCourses[0];
          const facultySlug = getFacultySlugByInstitution(first?.institutionName, first?.institutionCode);

          return (
            <div key={institutionName}>
              <h2 className="mb-2 border-b border-slate-200 pb-2 text-2xl font-semibold text-slate-950">
                {facultySlug ? (
                  <Link href={`/faculdades/${facultySlug}/`} className="hover:text-brand-700">{institutionName}</Link>
                ) : institutionName}
                {first?.institutionSigla && <span className="ml-3 align-middle rounded-full bg-slate-100 px-3 py-1 text-xs font-medium uppercase tracking-wide text-slate-500">{first.institutionSigla}</span>}
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
    </Container>
  );
}
