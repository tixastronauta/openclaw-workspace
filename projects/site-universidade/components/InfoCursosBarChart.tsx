"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type DataItem = {
  label: string;
  value: number;
};

type Props = {
  data: DataItem[];
  unit?: string;
  color?: string;
};

export function InfoCursosBarChart({ data, unit = "", color = "#2563eb" }: Props) {
  const fmt = (v: number | string) => `${v}${unit}`;
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
        <XAxis dataKey="label" tick={{ fontSize: 11 }} />
        <YAxis tickFormatter={fmt} tick={{ fontSize: 11 }} width={44} />
        <Tooltip
          formatter={(value) => fmt(typeof value === "number" ? value : String(value ?? ""))}
        />
        <Bar dataKey="value" fill={color} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
