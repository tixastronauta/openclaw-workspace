import type { Metadata } from "next";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";

export const metadata: Metadata = {
  title: "Política de privacidade",
  description: "Política de privacidade do Universidade.pt.",
  alternates: { canonical: "/privacidade/" }
};

export default function PrivacyPage() {
  return (
    <Container className="py-10">
      <Breadcrumbs items={[{ label: "Privacidade" }]} />
      <article className="max-w-3xl rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-4xl font-bold text-slate-950">Política de privacidade</h1>
        <p className="mt-4 leading-7 text-slate-700">
          Esta política explica, de forma simples, como o Universidade.pt trata informação dos visitantes.
        </p>

        <h2 className="mt-8 text-2xl font-semibold text-slate-950">Dados pessoais</h2>
        <p className="mt-3 leading-7 text-slate-700">
          O Universidade.pt pode ser utilizado sem criar conta e sem fornecer dados pessoais diretamente. Se nos contactares por email, poderemos usar o teu endereço e o conteúdo da mensagem apenas para responder ao pedido.
        </p>

        <h2 className="mt-8 text-2xl font-semibold text-slate-950">Dados técnicos</h2>
        <p className="mt-3 leading-7 text-slate-700">
          Como acontece na maioria dos sites, podem ser tratados dados técnicos básicos de acesso, como endereço IP, tipo de navegador, páginas visitadas e data/hora do acesso, para segurança, prevenção de abuso e funcionamento do serviço.
        </p>

        <h2 className="mt-8 text-2xl font-semibold text-slate-950">Cookies e serviços externos</h2>
        <p className="mt-3 leading-7 text-slate-700">
          Poderemos usar cookies ou serviços externos para funcionalidades essenciais, estatísticas agregadas ou publicidade. Quando aplicável, esses serviços podem tratar dados de acordo com as suas próprias políticas de privacidade.
        </p>

        <h2 className="mt-8 text-2xl font-semibold text-slate-950">Informação sobre cursos</h2>
        <p className="mt-3 leading-7 text-slate-700">
          O Universidade.pt apresenta informação sobre cursos e instituições para fins informativos. Sempre que existam links para DGES, InfoCursos ou outras entidades oficiais, deves usar essas fontes para confirmar a informação atualizada.
        </p>

        <h2 className="mt-8 text-2xl font-semibold text-slate-950">Contacto</h2>
        <p className="mt-3 leading-7 text-slate-700">
          Para pedidos relacionados com privacidade, correções ou remoção de informação, contacta-nos através de <a className="font-semibold text-brand-700 hover:text-brand-900" href="mailto:info@universidade.pt">info@universidade.pt</a>.
        </p>
      </article>
    </Container>
  );
}
