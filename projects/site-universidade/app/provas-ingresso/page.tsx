import type { Metadata } from "next";
import Link from "next/link";
import { NotebookPen } from "lucide-react";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";
import { getAllProvasIngresso, getCoursesByProvaIngresso } from "@/lib/courses";
import { slugify } from "@/lib/slug";

export const metadata: Metadata = {
  title: "Provas de ingresso",
  description: "Explora todas as provas de ingresso do ensino superior em Portugal e os cursos que as requerem.",
  alternates: { canonical: "/provas-ingresso/" }
};

export default function ProvasIngressoPage() {
  const provas = getAllProvasIngresso();

  return (
    <Container className="py-10">
      <Breadcrumbs items={[{ label: "Provas de ingresso" }]} />
      <section>
        <h1 className="text-4xl font-bold tracking-tight text-slate-950">Provas de ingresso</h1>
        <p className="mt-4 text-slate-700">
          Todas as provas de ingresso do ensino superior em Portugal, com o número de cursos que as requerem.
        </p>
      </section>

      <section className="mt-10 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {provas.map((prova) => {
          const slug = slugify(prova.name);
          const count = getCoursesByProvaIngresso(slug).length;
          return (
            <Link
              key={prova.code}
              href={`/provas-ingresso/${slug}/`}
              className="group flex h-full items-center gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
            >
              <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-700 group-hover:bg-brand-100">
                <NotebookPen className="size-5" />
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-slate-950 group-hover:text-brand-700">{prova.name}</p>
                <p className="mt-0.5 text-xs text-slate-500">{count} curso{count === 1 ? "" : "s"}</p>
              </div>
            </Link>
          );
        })}
      </section>
    </Container>
  );
}
