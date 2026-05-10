import type { Metadata } from "next";
import Link from "next/link";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";
import { CourseCard } from "@/components/CourseCard";
import { getCoursesByCycle, getCycles } from "@/lib/courses";
import { slugify } from "@/lib/slug";

type PageProps = {
  params: Promise<{ slug: string }>;
};

export function generateStaticParams() {
  return getCycles().map((cycle) => ({ slug: slugify(cycle) }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const cycle = getCycles().find((c) => slugify(c) === slug);
  if (!cycle) return {};
  return {
    title: cycle,
    description: `Cursos de ${cycle} do ensino superior em Portugal disponíveis no Universidade.pt.`,
    alternates: { canonical: `/ciclos/${slug}/` }
  };
}

export default async function CyclePage({ params }: PageProps) {
  const { slug } = await params;
  const cycle = getCycles().find((c) => slugify(c) === slug);
  if (!cycle) return <Container className="py-10"><p>Ciclo não encontrado.</p></Container>;

  const courses = getCoursesByCycle(cycle);

  return (
    <Container className="py-10">
      <Breadcrumbs items={[{ label: "Ciclos", href: "/ciclos/" }, { label: cycle }]} />
      <section>
        <h1 className="text-4xl font-bold tracking-tight text-slate-950">{cycle}</h1>
        <p className="mt-4 max-w-3xl text-slate-700">
          {courses.length} curso{courses.length === 1 ? "" : "s"} {courses.length === 1 ? "disponível" : "disponíveis"} neste ciclo.
        </p>
      </section>

      <section className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {courses.map((course) => <CourseCard key={course.slug} course={course} />)}
      </section>

      <div className="mt-10">
        <Link href="/ciclos/" className="text-sm font-semibold text-brand-700 hover:text-brand-900">← Ver todos os ciclos</Link>
      </div>
    </Container>
  );
}
