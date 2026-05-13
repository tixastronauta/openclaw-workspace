import Link from "next/link";

type BreadcrumbItem = { label: string; href?: string; title?: string };

export function Breadcrumbs({ items }: { items: BreadcrumbItem[] }) {
  return (
    <nav aria-label="Breadcrumb" className="mb-6 text-sm text-slate-500">
      <ol className="flex flex-wrap gap-2">
        <li><Link href="/" className="hover:text-brand-700">Início</Link></li>
        {items.map((item) => (
          <li key={item.label} className="flex gap-2">
            <span>/</span>
            {item.href
              ? <Link href={item.href} title={item.title} className="hover:text-brand-700">{item.label}</Link>
              : <span title={item.title}>{item.label}</span>}
          </li>
        ))}
      </ol>
    </nav>
  );
}
