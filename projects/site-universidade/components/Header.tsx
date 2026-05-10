import Image from "next/image";
import Link from "next/link";
import { Container } from "./Container";

const nav = [
  { href: "/cursos/", label: "Cursos" },
  { href: "/faculdades/", label: "Faculdades" },
  { href: "/sobre/", label: "Sobre" }
];

export function Header() {
  return (
    <header className="border-b border-slate-200 bg-white/90 backdrop-blur">
      <Container className="flex min-h-16 items-center justify-between gap-6 py-3">
        <Link href="/" className="flex items-center" aria-label="Universidade.pt — página inicial">
          <Image src="/brand/universidade-logo.png" alt="Universidade.pt" width={510} height={83} priority className="h-9 w-auto sm:h-11" />
        </Link>
        <nav className="flex flex-wrap items-center justify-end gap-4 text-sm font-medium text-slate-700">
          {nav.map((item) => (
            <Link key={item.href} href={item.href} className="hover:text-brand-700">
              {item.label}
            </Link>
          ))}
        </nav>
      </Container>
    </header>
  );
}
