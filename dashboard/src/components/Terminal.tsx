// src/components/Terminal.tsx
export default function Terminal({ logs }: { logs: string[] }) {
  return (
    <div className="terminal-border bg-black/80 p-4 rounded-lg h-64 overflow-y-auto font-mono text-xs md:text-sm">
      <div className="flex gap-2 mb-2 border-b border-green-900/50 pb-1">
        <span className="w-3 h-3 rounded-full bg-red-500/50"></span>
        <span className="w-3 h-3 rounded-full bg-yellow-500/50"></span>
        <span className="w-3 h-3 rounded-full bg-green-500/50"></span>
        <span className="ml-2 text-green-700 italic">openclaw_v1.0a - system.log</span>
      </div>
      {logs.map((log, i) => (
        <div key={i} className="mb-1">
          <span className="text-green-500 tracking-tighter">[SYS-OK]:</span> {log}
        </div>
      ))}
      <div className="animate-pulse inline-block w-2 h-4 bg-green-500 ml-1 align-middle"></div>
    </div>
  );
}

