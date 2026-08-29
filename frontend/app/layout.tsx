import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'ARGUS — Adaptive Physical Intelligence',
  description: 'AI that decides what physical experiment to perform next.',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
