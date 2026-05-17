import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";
import { CourseCard } from "@/components/CourseCard";
import { getAllProvasIngresso, getProvaIngressoBySlug, getCoursesByProvaIngresso } from "@/lib/courses";
import { slugify } from "@/lib/slug";

type PageProps = { params: Promise<{ slug: string }> };

export function generateStaticParams() {
  return getAllProvasIngresso().map((p) => ({ slug: slugify(p.name) }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const prova = getProvaIngressoBySlug(slug);
  if (!prova) return {};
  return {
    title: `Cursos com prova de ingresso: ${prova.name}`,
    description: `Cursos do ensino superior em Portugal que requerem ${prova.name} como prova de ingresso.`,
    alternates: { canonical: `/provas-ingresso/${slug}/` }
  };
}

export default async function ProvaIngressoPage({ params }: PageProps) {
  const { slug } = await params;
  const prova = getProvaIngressoBySlug(slug);
  if (!prova) notFound();

  const courses = getCoursesByProvaIngresso(slug);

  return (
    <Container className="py-10">
      <Breadcrumbs items={[{ label: "Provas de ingresso", href: "/provas-ingresso/" }, { label: prova.name }]} />

      <section>
        <h1 className="text-4xl font-bold tracking-tight text-slate-950">{prova.name}</h1>
        <p className="mt-3 text-slate-700">
          Podes-te candidatar a {courses.length} curso{courses.length === 1 ? "" : "s"} com esta prova de ingresso.
        </p>
      </section>

      <section className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {courses.map((course) => <CourseCard key={course.slug} course={course} />)}
      </section>

      <div className="mt-10">
        <Link href="/provas-ingresso/" className="text-sm font-semibold text-brand-700 hover:text-brand-900">← Ver todas as provas de ingresso</Link>
      </div>
    </Container>
  );
}
