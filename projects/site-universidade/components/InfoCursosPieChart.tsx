"use client";

import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

type SliceItem = {
  name: string;
  value: number;
  color: string;
};

type Props = {
  data: SliceItem[];
  unit?: string;
};

export function InfoCursosPieChart({ data, unit = "" }: Props) {
  const fmt = (v: number | string) => `${v}${unit}`;
  return (
    <ResponsiveContainer width="100%" height={200}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="45%"
          outerRadius={70}
          labelLine={false}
        >
          {data.map((entry, index) => (
            <Cell key={index} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value, name) => [
            fmt(typeof value === "number" ? value : String(value ?? "")),
            name,
          ]}
        />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}
