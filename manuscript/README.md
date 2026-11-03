# Thesis research-paper package

This directory contains the empirical research paper prepared in the Springer Nature `sn-jnl` style from the supplied chapter draft, Scopus export, and completed Thesis experiments.

## Main deliverables

- `main.pdf` — compiled 15-page manuscript for supervisor review.
- `main.tex` — editable LaTeX manuscript source.
- `paper_references.bib` — clean bibliography containing the references cited in the manuscript.
- `references.bib` — retained full BibTeX export from the supplied Scopus file, including the original export records and added foundational references.
- `scopus_export.csv` — copied 77-record Scopus export used for the literature-review corpus.
- `figures/pipeline.svg` — standalone pipeline figure.
- `figures/dataset_flow.svg` — standalone leakage-control figure.
- `figures/locked_test_comparison.svg` — standalone locked-test comparison figure.
- `figures/holdout_tradeoff.svg` — standalone project-held-out trade-off figure.
- `figures/operational_impact.svg` — alert-load and accepted-precision comparison.
- `figures/hybrid_funnel.svg` — calibrated/rule intersection funnel.
- `figures/precision_robustness.svg` — bootstrap precision-gain intervals.

The PDF embeds six TikZ figures so that the submitted manuscript does not depend on external image files: the leakage-control workflow, operational alert-burden comparison, locked-test comparison, hybrid corroboration funnel, bootstrap robustness intervals, and project-held-out operating-point trade-off. The standalone SVGs are retained for later editing or use in a conference/paper layout.

When mirrored to the public GitHub repository, the compiled PDF and Scopus CSV are stored as numbered gzip parts because of upload limits; the repository's `manuscript/README.md` gives the exact reconstruction commands.

## Empirical scope

The manuscript reports the completed PrimeVul leakage audit, Qwen2.5-Coder-1.5B-Instruct baseline, validation-only temperature calibration, conformal-style selective gate, Semgrep corroboration, locked-test results, bootstrap uncertainty intervals, and project-held-out analysis. The claims are deliberately limited to selective review triage; the paper does not claim autonomous high-recall vulnerability detection.

## Rebuild

From this directory:

```text
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

The raw PrimeVul JSONL partitions and the experiment outputs remain outside this manuscript package and are not modified by the paper build.

