import Link from "next/link";
import { ADS_ENABLED, AdSlot } from "@/components/AdSlot";
import { Container } from "@/components/Container";
import { PortugalDistrictMap } from "@/components/PortugalDistrictMap";
import { getAllDistricts, getCourseInitials, getCycles } from "@/lib/courses";
import { slugify } from "@/lib/slug";

export default function HomePage() {
  const initials = getCourseInitials();
  const cycles = getCycles();
  const districts = getAllDistricts().map((district) => ({
    slug: district.slug,
    name: district.name,
    facultyCount: district.faculties.length,
    courseCount: district.courseCount
  }));

  return (
    <Container className="py-12 sm:py-16">
      <section className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(420px,560px)] lg:items-center">
        <div className="max-w-3xl">
          <p className="text-sm font-semibold uppercase tracking-wide text-brand-700">Diretório independente</p>
          <h1 className="mt-3 text-4xl font-bold tracking-tight text-slate-950 sm:text-5xl">
            Cursos do ensino superior em Portugal, reunidos num só sítio.
          </h1>
          <p className="mt-5 text-lg leading-8 text-slate-700">
            Pesquisa cursos, compara instituições e encontra rapidamente informação organizada sobre o ensino superior em Portugal — tudo num diretório simples, pesquisável e feito para te poupar tempo.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/cursos/" className="rounded-xl bg-brand-700 px-5 py-3 text-sm font-semibold text-white shadow-sm hover:bg-brand-900">
              Ver todos os cursos
            </Link>
            <Link href="/faculdades/" className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 hover:border-brand-600 hover:text-brand-700">
              Ver faculdades
            </Link>
            <Link href="/distritos/" className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 hover:border-brand-600 hover:text-brand-700">
              Ver distritos
            </Link>
          </div>
        </div>
        <PortugalDistrictMap districts={districts} />
      </section>

      {ADS_ENABLED && (
        <section className="mt-12">
          <AdSlot label="Homepage — topo" />
        </section>
      )}

      <section className="mt-12 grid gap-8 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-950">Explorar por inicial</h2>
          <div className="mt-5 flex flex-wrap gap-2">
            {initials.map((initial) => (
              <Link key={initial} href={`/cursos/#${initial}`} className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 hover:border-brand-600 hover:text-brand-700">
                {initial}
              </Link>
            ))}
          </div>
        </div>
        {cycles.length > 0 && (
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-slate-950">Explorar por ciclos</h2>
            <div className="mt-5 flex flex-wrap gap-2">
              {cycles.map((cycle) => (
                <Link key={cycle} href={`/ciclos/${slugify(cycle)}/`} className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 hover:border-brand-600 hover:text-brand-700">
                  {cycle}
                </Link>
              ))}
            </div>
          </div>
        )}
      </section>

      <section className="mt-8">
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
