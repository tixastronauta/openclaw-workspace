"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { VacancyHistoryPoint } from "@/lib/courses";

type ChartPoint = {
  year: string;
  [phase: string]: string | number | undefined;
};

const PHASE_COLORS: Record<string, string> = {
  "1.ª fase": "#2563eb",
  "2.ª fase": "#16a34a",
  "Ano atual": "#f59e0b",
};

const FALLBACK_COLOR = "#2563eb";

function yearOrder(value: string): number {
  const match = value.match(/\d{4}/);
  return match ? Number(match[0]) : 0;
}

function phaseOrder(value: string): number {
  if (value === "1.ª fase") return 1;
  if (value === "2.ª fase") return 2;
  if (value === "Ano atual") return 3;
  return 99;
}

function CustomTooltip({ active, payload, label }: {
  active?: boolean;
  payload?: { name: string; value: number; color: string }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;

  return (
    <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-lg">
      <p className="mb-2 font-semibold text-slate-800">{label}</p>
      {payload.map((entry) => (
        <p key={entry.name} style={{ color: entry.color }} className="font-medium">
          {entry.name}: <span className="tabular-nums">{entry.value}</span>
        </p>
      ))}
    </div>
  );
}

export function VacanciesChart({ vacancies }: { vacancies: VacancyHistoryPoint[] }) {
  if (vacancies.length === 0) return null;

  const phases = Array.from(new Set(vacancies.map((item) => item.phase)))
    .sort((a, b) => phaseOrder(a) - phaseOrder(b) || a.localeCompare(b, "pt"));

  const byYear = new Map<string, ChartPoint>();
  for (const item of vacancies) {
    byYear.set(item.year, {
      ...(byYear.get(item.year) ?? { year: item.year }),
      [item.phase]: item.vacancies,
    });
  }

  const data = Array.from(byYear.values()).sort((a, b) => yearOrder(a.year) - yearOrder(b.year));
  const values = vacancies.map((item) => item.vacancies);
  const maxValue = Math.max(...values);
  const yMax = Math.max(10, Math.ceil((maxValue + 2) / 5) * 5);

  return (
    <div className="mt-6">
      <p className="mb-4 text-xs font-medium uppercase tracking-wide text-slate-500">
        Evolução do número de vagas
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
            allowDecimals={false}
            domain={[0, yMax]}
            tick={{ fontSize: 12, fill: "#64748b" }}
            axisLine={false}
            tickLine={false}
            width={36}
          />
          <Tooltip content={<CustomTooltip />} />
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
      {phases.length > 0 && (
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