import Link from "next/link";
import { Container } from "./Container";

export function Footer() {
  return (
    <footer className="mt-16 border-t border-slate-200 bg-white">
      <Container className="grid gap-4 py-8 text-sm text-slate-600 sm:grid-cols-2">
        <p>Universidade.pt é um diretório independente. Confirma sempre a informação nas fontes oficiais.</p>
        <nav className="flex flex-wrap gap-4 sm:justify-end">
          <Link href="/contacto/" className="hover:text-brand-700">Contacto</Link>
          <Link href="/privacidade/" className="hover:text-brand-700">Privacidade</Link>
          <Link href="/termos/" className="hover:text-brand-700">Termos</Link>
        </nav>
      </Container>
    </footer>
  );
}
