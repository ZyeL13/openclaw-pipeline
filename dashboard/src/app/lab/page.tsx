import fs from 'fs';
import path from 'path';
import Link from 'next/link';

export default function LabIndex() {
  const postsDirectory = path.join(process.cwd(), 'src/posts');
  const filenames = fs.readdirSync(postsDirectory);
  const posts = filenames.filter(f => f.endsWith('.mdx')).map(f => f.replace('.mdx', ''));

  return (
    <main className="min-h-screen p-10 bg-black text-green-500 font-mono">
      <div className="crt-overlay" />
      <h1 className="text-2xl font-bold neon-text mb-8 italic uppercase">[INDEX_RESEARCH_LOGS]</h1>
      <div className="grid gap-4">
        {posts.map(slug => (
          <Link key={slug} href={`/lab/${slug}`} className="border border-green-900 p-4 hover:bg-green-500 hover:text-black transition-all group">
            <span className="text-xs opacity-50 group-hover:text-black">FILE:</span> {slug.toUpperCase()}
          </Link>
        ))}
      </div>
      <Link href="/" className="mt-10 inline-block text-[10px] underline">RETURN_TO_DASHBOARD</Link>
    </main>
  );
}

