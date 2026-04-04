// src/components/StatusCard.tsx
interface StatusProps {
  label: string;
  value: string | number;
  colorClass: string; // Misal: 'text-amber-400' atau 'text-cyan-400'
}

export default function StatusCard({ label, value, colorClass }: StatusProps) {
  return (
    <div className="terminal-border p-4 bg-green-950/5 hover:bg-green-950/20 transition-all duration-300 group">
      <p className="text-[10px] uppercase tracking-[0.2em] opacity-50 text-white group-hover:opacity-100 transition-opacity">
        {label}
      </p>
      <p className={`text-2xl font-bold mt-1 ${colorClass} tracking-tighter`}>
        {value}
      </p>
    </div>
  );
}

