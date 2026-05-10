import Link from "next/link";
import { ADS_ENABLED, AdSlot } from "@/components/AdSlot";
import { Container } from "@/components/Container";
import { SearchBox } from "@/components/SearchBox";
import { getAllCourses, getCourseInitials, getCycles } from "@/lib/courses";

export default function HomePage() {
  const courses = getAllCourses();
  const initials = getCourseInitials();
  const cycles = getCycles();

  return (
    <Container className="py-12 sm:py-16">
      <section className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr] lg:items-center">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-brand-700">Diretório independente</p>
          <h1 className="mt-3 max-w-3xl text-4xl font-bold tracking-tight text-slate-950 sm:text-5xl">
            Cursos do ensino superior em Portugal, reunidos num só sítio.
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-700">
            Pesquisa cursos, consulta notas de entrada disponíveis e segue rapidamente para as fontes oficiais DGES e InfoCursos. A informação deve ser sempre confirmada nos organismos oficiais.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/cursos/" className="rounded-xl bg-brand-700 px-5 py-3 text-sm font-semibold text-white shadow-sm hover:bg-brand-900">
              Ver todos os cursos
            </Link>
          </div>
        </div>
        <SearchBox courses={courses} />
      </section>

      {ADS_ENABLED && (
        <section className="mt-12">
          <AdSlot label="Homepage — topo" />
        </section>
      )}

      <section className="mt-12 grid gap-8 lg:grid-cols-[0.8fr_1.2fr]">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-950">Explorar por inicial</h2>
          <p className="mt-2 text-sm text-slate-600">Agrupamento simples gerado a partir dos nomes dos cursos disponíveis.</p>
          <div className="mt-5 flex flex-wrap gap-2">
            {initials.map((initial) => (
              <Link key={initial} href={`/cursos/#${initial}`} className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 hover:border-brand-600 hover:text-brand-700">
                {initial}
              </Link>
            ))}
          </div>
          {cycles.length > 0 && (
            <div className="mt-6 border-t border-slate-100 pt-5">
              <h3 className="text-sm font-semibold text-slate-950">Ciclos disponíveis</h3>
              <div className="mt-3 flex flex-wrap gap-2">
                {cycles.map((cycle) => (
                  <span key={cycle} className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">{cycle}</span>
                ))}
              </div>
            </div>
          )}
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-950">O que encontras aqui</h2>
          <ul className="mt-4 grid gap-3 text-sm leading-6 text-slate-700 sm:grid-cols-2">
            <li>• Pesquisa por curso e instituição.</li>
            <li>• Notas de entrada dos anos disponíveis.</li>
            <li>• Ligações identificadas para DGES e InfoCursos.</li>
            <li>• Lista de faculdades com os respetivos cursos.</li>
          </ul>
        </div>
      </section>
    </Container>
  );
}
