import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Physical Data Setup | ARGUS',
  description: 'Visual, student-scale guide for collecting a physical ARGUS acoustic response dataset with two laptops and a phone.',
};

export default function SetupLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return children;
}
