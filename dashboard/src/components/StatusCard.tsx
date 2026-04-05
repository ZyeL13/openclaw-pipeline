interface StatusProps {
  label: string;
  value: string | number;
  colorClass: string;
}

export default function StatusCard({ label, value, colorClass }: StatusProps) {
  return (
    <div className="terminal-card p-3 sm:p-4 group">
      <p className="text-[9px] uppercase tracking-[0.2em] text-[var(--text-dim)] mb-1 group-hover:text-[var(--text-main)] transition-colors">
        {label}
      </p>
      <p className={`text-xl sm:text-2xl font-bold tracking-tighter ${colorClass}`}>
        {value}
      </p>
    </div>
  );
}
