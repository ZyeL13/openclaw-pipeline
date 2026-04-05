import Terminal from '@/components/Terminal';
import StatusCard from '@/components/StatusCard';
import VideoGrid from '@/components/VideoGrid';
import Link from 'next/link';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'OpenClaw Lab — AI × Crypto Automation Dashboard',
  alternates: { canonical: 'https://zyel.vercel.app' },
};

const labLogs = [
  '[INIT] ............. OpenClaw Neural Link — established',
  '[LOG-001] .......... Deploying multi-agent orchestrator',
  '[LOG-002] .......... Arsitektur 5-agent compiled',
  '[LOG-003] .......... Self-healing pipeline — active',
  '[DATA] ............. AI × Crypto research pipeline live',
  '[SYS] .............. Binance Square auto-poster — running',
  '[STATUS] ........... All systems nominal. Awaiting input_',
];

const stats = [
  { label: 'Pipeline Status', value: 'LIVE',      color: 'text-[var(--teal)]' },
  { label: 'Agent Count',     value: '5',          color: 'text-[var(--amber)]' },
  { label: 'Posts / Day',     value: '5×',         color: 'text-[var(--cyan)]' },
  { label: 'Stack',           value: 'FREE',       color: 'text-[var(--teal)]' },
];

const projects = [
  {
    id: 'konten-empire',
    title: 'Konten Empire Pipeline',
    desc: 'Fully automated TikTok/Reels/Shorts pipeline — Groq + Edge TTS + Pollinations + FFmpeg. Zero cost.',
    status: 'ACTIVE',
    lang: 'Python',
    tags: ['multi-agent', 'video', 'AI'],
  },
  {
    id: 'square-auto',
    title: 'Binance Square Autoposter',
    desc: '5 content categories (Hot, Alpha, New, Gainers, Losers) auto-generated from live Binance API data.',
    status: 'ACTIVE',
    lang: 'Python',
    tags: ['crypto', 'automation', 'Groq'],
  },
  {
    id: 'self-heal',
    title: 'Self-Healing Maintainer',
    desc: 'Error detection → AI diagnosis → auto-patch → validation → rollback loop. Runs unattended.',
    status: 'BETA',
    lang: 'Python',
    tags: ['LLM', 'devops', 'reliability'],
  },
];

export default function Dashboard() {
  return (
    <main className="min-h-screen relative">
      <div className="crt-overlay" />
      <div className="grid-bg fixed inset-0 opacity-30 pointer-events-none" />

      <div className="relative z-10 max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-10 space-y-6 sm:space-y-8">

        {/* ── HEADER ──────────────────────────────────────────── */}
        <header className="fade-in-up border-b border-[var(--border)] pb-5 sm:pb-6">
          <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
            <div>
              <p className="text-[10px] tracking-[0.25em] uppercase text-[var(--text-dim)] mb-1">
                openclaw_lab v1.0a — terminal dashboard
              </p>
              <h1 className="text-2xl sm:text-3xl font-bold neon-text leading-tight">
                OPENCLAW LAB
              </h1>
              <p className="text-[var(--text-dim)] text-xs mt-1 max-w-lg">
                AI × Crypto automation research by{' '}
                <span className="text-[var(--amber)]">Zyel</span>
                {' '}— built from Android via Termux
              </p>
            </div>
            <div className="flex items-center gap-2 text-[10px]">
              <span className="w-2 h-2 rounded-full bg-[var(--teal)] animate-pulse" />
              <span className="text-[var(--teal)] tracking-widest">ALL_SYSTEMS_NOMINAL</span>
            </div>
          </div>
        </header>

        {/* ── STATS ROW ────────────────────────────────────────── */}
        <section
          aria-label="System Statistics"
          className="grid grid-cols-2 sm:grid-cols-4 gap-3 fade-in-up delay-1"
        >
          {stats.map((s) => (
            <StatusCard key={s.label} label={s.label} value={s.value} colorClass={s.color} />
          ))}
        </section>

        {/* ── MAIN GRID ────────────────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 sm:gap-6">

          {/* Terminal Log */}
          <section
            aria-label="System Log"
            className="lg:col-span-7 fade-in-up delay-2"
          >
            <div className="flex justify-between items-center mb-2">
              <h2 className="text-[10px] font-bold tracking-[0.2em] uppercase text-[var(--text-dim)]">
                SYS_LOG // lab_journal_v1
              </h2>
              <Link
                href="/lab"
                className="text-[9px] text-[var(--cyan)] hover:text-[var(--teal)] tracking-widest transition-colors border border-[var(--border)] px-2 py-0.5 hover:border-[var(--teal)]"
              >
                VIEW_ALL_LOGS →
              </Link>
            </div>
            <Terminal logs={labLogs} />
          </section>

          {/* Video Queue */}
          <section
            aria-label="Video Pipeline Queue"
            className="lg:col-span-5 fade-in-up delay-3"
          >
            <div className="flex justify-between items-center mb-2">
              <h2 className="text-[10px] font-bold tracking-[0.2em] uppercase text-[var(--text-dim)]">
                VIDEO_PIPELINE // output_queue
              </h2>
              <span className="text-[9px] text-[var(--text-muted)] tracking-wider">KONTEN_EMPIRE</span>
            </div>
            <VideoGrid />
          </section>
        </div>

        {/* ── PROJECTS ──────────────────────────────────────────── */}
        <section aria-label="Active Projects" className="fade-in-up delay-4">
          <h2 className="text-[10px] font-bold tracking-[0.2em] uppercase text-[var(--text-dim)] mb-3">
            ACTIVE_PROJECTS // experiment_registry
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map((p) => (
              <div key={p.id} className="terminal-card p-4 group">
                <div className="flex justify-between items-start mb-2">
                  <span className={`text-[9px] tracking-widest px-1.5 py-0.5 border ${
                    p.status === 'ACTIVE'
                      ? 'border-[var(--teal)] text-[var(--teal)] bg-[var(--teal-glow)]'
                      : 'border-[var(--amber-dim)] text-[var(--amber)] bg-transparent'
                  }`}>
                    {p.status}
                  </span>
                  <span className="text-[9px] text-[var(--text-muted)] font-mono">{p.lang}</span>
                </div>
                <h3 className="text-sm font-bold text-[var(--text-main)] mb-1.5 leading-snug group-hover:text-[var(--teal)] transition-colors">
                  {p.title}
                </h3>
                <p className="text-[11px] text-[var(--text-dim)] leading-relaxed mb-3">{p.desc}</p>
                <div className="flex flex-wrap gap-1.5">
                  {p.tags.map((t) => (
                    <span key={t} className="text-[9px] px-1.5 py-0.5 bg-[var(--teal-glow)] text-[var(--teal-dim)] border border-[var(--border)]">
                      #{t}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ── FOOTER ────────────────────────────────────────────── */}
        <footer className="fade-in-up delay-5 border-t border-[var(--border)] pt-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 text-[9px] text-[var(--text-muted)]">
          <span>OPENCLAW_LAB // ZyeL13 // JAKARTA, ID</span>
          <span>STACK: TERMUX × PYTHON × NEXT.JS × GROQ × FREE_TIER</span>
        </footer>
      </div>
    </main>
  );
}
