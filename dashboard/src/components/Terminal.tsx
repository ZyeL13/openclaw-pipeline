'use client';
import { useEffect, useRef } from 'react';

interface TerminalProps {
  logs: string[];
  title?: string;
}

export default function Terminal({ logs, title = 'openclaw_v1.0a — system.log' }: TerminalProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div
      className="terminal-border bg-[#060908] rounded-lg overflow-hidden"
      role="log"
      aria-label="System terminal output"
      aria-live="polite"
    >
      {/* Title bar */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-[var(--border)] bg-[#0a0f0d]">
        <span className="w-2.5 h-2.5 rounded-full bg-[var(--red-dim)]" />
        <span className="w-2.5 h-2.5 rounded-full bg-[var(--amber-dim)]" />
        <span className="w-2.5 h-2.5 rounded-full bg-[var(--teal-dim)]" />
        <span className="ml-2 text-[10px] text-[var(--text-dim)] italic truncate">{title}</span>
      </div>

      {/* Log output */}
      <div className="p-4 h-56 sm:h-64 overflow-y-auto font-mono text-[11px] sm:text-xs space-y-1.5">
        {logs.map((log, i) => (
          <div
            key={i}
            className="flex gap-2 items-baseline opacity-0 animate-[fadeInUp_0.3s_ease_forwards]"
            style={{ animationDelay: `${i * 0.08}s` }}
          >
            <span className="text-[var(--teal-dim)] shrink-0 select-none">$</span>
            <span className="text-[var(--text-main)] leading-relaxed break-all">{log}</span>
          </div>
        ))}
        <div ref={bottomRef} className="flex items-center gap-1 pt-1">
          <span className="text-[var(--text-dim)]">$</span>
          <span className="cursor-blink inline-block w-1.5 h-3.5 bg-[var(--teal)] align-middle" />
        </div>
      </div>
    </div>
  );
}
