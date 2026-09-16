import type { Metadata } from 'next';
import './globals.css';
import { SpatialWorld } from '@/components/SpatialWorld';

export const metadata: Metadata = {
  title: 'ARGUS — Adaptive Physical Intelligence',
  description: 'AI that decides what physical experiment to perform next.',
  metadataBase: new URL('https://argus-neo-research.ripan-konar2024.chatgpt.site'),
  openGraph: {
    type: 'website',
    title: 'ARGUS. See beyond the surface.',
    description: 'A research instrument for adaptive acoustic experiments, visible uncertainty, and auditable evidence.',
    images: [{ url: 'https://argus-neo-research.ripan-konar2024.chatgpt.site/og.png', width: 1733, height: 907, alt: 'ARGUS. See beyond the surface. Conceptual acoustic panel illustration.' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'ARGUS. See beyond the surface.',
    description: 'Adaptive acoustic experiments. Visible uncertainty. Auditable evidence.',
    images: ['https://argus-neo-research.ripan-konar2024.chatgpt.site/og.png'],
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><SpatialWorld>{children}</SpatialWorld></body></html>;
}
