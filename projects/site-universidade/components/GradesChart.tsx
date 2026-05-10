"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type AdmissionGrade = {
  year: string;
  phase?: string;
  grade: string;
};

type ChartPoint = {
  year: string;
  [phase: string]: string | number | undefined;
};

const PHASE_COLORS: Record<string, string> = {
  "1.ª fase": "#2563eb",
  "2.ª fase": "#7c3aed",
};
const FALLBACK_COLOR = "#2563eb";

function parseGrade(grade: string): number | null {
  const n = parseFloat(grade.replace(",", "."));
  return isNaN(n) ? null : n;
}

function CustomTooltip({ active, payload, label }: {
  active?: boolean;
  payload?: { name: string; value: number; color: string }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-lg text-sm">
      <p className="mb-2 font-semibold text-slate-800">{label}</p>
      {payload.map((entry) => (
        <p key={entry.name} style={{ color: entry.color }} className="font-medium">
          {entry.name}: <span className="tabular-nums">{entry.value.toFixed(1)}</span>
        </p>
      ))}
    </div>
  );
}

export function GradesChart({ grades }: { grades: AdmissionGrade[] }) {
  if (grades.length === 0) return null;

  // Gather unique phases
  const phases = Array.from(new Set(grades.map((g) => g.phase ?? "Nota"))).sort();

  // Build one data point per year
  const byYear = new Map<string, ChartPoint>();
  for (const grade of grades) {
    const n = parseGrade(grade.grade);
    if (n === null) continue;
    const key = grade.year;
    const phase = grade.phase ?? "Nota";
    byYear.set(key, { ...(byYear.get(key) ?? { year: key }), [phase]: n });
  }

  const data = Array.from(byYear.values()).sort((a, b) => a.year.localeCompare(b.year));
  if (data.length < 2) return null; // chart not useful with a single point

  // Y-axis nice bounds
  const allValues = grades.map((g) => parseGrade(g.grade)).filter((n): n is number => n !== null);
  const minVal = Math.max(0, Math.floor(Math.min(...allValues) - 5));
  const maxVal = Math.min(200, Math.ceil(Math.max(...allValues) + 5));

  return (
    <div className="mt-6">
      <p className="mb-4 text-xs font-medium uppercase tracking-wide text-slate-500">
        Evolução das notas de entrada
      </p>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: 8, right: 16, left: -8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
          <XAxis
            dataKey="year"
            tick={{ fontSize: 12, fill: "#64748b" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            domain={[minVal, maxVal]}
            tick={{ fontSize: 12, fill: "#64748b" }}
            axisLine={false}
            tickLine={false}
            width={36}
          />
          <Tooltip content={<CustomTooltip />} />
          {phases.length > 1 && (
            <ReferenceLine stroke="#e2e8f0" strokeDasharray="0" />
          )}
          {phases.map((phase) => (
            <Line
              key={phase}
              type="monotone"
              dataKey={phase}
              name={phase}
              stroke={PHASE_COLORS[phase] ?? FALLBACK_COLOR}
              strokeWidth={2.5}
              dot={{ r: 4, fill: PHASE_COLORS[phase] ?? FALLBACK_COLOR, strokeWidth: 0 }}
              activeDot={{ r: 6, strokeWidth: 0 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
      {phases.length > 1 && (
        <div className="mt-3 flex flex-wrap gap-4">
          {phases.map((phase) => (
            <span key={phase} className="flex items-center gap-1.5 text-xs text-slate-600">
              <span
                className="inline-block h-2.5 w-5 rounded-full"
                style={{ background: PHASE_COLORS[phase] ?? FALLBACK_COLOR }}
              />
              {phase}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
