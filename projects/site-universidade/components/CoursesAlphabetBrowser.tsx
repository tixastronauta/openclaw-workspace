"use client";

import { useRef, useState } from "react";
import { CourseCard } from "@/components/CourseCard";
import type { Course } from "@/lib/courses";

const ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");
const FIRST_ROW = ALPHABET.slice(0, 13);
const SECOND_ROW = ALPHABET.slice(13);

type Props = {
  grouped: Record<string, Course[]>;
};

export function CoursesAlphabetBrowser({ grouped }: Props) {
  const firstAvailable = ALPHABET.find((l) => grouped[l]) ?? Object.keys(grouped)[0] ?? "A";
  const [selected, setSelected] = useState(firstAvailable);
  const coursesRef = useRef<HTMLDivElement>(null);
  const courses = grouped[selected] ?? [];

  function selectLetter(letter: string) {
    setSelected(letter);
    requestAnimationFrame(() => {
      coursesRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  function LetterButton({ letter }: { letter: string }) {
    const hasItems = Boolean(grouped[letter]);
    const isSelected = letter === selected;
    return (
      <button
        disabled={!hasItems}
        onClick={() => selectLetter(letter)}
        aria-pressed={isSelected}
        className={[
          "flex flex-1 items-center justify-center rounded-lg py-2 text-xs font-semibold transition",
          isSelected
            ? "bg-brand-600 text-white shadow-sm"
            : hasItems
            ? "text-slate-700 hover:bg-brand-50 hover:text-brand-700"
            : "cursor-not-allowed text-slate-300",
        ].join(" ")}
      >
        {letter}
      </button>
    );
  }

  return (
    <div className="mt-10">
      <nav aria-label="Filtrar por letra" className="sticky top-[4.5rem] z-20 rounded-2xl border border-slate-200 bg-white p-1.5 shadow-sm">
        {/* Mobile: 2 rows of 13 */}
        <div className="flex flex-col gap-0.5 sm:hidden">
          <div className="flex gap-0.5">
            {FIRST_ROW.map((l) => <LetterButton key={l} letter={l} />)}
          </div>
          <div className="flex gap-0.5">
            {SECOND_ROW.map((l) => <LetterButton key={l} letter={l} />)}
          </div>
        </div>
        {/* sm+: single row */}
        <div className="hidden gap-0.5 sm:flex">
          {ALPHABET.map((l) => <LetterButton key={l} letter={l} />)}
        </div>
      </nav>

      <div ref={coursesRef} className="mt-8 scroll-mt-44 sm:scroll-mt-40 grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
        {courses.map((course) => (
          <CourseCard key={course.slug} course={course} />
        ))}
      </div>
    </div>
  );
}
