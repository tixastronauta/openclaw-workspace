import type { Metadata } from "next";
import Link from "next/link";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";
import { getAreas, getCoursesByArea } from "@/lib/courses";
import { AREA_ICONS } from "@/lib/areaIcons";
import { slugify } from "@/lib/slug";

export const metadata: Metadata = {
  title: "Áreas de formação (CNAEF)",
  description: "Explora cursos do ensino superior em Portugal por área de formação segundo a Classificação Nacional de Áreas de Educação e Formação (CNAEF).",
  alternates: { canonical: "/areas/" }
};

function parseCnaef(area: string): { code: string; name: string } {
  const match = area.match(/^(\d+)\s+(.+)$/);
  if (match) return { code: match[1], name: match[2] };
  return { code: "", name: area };
}

export default function AreasPage() {
  const areas = getAreas();

  return (
    <Container className="py-10">
      <Breadcrumbs items={[{ label: "Áreas de formação" }]} />
      <section>
        <h1 className="text-4xl font-bold tracking-tight text-slate-950">Áreas de formação</h1>
        <p className="mt-4 text-slate-700">
          Explora cursos do ensino superior em Portugal por área de formação (CNAEF).
        </p>
      </section>

      <div className="mt-10 grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
        {areas
          .map((area) => ({ area, count: getCoursesByArea(slugify(area)).length }))
          .sort((a, b) => b.count - a.count)
          .map(({ area, count }) => {
          const { code, name } = parseCnaef(area);
          const Icon = AREA_ICONS[code];
          return (
            <Link
              key={area}
              href={`/areas/${slugify(area)}/`}
              className="group flex flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
            >
              {Icon && (
                <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-brand-600 transition group-hover:bg-brand-100">
                  <Icon className="h-5 w-5" />
                </div>
              )}
              <h2 className="text-base font-semibold leading-snug text-slate-950 group-hover:text-brand-700">{name}</h2>
              <p className="mt-2 text-sm text-slate-500">{count} curso{count === 1 ? "" : "s"}</p>
            </Link>
          );
        })}
      </div>
    </Container>
  );
}
