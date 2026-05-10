import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ADS_ENABLED, AdSlot } from "@/components/AdSlot";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";
import { CourseCard } from "@/components/CourseCard";
import { getAllFaculties, getFacultyBySlug } from "@/lib/courses";

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
    description: `Cursos disponíveis em ${faculty.institutionName}, com links para páginas de curso e fontes oficiais quando disponíveis.`,
    alternates: { canonical: `/faculdades/${faculty.slug}/` }
  };
}

export default async function FacultyPage({ params }: PageProps) {
  const { slug } = await params;
  const faculty = getFacultyBySlug(slug);
  if (!faculty) notFound();

  return (
    <Container className="py-10">
      <Breadcrumbs items={[{ label: "Faculdades", href: "/faculdades/" }, { label: faculty.institutionName }]} />
      <section>
        <h1 className="text-4xl font-bold tracking-tight text-slate-950">{faculty.institutionName}</h1>
        <div className="mt-3 flex flex-wrap gap-2 text-xs font-medium uppercase tracking-wide text-slate-500">
          {faculty.institutionCode && <span className="rounded-full bg-slate-100 px-3 py-1">Código {faculty.institutionCode}</span>}
          <span className="rounded-full bg-slate-100 px-3 py-1">{faculty.courses.length} curso{faculty.courses.length === 1 ? "" : "s"}</span>
        </div>
        <p className="mt-4 max-w-3xl text-slate-700">
          Cursos desta instituição disponíveis no Universidade.pt. Confirma sempre detalhes atualizados nas páginas oficiais indicadas em cada curso.
        </p>
      </section>

      {ADS_ENABLED && (
        <div className="mt-10">
          <AdSlot label="Faculdade — antes da lista de cursos" />
        </div>
      )}

      <section className="mt-10">
        <div className="mb-5 flex items-center justify-between gap-4">
          <h2 className="text-2xl font-semibold text-slate-950">Cursos</h2>
          <Link href="/faculdades/" className="text-sm font-semibold text-brand-700 hover:text-brand-900">Ver todas as faculdades</Link>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {faculty.courses.map((course) => <CourseCard key={course.slug} course={course} />)}
        </div>
      </section>
    </Container>
  );
}
