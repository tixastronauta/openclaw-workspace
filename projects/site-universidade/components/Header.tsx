import Image from "next/image";
import Link from "next/link";
import { Container } from "./Container";
import { GlobalSearch } from "./GlobalSearch";
import { MobileNav } from "./MobileNav";

const nav = [
  { href: "/cursos/", label: "Cursos" },
  { href: "/faculdades/", label: "Faculdades" },
  { href: "/ciclos/", label: "Ciclos" },
  { href: "/top-10/", label: "Top 10" },
];

export function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/90 backdrop-blur">
      <Container className="py-3">
        {/* Row: logo · search (sm+, center) · desktop nav (sm+) · burger (mobile) */}
        <div className="flex items-center gap-3">
          <Link href="/" className="flex shrink-0 items-center" aria-label="Universidade.pt — página inicial">
            <Image src="/brand/universidade-logo.png" alt="Universidade.pt" width={510} height={83} priority className="h-8 w-auto sm:h-10" />
          </Link>

          <div className="hidden flex-1 justify-center sm:flex">
            <GlobalSearch />
          </div>

          <nav className="ml-auto hidden shrink-0 items-center gap-4 text-sm font-medium text-slate-700 sm:flex">
            {nav.map((item) => (
              <Link key={item.href} href={item.href} className="hover:text-brand-700">
                {item.label}
              </Link>
            ))}
          </nav>

          {/* Burger — mobile only, rendered inside MobileNav */}
          <MobileNav />
        </div>

        {/* Search — mobile only, second row */}
        <div className="mt-2.5 sm:hidden">
          <GlobalSearch />
        </div>
      </Container>
    </header>
  );
}
