import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Virtual Acoustic Bench | ARGUS',
  description: 'Interactive, physics-informed acoustic experiment simulator for the ARGUS research platform.',
};

export default function SimulatorLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return children;
}
