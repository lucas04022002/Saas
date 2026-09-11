export function Kpi({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return <div className="border-b border-line py-6 md:border-r md:pr-6 md:[&:last-child]:border-r-0"><div className="eyebrow">{label}</div><div className="mt-2 font-tight text-[44px] md:text-[56px] font-extrabold leading-none tracking-[-0.06em]">{value}{unit && <span className="ml-1 text-[22px] tracking-[-0.02em]">{unit}</span>}</div></div>;
}
