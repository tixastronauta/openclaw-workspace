import { PORTUGAL_DISTRICT_PATHS } from "@/lib/portugalDistrictPaths";

export function DistrictMiniMap({ districtName, className = "h-14" }: { districtName?: string; className?: string }) {
  return (
    <svg viewBox="165 60 355 390" aria-hidden="true" className={`w-auto shrink-0 ${className}`}>
      {PORTUGAL_DISTRICT_PATHS.map((shape) => (
        <path
          key={shape.name}
          d={shape.d}
          fill={shape.name === districtName ? "#2563eb" : "#dbeafe"}
          stroke="#ffffff"
          strokeWidth={1.5}
        />
      ))}
    </svg>
  );
}
