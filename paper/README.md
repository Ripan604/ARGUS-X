# ARGUS NEO IEEE paper package

This directory is a self-contained, upload-ready IEEE conference manuscript for ARGUS NEO and its candidate algorithmic contribution, trust-gated counterfactual dual-control interrogation (TG-CDI).

## Overleaf

1. Create a **Blank Project** in Overleaf.
2. Upload `main.tex`, `nuisance-design-section.tex`, `references.bib`, and this guide into the project root.
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
- `main.pdf` - compiled manuscript, including the research extension.
- `argus-ieee-overleaf.zip` - upload-ready archive containing the source files and this guide.

The manuscript is technical evidence and research positioning, not a patent application, patentability opinion, freedom-to-operate opinion, certification record, or proof of market superiority.
