import fs from 'fs';
import path from 'path';
import matter from 'gray-matter';
import Link from 'next/link';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Research Lab — All Logs',
  description: 'Index semua artikel riset AI agents, multi-agent orchestration, dan crypto automation oleh Zyel.',
  alternates: { canonical: 'https://zyel.vercel.app/lab' },
  openGraph: {
    title: 'Research Lab | OpenClaw Lab',
    description: 'Index riset AI × Crypto automation oleh Zyel.',
    url: 'https://zyel.vercel.app/lab',
  },
};

interface PostMeta {
  slug: string;
  title: string;
  date: string;
  status: string;
  excerpt: string;
}

function getPosts(): PostMeta[] {
  const dir = path.join(process.cwd(), 'src/posts');
  const files = fs.readdirSync(dir).filter(f => f.endsWith('.mdx'));
  return files
    .map(f => {
      const raw = fs.readFileSync(path.join(dir, f), 'utf8');
      const { data } = matter(raw);
      return {
        slug:    f.replace('.mdx', ''),
        title:   data.title   || f,
        date:    data.date    || '',
        status:  data.status  || 'Unknown',
        excerpt: data.excerpt || '',
      };
    })
    .sort((a, b) => (a.date < b.date ? 1 : -1));
}

const statusStyle: Record<string, string> = {
  Published: 'text-[var(--teal)] border-[var(--teal-dim)] bg-[var(--teal-glow)]',
  Draft:     'text-[var(--amber)] border-[var(--amber-dim)]',
};

export default function LabIndex() {
  const posts = getPosts();

  return (
    <main className="min-h-screen relative">
      <div className="crt-overlay" />
      <div className="grid-bg fixed inset-0 opacity-20 pointer-events-none" />

      <div className="relative z-10 max-w-3xl mx-auto px-4 sm:px-6 py-8 sm:py-14">

        {/* Header */}
        <header className="mb-8 border-b border-[var(--border)] pb-6">
          <Link
            href="/"
            className="inline-block text-[9px] tracking-[0.2em] text-[var(--text-dim)] hover:text-[var(--teal)] mb-6 border border-[var(--border)] px-2 py-1 transition-colors hover:border-[var(--teal)]"
          >
            ← RETURN_TO_DASHBOARD
          </Link>
          <p className="text-[10px] tracking-[0.25em] uppercase text-[var(--text-dim)] mb-1">
            openclaw_lab // research_index
          </p>
          <h1 className="text-2xl sm:text-3xl font-bold neon-text">
            LAB_JOURNAL
          </h1>
          <p className="text-[var(--text-dim)] text-xs mt-1">
            {posts.length} file(s) indexed — sorted by date desc
          </p>
        </header>

        {/* Post list */}
        <nav aria-label="Research posts" className="space-y-3">
          {posts.map((post, i) => (
            <Link
              key={post.slug}
              href={`/lab/${post.slug}`}
              className="terminal-card block p-4 sm:p-5 no-underline group fade-in-up"
              style={{ animationDelay: `${i * 0.08}s` }}
            >
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <span className={`text-[9px] tracking-widest px-1.5 py-0.5 border ${statusStyle[post.status] || 'text-[var(--text-dim)] border-[var(--border)]'}`}>
                  {post.status.toUpperCase()}
                </span>
                <span className="text-[9px] text-[var(--text-muted)]">{post.date}</span>
              </div>
              <h2 className="text-sm font-bold text-[var(--text-main)] group-hover:text-[var(--teal)] transition-colors mb-1 leading-snug">
                {post.title}
              </h2>
              {post.excerpt && (
                <p className="text-[11px] text-[var(--text-dim)] line-clamp-2 leading-relaxed">
                  {post.excerpt}
                </p>
              )}
              <span className="text-[9px] text-[var(--teal)] tracking-wider mt-2 inline-block opacity-0 group-hover:opacity-100 transition-opacity">
                READ_LOG →
              </span>
            </Link>
          ))}
        </nav>

        <footer className="mt-12 text-[9px] text-[var(--text-muted)]">
          END_OF_INDEX // {posts.length}_files_found
        </footer>
      </div>
    </main>
  );
}
