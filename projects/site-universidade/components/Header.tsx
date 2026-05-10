import Image from "next/image";
import Link from "next/link";
import { getAllCourses } from "@/lib/courses";
import { Container } from "./Container";
import { GlobalSearch } from "./GlobalSearch";

const nav = [
  { href: "/cursos/", label: "Cursos" },
  { href: "/faculdades/", label: "Faculdades" },
  { href: "/ciclos/", label: "Ciclos" },
  { href: "/top-10/", label: "Top 10" }
];

export function Header() {
  const courses = getAllCourses();

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/90 backdrop-blur">
      <Container className="flex min-h-16 items-center gap-4 py-3">
        <Link href="/" className="flex shrink-0 items-center" aria-label="Universidade.pt — página inicial">
          <Image src="/brand/universidade-logo.png" alt="Universidade.pt" width={510} height={83} priority className="h-9 w-auto sm:h-11" />
        </Link>

        {/* Search — grows to fill middle space */}
        <div className="flex flex-1 justify-center">
          <GlobalSearch courses={courses} />
        </div>

        <nav className="flex shrink-0 flex-wrap items-center gap-4 text-sm font-medium text-slate-700">
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
