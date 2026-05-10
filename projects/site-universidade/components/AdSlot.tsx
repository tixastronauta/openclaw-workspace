export const ADS_ENABLED = process.env.NEXT_PUBLIC_ENABLE_AD_SLOTS === "true";

export function AdSlot({ label = "Espaço reservado para publicidade" }: { label?: string }) {
  if (!ADS_ENABLED) return null;

  return (
    <aside className="rounded-2xl border border-dashed border-slate-300 bg-white/70 p-6 text-center text-sm text-slate-500" aria-label={label}>
      <span className="block font-medium text-slate-700">Publicidade</span>
      <span>{label}</span>
    </aside>
  );
}
