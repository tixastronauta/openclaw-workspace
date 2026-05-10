import type { Metadata } from "next";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";

export const metadata: Metadata = {
  title: "Sobre",
  description: "Sobre o Universidade.pt, um diretório independente de cursos do ensino superior em Portugal.",
  alternates: { canonical: "/sobre/" }
};

export default function AboutPage() {
  return (
    <Container className="py-10">
      <Breadcrumbs items={[{ label: "Sobre" }]} />
      <div className="max-w-3xl rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-4xl font-bold text-slate-950">Sobre</h1>
        <p className="mt-4 leading-7 text-slate-700">Universidade.pt é um diretório independente para ajudar a encontrar cursos do ensino superior em Portugal.</p>
        <p className="mt-4 leading-7 text-slate-700">O objetivo é facilitar a comparação de cursos, instituições e notas de entrada, reunindo a informação essencial de forma simples e fácil de consultar.</p>
        <p className="mt-4 leading-7 text-slate-700">A informação apresentada deve ser sempre confirmada nas fontes oficiais antes de qualquer decisão de candidatura.</p>
      </div>
    </Container>
  );
}
