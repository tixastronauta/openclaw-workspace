import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { NotebookPen } from "lucide-react";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";
import { CourseCard } from "@/components/CourseCard";
import { getAllProvaSets, getProvaSetBySlug, getCoursesByProvaSet } from "@/lib/courses";

type PageProps = { params: Promise<{ slug: string }> };

export function generateStaticParams() {
  return getAllProvaSets().map((s) => ({ slug: s.slug }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const entry = getProvaSetBySlug(slug);
  if (!entry) return {};
  const label = entry.provas.map((p) => p.name).join(" + ");
  return {
    title: `Cursos com provas: ${label}`,
    description: `Cursos do ensino superior em Portugal que aceitam o conjunto de provas de ingresso: ${label}.`,
    alternates: { canonical: `/provas-ingresso/conjunto/${slug}/` }
  };
}

export default async function ProvaSetPage({ params }: PageProps) {
  const { slug } = await params;
  const entry = getProvaSetBySlug(slug);
  if (!entry) notFound();

  const courses = getCoursesByProvaSet(slug);
  const label = entry.provas.map((p) => p.name).join(" + ");

  return (
    <Container className="py-10">
      <Breadcrumbs items={[
        { label: "Provas de ingresso", href: "/provas-ingresso/" },
        { label: label }
      ]} />

      <section>
        <h1 className="text-4xl font-bold tracking-tight text-slate-950">Conjunto de provas de ingresso</h1>
        <div className="mt-4 inline-flex flex-col gap-1.5 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
          {entry.provas.map((prova, i) => (
            <div key={prova.code} className="flex items-center gap-2 text-sm">
              {i > 0
                ? <span className="inline-flex size-4 shrink-0 items-center justify-center text-[10px] font-black text-slate-400">+</span>
                : <NotebookPen className="size-4 shrink-0 text-slate-400" aria-hidden="true" />
              }
              <span className="font-medium text-slate-800">{prova.name}</span>
            </div>
          ))}
        </div>
        <p className="mt-6 text-slate-700">
          Podes-te candidatar a {courses.length} curso{courses.length === 1 ? "" : "s"} com este conjunto de provas de ingresso.
        </p>
      </section>

      <section className="mt-10 grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
        {courses.map((course) => <CourseCard key={course.slug} course={course} />)}
      </section>

      <div className="mt-10">
        <Link href="/provas-ingresso/" className="text-sm font-semibold text-brand-700 hover:text-brand-900">
          ← Ver todas as provas de ingresso
        </Link>
      </div>
    </Container>
  );
}
