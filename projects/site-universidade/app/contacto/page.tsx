import type { Metadata } from "next";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { Container } from "@/components/Container";

export const metadata: Metadata = {
  title: "Contacto",
  description: "Informação de contacto do Universidade.pt.",
  alternates: { canonical: "/contacto/" }
};

export default function ContactPage() {
  return (
    <Container className="py-10">
      <Breadcrumbs items={[{ label: "Contacto" }]} />
      <div className="max-w-3xl rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-4xl font-bold text-slate-950">Contacto</h1>
        <p className="mt-4 leading-7 text-slate-700">Para contacto editorial, correções ou pedidos relacionados com informação publicada, usa <a className="font-semibold text-brand-700 hover:text-brand-900" href="mailto:info@universidade.pt">info@universidade.pt</a>.</p>
      </div>
    </Container>
  );
}
