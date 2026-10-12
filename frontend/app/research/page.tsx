import type { Metadata } from 'next';
import Link from 'next/link';
import { ResearchEvidence } from '@/components/ResearchEvidence';
import { MeasuredDataEvidence } from '@/components/MeasuredDataEvidence';
import { FundamentalEvidence } from '@/components/FundamentalEvidence';
import styles from '@/components/researchEvidence.module.css';

export const metadata: Metadata = {
  title: 'ARGUS — Evidence laboratory',
  description: 'Inspect source-checked external recordings, completed reference-conditioned confirmation, retained model failures and historical synthetic comparisons.',
  openGraph: { title: 'ARGUS — Evidence laboratory', description: 'Measured results, physical scope and negative findings remain visible together.' },
  twitter: { title: 'ARGUS — Evidence laboratory', description: 'Explore measured studies and the completed 29-bank confirmation.' },
};

export default function ResearchEvidencePage() {
  return <main className={styles.page}>
    <header className={styles.nav}><Link href="/" className={styles.brand}>ARGUS.<small>PHYSICAL INTELLIGENCE / RESEARCH</small></Link><nav className={styles.navLinks} aria-label="Research navigation"><Link href="/simulator">Virtual lab</Link><Link href="/">Open instrument ↗</Link></nav></header>
    <section className={styles.hero} aria-labelledby="research-page-title"><div><p className={styles.kicker}>Evidence laboratory / recorded research</p><h1 id="research-page-title">The model has to answer<br />to the measurements.</h1><p>Explore four measured tasks and the completed reference-conditioned confirmation. Compare physical units, sample counts, held-out scope and artifact identities before drawing a conclusion.</p></div><aside className={styles.heroSummary}><strong>Useful metrology.<br />Unresolved structural inference.</strong><p>Healthy reference prediction improved. Compensated localization and adaptive damage sensitivity failed on separate confirmation. The experimental modes remain outside production physical acquisition.</p></aside></section>
    <div className={styles.layout}><nav className={styles.side} aria-label="Evidence sections"><p>INSPECT THE RECORD</p><a href="#fundamental-evidence">01 / Latest confirmation</a><a href="#measured-evidence">02 / Measured tasks</a><a href="#synthetic-evidence">03 / Historical simulation</a><a href="#evidence-scope">04 / Scope of this page</a></nav><div className={styles.content}>
      <FundamentalEvidence />
      <MeasuredDataEvidence />
      <div id="synthetic-evidence" className={styles.historical}><ResearchEvidence /></div>
      <p id="evidence-scope" className={styles.footnote}>These pages show preserved research records and compact, source-checked exports. They work without the acoustic backend. No selection here acquires a waveform, actuates a probe or authorizes a healthy structural release. Interactive ARGUS inspection sessions require the local Python engine.</p>
    </div></div>
  </main>;
}
