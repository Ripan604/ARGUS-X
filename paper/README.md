# ARGUS IEEE paper package

This folder is a self-contained IEEE conference-paper project for Overleaf.

## Overleaf

1. Create a **Blank Project** in Overleaf.
2. Upload `main.tex` and `references.bib` into the project root.
3. In **Menu → Compiler**, select **pdfLaTeX**.
4. Click **Recompile**. Overleaf runs BibTeX automatically.

All diagrams and benchmark plots are generated inside LaTeX with TikZ/PGFPlots, so there are no missing image files.

## Local compile

From this folder:

```powershell
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

Clean auxiliary files while retaining the PDF:

```powershell
latexmk -c
```

## Before submission

- Replace the author and affiliation block near the top of `main.tex` with the complete author list, institutional affiliation, and email.
- Check the target conference's page limit, anonymity rule, copyright notice, and required IEEE template version.
- If the venue is double-blind, replace identifying repository, author, and acknowledgment details before submission.
- Do not present the synthetic benchmark as physical validation. The paper intentionally states that localization-error confidence intervals cross zero and that the real-data scenario split exposes a sim-to-real gap.
- Re-run benchmarks after algorithm changes and update every result table and embedded plot together.

## Files

- `main.tex` — complete detailed manuscript, inline figures, equations, algorithm, results, limitations, data-collection plan, and appendices.
- `references.bib` — BibTeX database using primary scholarly sources and the official LMSD dataset DOI.
- `argus-ieee-overleaf.zip` — upload-ready archive generated from the two source files and this guide.
