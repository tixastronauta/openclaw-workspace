import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";
import { CourseCard } from "@/components/CourseCard";
import { getDuracoes, getDuracaoBySlug, getCoursesByDuracao } from "@/lib/courses";
import { slugify } from "@/lib/slug";

type PageProps = { params: Promise<{ slug: string }> };

export function generateStaticParams() {
  return getDuracoes().map((d) => ({ slug: slugify(d) }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const duracao = getDuracaoBySlug(slug);
  if (!duracao) return {};
  return {
    title: `Cursos com duração de ${duracao}`,
    description: `Cursos do ensino superior em Portugal com duração de ${duracao}.`,
    alternates: { canonical: `/duracoes/${slug}/` }
  };
}

export default async function DuracaoPage({ params }: PageProps) {
  const { slug } = await params;
  const duracao = getDuracaoBySlug(slug);
  if (!duracao) notFound();

  const courses = getCoursesByDuracao(slug);

  return (
    <Container className="py-10">
      <Breadcrumbs items={[{ label: "Duração", href: "/duracoes/" }, { label: duracao }]} />

      <section>
        <h1 className="text-4xl font-bold tracking-tight text-slate-950">{duracao}</h1>
        <p className="mt-3 text-slate-700">
          {courses.length} curso{courses.length === 1 ? "" : "s"} {courses.length === 1 ? "disponível" : "disponíveis"} com esta duração.
        </p>
      </section>

      <section className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {courses.map((course) => <CourseCard key={course.slug} course={course} />)}
      </section>

      <div className="mt-10">
        <Link href="/duracoes/" className="text-sm font-semibold text-brand-700 hover:text-brand-900">← Ver todas as durações</Link>
      </div>
    </Container>
  );
}
