"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type CuriosityFact = {
  id: string;
  lead: string;
  courseName: string;
  location: string;
  href: string;
};

type Props = {
  facts: CuriosityFact[];
};

export function Top10CuriositiesCarousel({ facts }: Props) {
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    if (facts.length < 2) return;

    const timer = window.setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % facts.length);
    }, 5000);

    return () => window.clearInterval(timer);
  }, [facts.length]);

  if (facts.length === 0) return null;

  const activeFact = facts[activeIndex];
  const [locationPrep, ...locationRest] = activeFact.location.split(" ");
  const locationName = locationRest.join(" ");

  return (
    <section className="relative mt-12 overflow-hidden rounded-2xl bg-white p-6 shadow-lg ring-1 ring-slate-200 sm:p-10">
      {/* oversized decorative "?" watermark */}
      <span
        className="pointer-events-none absolute select-none font-black leading-none text-brand-100"
        style={{ top: -51, fontSize: 413, right: 18 }}
        aria-hidden="true"
      >
        ?
      </span>

      {/* header row */}
      <div className="relative">
        <h2 className="text-xs font-bold uppercase tracking-widest text-brand-600">Sabias Que</h2>
      </div>

      {/* fact */}
      <div className="relative mt-5">
        <div className="h-32 overflow-hidden sm:h-36">
          <p key={activeFact.id} className="text-2xl leading-relaxed text-slate-700 sm:text-3xl sm:leading-relaxed">
            {activeFact.lead}
            <br />
            <span className="font-black text-brand-600">{activeFact.courseName}</span>
            {" "}
            <span>{locationPrep} </span>
            <span className="font-bold">{locationName}</span>
          </p>
        </div>
        <Link
          href={activeFact.href}
          className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-brand-600 hover:underline"
          aria-label="Ver ranking Top 10"
        >
          Ver ranking completo
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4" aria-hidden="true">
            <path fillRule="evenodd" d="M3 10a.75.75 0 01.75-.75h10.69l-3.22-3.22a.75.75 0 111.06-1.06l4.5 4.5a.75.75 0 010 1.06l-4.5 4.5a.75.75 0 01-1.06-1.06l3.22-3.22H3.75A.75.75 0 013 10z" clipRule="evenodd" />
          </svg>
        </Link>
      </div>

      {/* navigation dots */}
      {facts.length > 1 && (
        <div className="mt-6 flex items-center gap-1.5" aria-label="Navegação de curiosidades">
          {facts.map((fact, index) => (
            <button
              key={fact.id}
              type="button"
              onClick={() => setActiveIndex(index)}
              className={`rounded-full transition-all ${
                index === activeIndex
                  ? "h-2 w-8 bg-brand-600"
                  : "h-2 w-2 bg-slate-200 hover:bg-slate-300"
              }`}
              aria-label={`Mostrar curiosidade ${index + 1}`}
            />
          ))}
        </div>
      )}
    </section>
  );
}
