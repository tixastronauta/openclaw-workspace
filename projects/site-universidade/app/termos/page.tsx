import type { Metadata } from "next";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";

export const metadata: Metadata = {
  title: "Termos e condições",
  description: "Termos e condições de utilização do Universidade.pt.",
  alternates: { canonical: "/termos/" }
};

export default function TermsPage() {
  return (
    <Container className="py-10">
      <Breadcrumbs items={[{ label: "Termos" }]} />
      <article className="max-w-3xl rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-4xl font-bold text-slate-950">Termos e condições</h1>
        <p className="mt-4 leading-7 text-slate-700">
          Ao utilizar o Universidade.pt, aceitas estes termos de utilização. Se não concordares, não deves usar o site.
        </p>

        <h2 className="mt-8 text-2xl font-semibold text-slate-950">Natureza do serviço</h2>
        <p className="mt-3 leading-7 text-slate-700">
          O Universidade.pt é um diretório independente de cursos do ensino superior em Portugal. O site organiza informação para consulta, mas não é uma entidade oficial, não representa a DGES, InfoCursos ou qualquer instituição de ensino, e não substitui informação oficial.
        </p>

        <h2 className="mt-8 text-2xl font-semibold text-slate-950">Exatidão da informação</h2>
        <p className="mt-3 leading-7 text-slate-700">
          Procuramos apresentar informação útil e atualizada, mas podem existir erros, omissões ou desatualizações. Antes de tomar decisões sobre candidaturas, cursos, vagas, notas ou instituições, deves confirmar sempre a informação nas fontes oficiais.
        </p>

        <h2 className="mt-8 text-2xl font-semibold text-slate-950">Utilização permitida</h2>
        <p className="mt-3 leading-7 text-slate-700">
          Podes usar o site para pesquisa pessoal e consulta informativa. Não é permitido tentar comprometer o funcionamento do site, automatizar acessos abusivos ou reutilizar conteúdos de forma que possa induzir terceiros em erro.
        </p>

        <h2 className="mt-8 text-2xl font-semibold text-slate-950">Responsabilidade</h2>
        <p className="mt-3 leading-7 text-slate-700">
          O Universidade.pt é disponibilizado “tal como está”. Não garantimos disponibilidade contínua, ausência de erros ou adequação da informação a qualquer decisão específica. A utilização da informação é da responsabilidade do utilizador.
        </p>

        <h2 className="mt-8 text-2xl font-semibold text-slate-950">Contacto</h2>
        <p className="mt-3 leading-7 text-slate-700">
          Para correções, dúvidas ou pedidos relacionados com estes termos, contacta <a className="font-semibold text-brand-700 hover:text-brand-900" href="mailto:info@universidade.pt">info@universidade.pt</a>.
        </p>
      </article>
    </Container>
  );
}
