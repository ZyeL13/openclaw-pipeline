import '@/styles/globals.css';
import type { Metadata } from 'next';
import Script from 'next/script';

export const metadata: Metadata = {
  title: 'OpenClaw Lab | AI x Crypto Automation Experiments',
  description: 'Dokumentasi riset, multi-agent frameworks, dan otomatisasi pipeline AI.',
  keywords: 'AI agents, crypto trading bots, LLM comparison, video automation',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        {/* Google AdSense Script */}
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

