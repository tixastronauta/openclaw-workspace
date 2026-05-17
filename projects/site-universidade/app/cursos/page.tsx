import type { Metadata } from "next";
import { ADS_ENABLED, AdSlot } from "@/components/AdSlot";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";
import { CoursesAlphabetBrowser } from "@/components/CoursesAlphabetBrowser";
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

      <CoursesAlphabetBrowser grouped={grouped} />
    </Container>
  );
}
