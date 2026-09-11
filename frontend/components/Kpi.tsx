export function Kpi({ label, value, unit, dark = false }: { label: string; value: string; unit?: string; dark?: boolean }) {
  const line = dark ? "border-line-dark" : "border-line";
  const eyebrow = dark ? "text-xs font-semibold uppercase tracking-[0.08em] text-faint-dark" : "eyebrow";
  return (
    <div className={`border-b ${line} py-6 md:border-r md:pr-6 md:[&:last-child]:border-r-0`}>
      <div className={eyebrow}>{label}</div>
      <div className="mt-2 font-tight text-[44px] md:text-[56px] font-extrabold leading-none tracking-[-0.06em]">{value}{unit && <span className="ml-1 text-[22px] tracking-[-0.02em]">{unit}</span>}</div>
    </div>
  );
}
