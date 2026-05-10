import type { Metadata } from "next";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";

export const metadata: Metadata = {
  title: "Fontes oficiais",
  description: "Porque deves confirmar informação sobre cursos e candidaturas nas fontes oficiais DGES e InfoCursos.",
  alternates: { canonical: "/fontes-oficiais/" }
};

export default function OfficialSourcesPage() {
  return (
    <Container className="py-10">
      <Breadcrumbs items={[{ label: "Fontes oficiais" }]} />
      <div className="max-w-3xl rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-4xl font-bold text-slate-950">Confirma sempre nas fontes oficiais</h1>
        <p className="mt-4 leading-7 text-slate-700">Este site é um diretório independente. A informação sobre cursos, vagas, candidaturas, regras, médias e notas deve ser confirmada nas fontes oficiais antes de qualquer decisão.</p>
        <ul className="mt-6 grid gap-3 text-slate-700">
          <li>• DGES: informação oficial sobre acesso ao ensino superior.</li>
          <li>• InfoCursos: dados oficiais de cursos e instituições.</li>
          <li>• Instituições de ensino: páginas oficiais de cada universidade ou politécnico.</li>
        </ul>
      </div>
    </Container>
  );
}
