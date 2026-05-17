import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";
import { CourseCard } from "@/components/CourseCard";
import { getTiposEnsino, getTipoEnsinoBySlug, getCoursesByTipoEnsino } from "@/lib/courses";
import { slugify } from "@/lib/slug";

type PageProps = { params: Promise<{ slug: string }> };

export function generateStaticParams() {
  return getTiposEnsino().map((t) => ({ slug: slugify(t) }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const tipo = getTipoEnsinoBySlug(slug);
  if (!tipo) return {};
  return {
    title: tipo,
    description: `Cursos do ${tipo} em Portugal disponíveis no Universidade.pt.`,
    alternates: { canonical: `/tipos-ensino/${slug}/` }
  };
}

export default async function TipoEnsinoPage({ params }: PageProps) {
  const { slug } = await params;
  const tipo = getTipoEnsinoBySlug(slug);
  if (!tipo) notFound();

  const courses = getCoursesByTipoEnsino(slug);

  return (
    <Container className="py-10">
      <Breadcrumbs items={[{ label: "Tipos de ensino", href: "/tipos-ensino/" }, { label: tipo }]} />

      <section>
        <h1 className="text-4xl font-bold tracking-tight text-slate-950">{tipo}</h1>
        <p className="mt-3 text-slate-700">
          {courses.length} curso{courses.length === 1 ? "" : "s"} {courses.length === 1 ? "disponível" : "disponíveis"} neste tipo de ensino.
        </p>
      </section>

      <section className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {courses.map((course) => <CourseCard key={course.slug} course={course} />)}
      </section>

      <div className="mt-10">
        <Link href="/tipos-ensino/" className="text-sm font-semibold text-brand-700 hover:text-brand-900">← Ver todos os tipos de ensino</Link>
      </div>
    </Container>
  );
}
