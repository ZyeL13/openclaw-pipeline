import '@/styles/globals.css';
import type { Metadata } from 'next';
import Script from 'next/script';

const BASE_URL = 'https://zyel.vercel.app';

export const metadata: Metadata = {
  metadataBase: new URL(BASE_URL),
  title: {
    default: 'OpenClaw Lab — AI × Crypto Automation by Zyel',
    template: '%s | OpenClaw Lab',
  },
  description:
    'Dokumentasi riset AI agents, multi-agent orchestration, crypto automation pipeline, dan eksperimen LLM oleh Zyel — dibangun dari Android via Termux.',
  keywords: [
    'AI agents', 'multi-agent orchestration', 'crypto automation', 'LLM comparison',
    'video automation', 'Termux AI', 'Groq API', 'self-healing pipeline',
    'Binance automation', 'Indonesian AI developer', 'OpenClaw Lab',
  ],
  authors: [{ name: 'Zyel', url: BASE_URL }],
  creator: 'Zyel',
  robots: { index: true, follow: true },
  openGraph: {
    type: 'website',
    locale: 'id_ID',
    url: BASE_URL,
    siteName: 'OpenClaw Lab',
    title: 'OpenClaw Lab — AI × Crypto Automation',
    description: 'Riset AI agents, multi-agent orchestration, dan crypto automation pipeline oleh Zyel.',
    images: [{ url: '/og-default.png', width: 1200, height: 630, alt: 'OpenClaw Lab' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'OpenClaw Lab — AI × Crypto Automation',
    description: 'Riset AI agents dan crypto automation oleh Zyel.',
    images: ['/og-default.png'],
  },
  alternates: { canonical: BASE_URL },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
        <link rel="icon" href="/favicon.ico" sizes="any" />
        <Script
          async
          src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-5429089740484905"
          crossOrigin="anonymous"
          strategy="afterInteractive"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
