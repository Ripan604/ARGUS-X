import type { Metadata } from 'next';
import Link from 'next/link';
import { ResearchEvidence } from '@/components/ResearchEvidence';

export const metadata: Metadata = {
  title: 'ARGUS — Research evidence',
  description: 'Recorded paired synthetic evaluation of nuisance-aware acoustic experiment design, including failures and uncertainty.',
  openGraph: { title: 'ARGUS — Let the evidence disagree.', description: 'Inspect the full synthetic comparison, including inconclusive results and failures.' },
  twitter: { title: 'ARGUS — Let the evidence disagree.', description: 'Inspect the full synthetic comparison, including inconclusive results and failures.' },
};

export default function ResearchEvidencePage() {
  return <main className="setup-shell">
    <header className="setup-nav"><Link href="/" className="brand-lockup"><div className="brand-mark"><span /></div><div><strong>ARGUS.</strong><small>PHYSICAL INTELLIGENCE</small></div></Link><div><Link href="/simulator" className="probe-link">VIRTUAL LAB</Link><Link href="/" className="ghost-button">BACK TO ARGUS</Link></div></header>
    <section className="secondary-page"><ResearchEvidence /><p className="brain-note">This recorded study can be viewed without the local acoustic engine. Interactive ARGUS sessions require the Python backend running on your computer.</p></section>
  </main>;
}
