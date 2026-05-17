"use client";

import { useEffect, useMemo, useState } from "react";
import { PORTUGAL_DISTRICT_PATHS } from "@/lib/portugalDistrictPaths";

type DistrictSummary = {
  slug: string;
  name: string;
  facultyCount: number;
  courseCount: number;
};

function plural(value: number, one: string, many: string) {
  return `${value} ${value === 1 ? one : many}`;
}

export function PortugalDistrictMap({ districts }: { districts: DistrictSummary[] }) {
  const byName = useMemo(() => new Map(districts.map((district) => [district.name, district])), [districts]);
  const [autoIndex, setAutoIndex] = useState(0);
  const [hovered, setHovered] = useState<DistrictSummary | null>(null);
  const [paused, setPaused] = useState(false);
  const activeDistrict = hovered ?? districts[autoIndex % Math.max(districts.length, 1)] ?? null;

  useEffect(() => {
    if (paused || districts.length === 0) return;

    const timer = window.setInterval(() => {
      setAutoIndex((current) => (current + 1) % districts.length);
    }, 1800);

    return () => window.clearInterval(timer);
  }, [districts.length, paused]);

  return (
    <div className="relative w-full">
      {activeDistrict && (
        <div className="absolute z-10 rounded-2xl border border-brand-100 bg-white/95 px-4 py-3 text-center text-sm shadow-lg backdrop-blur" style={{ left: 100, top: 110, width: 160 }}>
          <p className="font-semibold text-brand-900">{activeDistrict.name}</p>
          <p className="text-brand-800">{plural(activeDistrict.facultyCount, "instituição", "instituições")}</p>
          <p className="text-brand-800">{plural(activeDistrict.courseCount, "curso", "cursos")}</p>
        </div>
      )}

      <svg viewBox="165 75 355 360" role="img" aria-label="Mapa de Portugal por distrito" className="block h-auto w-full">
        <defs>
          <filter id="mapShadow" x="-8%" y="-8%" width="116%" height="116%">
            <feDropShadow dx="0" dy="2" stdDeviation="2" floodOpacity="0.12" />
          </filter>
        </defs>
        <g filter="url(#mapShadow)">
          {PORTUGAL_DISTRICT_PATHS.map((shape) => {
            const district = byName.get(shape.name);
            const active = activeDistrict?.name === shape.name;
            const hasData = Boolean(district);

            return (
              <a
                key={shape.name}
                href={district ? `/distritos/${district.slug}/` : "/distritos/"}
                onMouseEnter={() => {
                  setPaused(true);
                  setHovered(district ?? null);
                }}
                onMouseLeave={() => {
                  setHovered(null);
                  setPaused(false);
                }}
                onFocus={() => {
                  setPaused(true);
                  setHovered(district ?? null);
                }}
                onBlur={() => {
                  setHovered(null);
                  setPaused(false);
                }}
                aria-label={district ? `${district.name}: ${plural(district.facultyCount, "instituição", "instituições")}, ${plural(district.courseCount, "curso", "cursos")}` : shape.name}
                className="outline-none"
              >
                <path
                  d={shape.d}
                  className={`transition duration-150 ${hasData ? "cursor-pointer" : "cursor-default"}`}
                  fill={active ? "#2563eb" : hasData ? "#dbeafe" : "#f1f5f9"}
                  stroke={active ? "#1d4ed8" : "#ffffff"}
                  strokeWidth={active ? 1.7 : 1.1}
                />
              </a>
            );
          })}
        </g>
      </svg>
    </div>
  );
}
