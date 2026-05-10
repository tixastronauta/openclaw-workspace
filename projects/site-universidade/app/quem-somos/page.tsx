import type { Metadata } from "next";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";

export const metadata: Metadata = {
  title: "Quem somos",
  description: "Quem somos e contacto do Universidade.pt, um diretório independente de cursos do ensino superior em Portugal.",
  alternates: { canonical: "/quem-somos/" }
};

export default function QuemSomosPage() {
  return (
    <Container className="py-10">
      <Breadcrumbs items={[{ label: "Quem somos" }]} />
      <div className="max-w-3xl rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-4xl font-bold text-slate-950">Quem somos</h1>
        <p className="mt-4 leading-7 text-slate-700">
          Universidade.pt é um diretório independente para ajudar a encontrar cursos do ensino superior em Portugal.
        </p>
        <p className="mt-4 leading-7 text-slate-700">
          O objetivo é facilitar a comparação de cursos, instituições e notas de entrada, reunindo a informação essencial de forma simples e fácil de consultar.
        </p>
        <p className="mt-4 leading-7 text-slate-700">
          A informação apresentada deve ser sempre confirmada nas fontes oficiais antes de qualquer decisão de candidatura.
        </p>
        <p className="mt-4 leading-7 text-slate-700">
          Para contacto editorial, correções ou pedidos relacionados com informação publicada, usa{" "}
          <a className="font-semibold text-brand-700 hover:text-brand-900" href="mailto:info@universidade.pt">
            info@universidade.pt
          </a>.
        </p>
      </div>
    </Container>
  );
}
