import Link from "next/link";

export function Breadcrumbs({ items }: { items: { label: string; href?: string }[] }) {
  return (
    <nav aria-label="Breadcrumb" className="mb-6 text-sm text-slate-500">
      <ol className="flex flex-wrap gap-2">
        <li><Link href="/" className="hover:text-brand-700">Início</Link></li>
        {items.map((item) => (
          <li key={item.label} className="flex gap-2">
            <span>/</span>
            {item.href ? <Link href={item.href} className="hover:text-brand-700">{item.label}</Link> : <span>{item.label}</span>}
          </li>
        ))}
      </ol>
    </nav>
  );
}
