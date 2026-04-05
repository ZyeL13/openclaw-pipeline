import fs from 'fs';
import path from 'path';
import matter from 'gray-matter';
import { compileMDX } from 'next-mdx-remote/rsc';
import Link from 'next/link';
import type { Metadata } from 'next';

const BASE_URL = 'https://zyel.vercel.app';
const postsDir = () => path.join(process.cwd(), 'src/posts');

export async function generateStaticParams() {
  return fs.readdirSync(postsDir())
    .filter(f => f.endsWith('.mdx'))
    .map(f => ({ slug: f.replace('.mdx', '') }));
}

export async function generateMetadata({ params }: { params: { slug: string } }): Promise<Metadata> {
  const { slug } = await params;
  const raw = fs.readFileSync(path.join(postsDir(), `${slug}.mdx`), 'utf8');
  const { data } = matter(raw);
  const url = `${BASE_URL}/lab/${slug}`;

  return {
    title: data.title || slug,
    description: data.excerpt || data.description || '',
    authors: [{ name: data.author || 'Zyel', url: BASE_URL }],
    alternates: { canonical: url },
    openGraph: {
      type: 'article',
      url,
      title: data.title,
      description: data.excerpt || '',
      publishedTime: data.date,
      authors: [data.author || 'Zyel'],
      images: [{ url: '/og-default.png', width: 1200, height: 630 }],
    },
    twitter: {
      card: 'summary_large_image',
      title: data.title,
      description: data.excerpt || '',
    },
    other: {
      'article:published_time': data.date,
    },
  };
}

// MDX component overrides — inherits .prose-terminal styles from CSS
const components = {
  a:          (props: any) => <a className="text-[var(--cyan)] underline underline-offset-2 hover:text-[var(--teal)] transition-colors" {...props} />,
  blockquote: (props: any) => <blockquote {...props} />,
  h2:         (props: any) => <h2 {...props} />,
  h3:         (props: any) => <h3 {...props} />,
  code:       (props: any) => <code {...props} />,
  pre:        (props: any) => <pre {...props} />,
};

export default async function ArticlePage({ params }: { params: { slug: string } }) {
  const { slug } = await params;
  const filePath = path.join(postsDir(), `${slug}.mdx`);
  const source = fs.readFileSync(filePath, 'utf8');

  const { content, frontmatter } = await compileMDX({
    source,
    components,
    options: { parseFrontmatter: true },
  });

  const { title, date, status, author, excerpt } = frontmatter as {
    title: string; date: string; status: string; author: string; excerpt?: string;
  };

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: title,
    description: excerpt || '',
    datePublished: date,
    author: { '@type': 'Person', name: author, url: BASE_URL },
    publisher: { '@type': 'Person', name: 'Zyel', url: BASE_URL },
    url: `${BASE_URL}/lab/${slug}`,
  };

  return (
    <main className="min-h-screen relative selection:bg-[var(--teal)] selection:text-black">
      <div className="crt-overlay" />
      <div className="grid-bg fixed inset-0 opacity-15 pointer-events-none" />

      {/* JSON-LD */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <div className="relative z-10 max-w-2xl mx-auto px-4 sm:px-6 py-8 sm:py-14">

        {/* Back nav */}
        <Link
          href="/lab"
          className="inline-block text-[9px] tracking-[0.2em] text-[var(--text-dim)] hover:text-[var(--teal)] mb-8 border border-[var(--border)] px-2 py-1 transition-colors hover:border-[var(--teal)]"
        >
          ← KEMBALI_KE_LAB
        </Link>

        <article itemScope itemType="https://schema.org/Article">

          {/* Article header */}
          <header className="mb-10 border-b border-[var(--border)] pb-7">
            <div className="flex flex-wrap gap-2 mb-4">
              <span className={`text-[9px] tracking-widest px-1.5 py-0.5 border ${
                status === 'Published'
                  ? 'text-[var(--teal)] border-[var(--teal-dim)] bg-[var(--teal-glow)]'
                  : 'text-[var(--amber)] border-[var(--amber-dim)]'
              }`}>
                {status?.toUpperCase()}
              </span>
              <span className="text-[9px] text-[var(--text-muted)] border border-[var(--border)] px-1.5 py-0.5">
                {date}
              </span>
            </div>

            <h1
              itemProp="headline"
              className="text-xl sm:text-2xl font-black neon-text leading-tight mb-3"
            >
              {title}
            </h1>

            {excerpt && (
              <p className="text-sm text-[var(--text-dim)] leading-relaxed italic">
                {excerpt}
              </p>
            )}

            <div className="mt-4 text-[9px] text-[var(--text-muted)] flex flex-wrap gap-x-4 gap-y-1">
              <span>author: <span className="text-[var(--amber)]">{author}</span></span>
              <span>file: <span className="text-[var(--text-dim)]">{slug}.mdx</span></span>
            </div>
          </header>

          {/* Article body */}
          <section
            className="prose-terminal"
            itemProp="articleBody"
          >
            {content}
          </section>

          {/* Footer */}
          <footer className="mt-14 pt-6 border-t border-[var(--border)] flex flex-col sm:flex-row justify-between gap-2 text-[9px] text-[var(--text-muted)]">
            <span>FILE_ID: {slug.toUpperCase()}.MDX</span>
            <span>END_OF_TRANSMISSION</span>
          </footer>
        </article>

        {/* Navigation CTA */}
        <div className="mt-10 flex gap-3">
          <Link
            href="/lab"
            className="text-[10px] tracking-widest border border-[var(--border)] px-3 py-2 text-[var(--text-dim)] hover:border-[var(--teal)] hover:text-[var(--teal)] transition-colors"
          >
            ← ALL_LOGS
          </Link>
          <Link
            href="/"
            className="text-[10px] tracking-widest border border-[var(--border)] px-3 py-2 text-[var(--text-dim)] hover:border-[var(--teal)] hover:text-[var(--teal)] transition-colors"
          >
            ⌂ DASHBOARD
          </Link>
        </div>
      </div>
    </main>
  );
}
