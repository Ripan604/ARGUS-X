"""Generate dated review evidence and a manuscript table from actual artifacts."""
from __future__ import annotations
import json
from pathlib import Path
from hashlib import sha256
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
result=json.loads((ROOT/'research_results/release_validation_2026_10_07.json').read_text())
if result['metadata']['source_changed_during_run']:
    raise SystemExit('Source changed during validation; do not promote these results')
mismatches=[name for name,digest in result['metadata']['source_sha256'].items()
            if not (ROOT/name).is_file() or sha256((ROOT/name).read_bytes()).hexdigest()!=digest]
if mismatches:
    raise SystemExit('Validation source no longer matches: '+', '.join(mismatches))
suite=ET.parse(ROOT/'output/release/backend-tests.xml').getroot()
tests=sum(int(s.get('tests',0)) for s in suite.iter('testsuite'))
failures=sum(int(s.get('failures',0))+int(s.get('errors',0)) for s in suite.iter('testsuite'))
skipped=sum(int(s.get('skipped',0)) for s in suite.iter('testsuite'))
if failures:
    raise SystemExit('Do not promote a failing backend suite')
frontend=json.loads((ROOT/'output/release/frontend-checks.json').read_text())
if not frontend['all_passed'] or any(sha256((ROOT/name).read_bytes()).hexdigest()!=digest
        for name,digest in frontend['source_sha256'].items()):
    raise SystemExit('Frontend checks failed or source no longer matches')
frontend_count=next(check['tests'] for check in frontend['checks'] if check['task']=='test')
summary={c:{v:{'mean_error_mm':s['localization_error_mm']['mean'],
               'success_20mm_rate':s['success_20mm_rate'],
               'failure_30mm_rate':s['failure_30mm_rate'],
               'abstained_rate':s['abstained_rate'],
               'mean_computation_seconds':s['mean_computation_seconds']}
           for v,s in values.items()} for c,values in result['summary'].items()}
report={'date':'2026-10-07','backend':{'passed':tests-skipped,'skipped':skipped,'failures':failures,'total':tests},
        'frontend':{'tests_passed':frontend_count,'typecheck':'passed','lint':'passed','production_build':'passed'},
        'dependencies':{'next':'16.3.8','torch':'2.6.0+cpu','python':'3.10.11'},
        'synthetic_validation':{'attempted':len(result['runs']),'completed':sum(r['completed'] for r in result['runs']),
            'source_stable':True,'seeds':result['metadata']['seeds'],'steps':result['metadata']['steps'],
            'summary':summary,'paired':result['paired_comparisons'],'risk_paired':result['risk_vs_legacy_paired']},
        'online_dependency_audit':'blocked_pending_explicit_user_permission',
        'physical_accuracy_validated':False,'patent_filed':False,'external_publication_performed':False}
(ROOT/'output/release/readiness-report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
rows=[]
for c,values in summary.items():
    for v,s in values.items():
        label={'legacy_proxy':'Legacy proxy','nuisance_aware':'Nuisance-aware','risk_calibration':'Risk calibration'}[v]
        rows.append(f"{'Nominal' if c=='nominal' else 'Mismatch'} & {label} & {s['mean_error_mm']:.2f} & {s['success_20mm_rate']:.3f} \\\\")
tex=r'''\subsection{7 October Current-Source Engineering Validation}
The fixed release protocol used seeds 64000--64007, six observations, twelve
shared diagnostic opportunities, three policies, and nominal and mismatched/noisy
conditions. All 48 runs completed; the pre/post source hashes agree and match the
reviewed backend files. This is a small synthetic engineering check, not a powered
physical trial. Table~\ref{tab:october-release} retains every outcome.
\begin{table}[t]
\caption{October Release Synthetic Check (Eight Seeds per Condition/Policy)}
\label{tab:october-release}
\centering\scriptsize
\begin{tabular}{@{}llrr@{}}\toprule
Condition & Policy & Mean error (mm) & Success $\leq20$ mm \\
\midrule
'''+ '\n'.join(rows)+r'''
\bottomrule\end{tabular}
\end{table}
Nuisance-aware error advantages over legacy were 1.74 mm with paired bootstrap
95\% interval $[-6.78,9.50]$ mm nominally and 45.59 mm with interval
$[-22.85,107.10]$ mm under mismatch. Risk-controller advantages were 2.69 mm
with interval $[-0.78,7.59]$ mm and 46.24 mm with interval $[-10.48,112.27]$ mm,
respectively. Every interval crosses zero. All policies succeeded within 20 mm
in 6/8 nominal cases. Under mismatch, legacy succeeded in 0/8 and both optional
policies in 1/8. Mismatch failures remain substantial; the software guards do not
establish physical robustness. Timing on the shared workstation is descriptive.
The artifact is \path{research_results/release_validation_2026_10_07.json}; the
fixed protocol is \path{docs/VALIDATION_PROTOCOL_2026_10_07.md}. No seed filtering,
post-result tuning, physical relabeling or superiority claim is made.
'''
(ROOT/'paper/release-validation-section.tex').write_text(tex,encoding='utf-8')
paper=ROOT/'paper/main.tex'
text=paper.read_text(encoding='utf-8')
marker='\\textbf{Current-source evaluation reference.}'
if marker in text:
    start=text.index(marker)
    end=text.index('\n',start)
    text=text[:start]+'\\input{release-validation-section.tex}'+text[end:]
elif '\\input{release-validation-section.tex}' not in text:
    raise SystemExit('Could not identify the manuscript release section')
paper.write_text(text,encoding='utf-8')
print('Evidence source matches current code; backend',tests-skipped,'passed,',skipped,'skipped; synthetic',len(result['runs']),'runs')
