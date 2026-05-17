import Link from "next/link";
import { Container } from "@/components/Container";

export default function NotFound() {
  return (
    <Container className="py-24 text-center">
      <p className="text-8xl font-black tracking-tight text-slate-200">404</p>
      <h1 className="mt-4 text-2xl font-bold text-slate-950">Página não encontrada</h1>
      <p className="mt-3 text-slate-500">
        O endereço que introduziste não existe ou foi removido.
      </p>
      <Link
        href="/"
        className="mt-8 inline-flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700"
      >
        Ir para a página inicial
      </Link>
    </Container>
  );
}
