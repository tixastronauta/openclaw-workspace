"use client";

import { ArrowRight, CircleHelp } from "lucide-react";
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
    <section className="mt-12 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="grid md:grid-cols-[11rem_minmax(0,1fr)]">
        <div className="flex items-center gap-3 border-b border-slate-200 bg-slate-50 px-6 py-5 md:block md:border-b-0 md:border-r md:py-8">
          <div className="flex size-11 items-center justify-center rounded-2xl bg-brand-600 text-white shadow-sm md:size-14">
            <CircleHelp className="size-6 md:size-7" aria-hidden="true" />
          </div>
          <h2 className="text-xs font-bold uppercase tracking-widest text-brand-700 md:mt-4">
            Sabias que
          </h2>
        </div>

        <div className="px-6 py-6 sm:px-8 md:py-8">
          <div className="min-h-32 overflow-hidden sm:min-h-28">
            <p key={activeFact.id} className="text-xl leading-relaxed text-slate-700 sm:text-2xl sm:leading-relaxed">
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
            className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-brand-600 hover:text-brand-900"
            aria-label="Ver ranking Top 10"
          >
            Ver ranking completo
            <ArrowRight className="size-4" aria-hidden="true" />
          </Link>
        </div>
      </div>

      {/* navigation dots */}
      {facts.length > 1 && (
        <div className="flex items-center gap-1.5 border-t border-slate-100 px-6 pb-5 pt-4 sm:px-8 md:ml-44" aria-label="Navegação de curiosidades">
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
