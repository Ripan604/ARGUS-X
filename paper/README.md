# ARGUS NEO IEEE paper package

This directory is a self-contained, upload-ready IEEE conference manuscript for ARGUS NEO and its candidate algorithmic contribution, trust-gated counterfactual dual-control interrogation (TG-CDI).

The 7 October 2026 revision corrects runtime/claim mismatches, adds input,
network and evidence hardening, and distinguishes the dated release validation
from earlier source versions. See `../docs/PUBLICATION_READINESS.md` and
`../docs/RELEASE_READINESS_REPORT.md` for the supported scope and actual checks.

The later acquisition-v2 extension is in `probe-v2-section.tex`. It documents
concurrent firmware, the physical time-origin gate, 470 backend/30 frontend tests
and a source-frozen 1,920-run scalar comparison against strong A/D baselines.
D-optimal superiority is inconclusive and doubled-noise coverage is poor.
Read `../docs/PROBE_V2_RELEASE_REVIEW.md` for the current evidence boundary.

The 8 October measured-data addition is `measured-data-section.tex`. It reports
four distinct tasks using actual published recordings: whole-plate audio
screening, a previously seen transient-source localization reanalysis, native
ultrasonic offline path replay, and cross-panel operator-quality classification.
It retains failed operational decisions and negative transfer findings. The
measured replay does not validate ARGUS's physical apparatus or establish novelty.

That section also records the healthy-reference transport development failure,
its archived one-percent policy and subsequent bounded five-percent policy,
negative localization results, and the unsupported whole-trajectory reference
gate in the initial three-bank development check. A later public retry recovered
all 29 planned confirmation banks after temporary HTTP 403 failures. Confirmation
completed on 9 October 2026; the result filename retains the 8 October protocol
tag. Its 19 calibration and ten confirmation banks yielded 864 trajectories and 216 controller-bound
calibrations; transported adaptive localization errors exceeded the raw variant,
and all adaptive variants detected none of the eight mass/temperature conditions.
Their zero false alarms on two unique healthy banks does not establish useful
inspection or field coverage. Each transported random-order variant had ten
early alerts among 128 damage order replays, a 7.8125% mean after collapsing
orders within eight physical conditions; these are not independent physical
detections, and no variant had a final-budget alert. The same plate and correlated cooling blocks
still limit interpretation; no production activation followed. Its three additional
primary references are included in `references.bib`; no extra upload file or
external figure is required.

The 20 September 2026 revision distinguished historical benchmarks from the
current 24-run synthetic risk-controller evaluation, reports negative and
inconclusive results, and narrows implementation and patent-support claims.
It is a working manuscript, not a submission-ready efficacy or novelty claim.
See `../docs/AUDIT_REMEDIATION.md` and `../docs/CURRENT_INVENTION_DISCLOSURE.md`.

## Overleaf

1. Create a **Blank Project** in Overleaf.
2. Upload `main.tex`, `nuisance-design-section.tex`, `release-validation-section.tex`, `probe-v2-section.tex`, `measured-data-section.tex`, `references.bib`, and this guide into the project root.
3. In **Menu > Compiler**, select **pdfLaTeX**.
4. Click **Recompile**. Overleaf will run BibTeX and the cross-reference passes.

All architecture diagrams and benchmark plots are generated in LaTeX with TikZ/PGFPlots. There are no external image dependencies.

## Local compile

With `latexmk`:

```powershell
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

Or manually:

```powershell
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

## Before submission

- Replace the author block with the full author list, affiliation, ORCID/email, and funding information.
- Check the venue's page limit, anonymity rule, copyright notice, and required IEEE template version.
- For double-blind review, remove author and repository-identifying details.
- Do not present simulated results as physical validation. The paper explicitly separates the 30-case baseline from the small NEO engineering diagnostics.
- Re-run all benchmarks after algorithm changes and update tables, plots, sample sizes, seeds, and limitations together.
- Obtain a professional claim-specific patent search before making patentability assertions or public disclosure decisions.

## Files

- `main.tex` - detailed IEEE manuscript with TG-CDI equations and pseudocode, competitor positioning, a claim-oriented technical map, diagrams, observed results, limitations, and appendices.
- `references.bib` - primary scholarly references, reviewed patent documents, official product sources, and the LMSD dataset record.
- `nuisance-design-section.tex` - researched arrival-time information extension, numerical assumptions, and the 80-run paired evaluation (including negative and inconclusive findings).
- `measured-data-section.tex` - four measured-source assessments, physical grouping, task/metric units, genuine results, and negative operational findings; no external figures required.
- `main.pdf` - compiled manuscript, including the research extension.
- `argus-ieee-overleaf.zip` - upload-ready archive containing the source files and this guide.

The manuscript is technical evidence and research positioning, not a patent application, patentability opinion, freedom-to-operate opinion, certification record, or proof of market superiority.
