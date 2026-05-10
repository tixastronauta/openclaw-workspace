type MapEmbedProps = {
  query?: string;
  title?: string;
};

export function MapEmbed({ query, title = "Localização no Google Maps" }: MapEmbedProps) {
  const trimmedQuery = query?.trim();
  if (!trimmedQuery) return null;

  const encodedQuery = encodeURIComponent(trimmedQuery);
  const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodedQuery}`;
  const embedUrl = `https://www.google.com/maps?q=${encodedQuery}&output=embed`;

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="p-5">
        <h2 className="text-lg font-semibold text-slate-950">Localização</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">{trimmedQuery}</p>
      </div>
      <iframe
        src={embedUrl}
        title={title}
        loading="lazy"
        referrerPolicy="no-referrer-when-downgrade"
        className="h-64 w-full border-0"
      />
      <div className="border-t border-slate-100 p-5">
        <a
          href={mapsUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm font-semibold text-brand-700 hover:text-brand-900"
        >
          Abrir no Google Maps →
        </a>
      </div>
    </section>
  );
}
