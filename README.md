# Confidence-Calibrated LLM Code-Review Triage — Reproducibility Bundle

This bundle contains the non-sensitive artifacts required to inspect and reproduce the reported Thesis analysis. It includes the manuscript, source scripts, Colab notebooks, model outputs, Semgrep outputs, leakage/provenance manifests, statistical summaries, and the detailed research reports.

## Included evidence

### `manuscript/`

- `main.pdf`: compiled research paper.
- `main.tex`: editable Springer Nature LaTeX source.
- `paper_references.bib`: clean bibliography used by the paper.
- `references.bib` and `scopus_export.csv`: retained literature-search exports.
- `figures/`: standalone SVG figures.

### `scripts/`

The archived Python scripts and Colab notebooks cover the PrimeVul audit, SimHash retrieval, near-duplicate verification, provenance review, Qwen inference, calibration, conformal abstention, policy selection, Semgrep corroboration, and statistical analysis. `SCRIPT_ARCHIVE_MANIFEST.json` records the archived script inventory.

### `experiment_outputs/`

These are the generated results used to support the paper:

- Qwen validation, locked-test, smoke-test, and unseen-project predictions.
- Semgrep test and unseen-project findings.
- Frozen-policy and higher-recall policy outputs.
- Validation policy sweeps and locked-test/project-clustered statistics.
- Verified near-duplicate/provenance review report.
- Project-held-out manifest.

### `dataset_reference/`

The leakage-controlled PrimeVul manifest is included. The raw PrimeVul JSONL files are intentionally not copied into this repository bundle; they remain obtainable from the original dataset source and are protected from accidental modification.

## Main reported settings

- Model: `Qwen/Qwen2.5-Coder-1.5B-Instruct`, Hugging Face revision `2e1fd39`.
- Seed: `12345`.
- Calibration: validation-only temperature scaling.
- Primary conformal significance level: `alpha=0.10`.
- Hybrid gate: conformal prediction set exactly `[1]` and at least one Semgrep finding.
- Semgrep Community Edition: `1.163.0`.
- Official retained test population: `24,008` records.
- Primary locked-test result: precision `7.96%`, coverage `1.88%`, vulnerable-record recall `6.90%`.

## Verification order

1. Read `reports/THESIS_MASTER_IMPLEMENTATION_REPORT.md` and `reports/thesis_results_discussion_tables.md`.
2. Inspect `dataset_reference/thesis_primevul_leakage_controlled_manifest.json`.
3. Review the corresponding scripts in `scripts/`.
4. Compare the JSON/JSONL outputs in `experiment_outputs/` with the report tables.
5. Rebuild the paper from `manuscript/main.tex` using the Springer class and bibliography files.

## Exclusions

The raw PrimeVul dataset, the downloaded 240 MB archive, temporary SQLite indexes, temporary render-check images, model weights, API keys, and private chat history are excluded. Their omission is deliberate: the bundle is intended to be auditable without redistributing the dataset or credentials.

