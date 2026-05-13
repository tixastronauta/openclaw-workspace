import type { Metadata } from "next";
import { ADS_ENABLED, AdSlot } from "@/components/AdSlot";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";
import { CourseCard } from "@/components/CourseCard";
import { getAllCourses } from "@/lib/courses";

export const metadata: Metadata = {
  title: "Lista de cursos",
  description: "Lista pesquisável de cursos do ensino superior em Portugal, com páginas individuais e ligações para fontes oficiais.",
  alternates: { canonical: "/cursos/" }
};

export default function CoursesPage() {
  const courses = getAllCourses();
  const grouped = courses.reduce<Record<string, typeof courses>>((acc, course) => {
    const initial = course.courseName[0]?.toLocaleUpperCase("pt") ?? "#";
    acc[initial] = [...(acc[initial] ?? []), course];
    return acc;
  }, {});

  return (
    <Container className="py-10">
      <Breadcrumbs items={[{ label: "Cursos" }]} />
      <section>
        <h1 className="text-4xl font-bold tracking-tight text-slate-950">Cursos</h1>
        <p className="mt-4 text-slate-700">
          Pesquisa cursos do ensino superior em Portugal, consulta notas de entrada disponíveis e acede rapidamente às fontes oficiais.
        </p>
      </section>

      {ADS_ENABLED && (
        <div className="mt-10">
          <AdSlot label="Índice de cursos — entre pesquisa e listagem" />
        </div>
      )}

      <section className="mt-10 grid gap-10">
        {Object.entries(grouped).map(([initial, items]) => (
          <div key={initial} id={initial}>
            <h2 className="sticky top-[6.5rem] z-20 -mx-2 mb-4 border-b border-slate-200 bg-slate-50/95 px-2 py-2 text-2xl font-semibold text-slate-950 backdrop-blur sm:top-16">{initial}</h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {items.map((course) => <CourseCard key={course.slug} course={course} />)}
            </div>
          </div>
        ))}
      </section>
    </Container>
  );
}
