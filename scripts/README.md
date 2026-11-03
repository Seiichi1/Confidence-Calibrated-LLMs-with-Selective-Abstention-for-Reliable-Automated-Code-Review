# Thesis experiment-code archive

This directory stores snapshots of the scripts and rule/notebook artifacts used
for the completed Thesis experiments as of 2026-10-26. The working source files
remain under `work/`; these copies are preserved so the thesis can cite the
exact implementation associated with each report.

## Experiment mapping

| Thesis stage | Archived implementation | Associated report/protocol |
|---|---|---|
| PrimeVul schema and provenance audit | `primevul_audit.py` | `thesis_progress_report.md` |
| Approximate near-duplicate scan | `near_duplicate_scan.py` | `thesis_progress_report.md` |
| Similarity verification | `near_duplicate_verify.py` | `thesis_progress_report.md` |
| Provenance and representative-diff review | `review_near_duplicate_pairs.py` | `thesis_progress_report.md` |
| High-priority pair triage | `triage_high_priority_pairs.py` | `thesis_progress_report.md` |
| Connected-component manifest | `build_high_priority_group_manifest.py` | `thesis_progress_report.md` |
| Leakage-controlled manifest | `build_leakage_controlled_manifest.py` | `thesis_progress_report.md` |
| Qwen smoke/full inference | `run_qwen_sample.py`, `run_qwen_colab.py`, `primevul_qwen_colab.ipynb`, `primevul_qwen_test_colab.ipynb` | `qwen_validation_baseline_report.md`, `LOCKED_TEST_PROTOCOL.md` |
| Confidence calibration | `fit_qwen_calibration.py` | `qwen_calibration_report.md` |
| Conformal selective prediction | `run_conformal_abstention.py` | `qwen_conformal_report.md` |
| Frozen-policy application | `apply_frozen_policy.py` | `THESIS_OPERATING_POLICY.md`, `LOCKED_TEST_PROTOCOL.md` |
| Static corroboration | `run_semgrep_corroboration.py`, `semgrep_primevul_rules.yml` | `STATIC_CORROBORATION_PROTOCOL.md`, `qwen_static_corroboration_report.md` |
| Hybrid validation ablation | `evaluate_hybrid_validation.py` | `qwen_hybrid_validation_report.md` |
| Operating-policy cost sweep | `select_validation_operating_policy.py` | `qwen_policy_sweep_report.md` |
| Locked-test statistical uncertainty and paired ablations | `run_locked_test_statistics.py` | `qwen_locked_test_statistics_report.md` |
| Project-clustered locked-test sensitivity | `run_project_clustered_statistics.py` | `qwen_project_clustered_statistics_report.md` |
| Higher-recall validation sweep | `run_high_recall_validation_sweep.py` | `qwen_high_recall_improvement_report.md` |
| Higher-recall candidate application | `apply_high_recall_candidate_policy.py` | `qwen_high_recall_improvement_report.md` |
| Unseen-project holdout construction | `build_unseen_project_holdout.py` | `unseen_project_holdout_protocol.md` |
| Unseen-project Qwen inference | `primevul_qwen_unseen_project_colab.ipynb` | `unseen_project_holdout_protocol.md` |
| Unseen-project Semgrep corroboration | `primevul_semgrep_unseen_project_colab.ipynb` | `unseen_project_holdout_protocol.md` |
| Unseen-project paired uncertainty statistics | `run_unseen_policy_comparison_statistics.py` | `unseen_project_policy_results_report.md` |
| Phoenix paired-reference evaluation | Released Phoenix `scripts/evaluate.py` used outside the project directory | `sota_reference_and_matched_baseline_report.md` |
| Matched larger open-source baseline | `primevul_qwen14b_locked_test_colab.ipynb`, `evaluate_qwen_matched_baseline.py` | `sota_reference_and_matched_baseline_report.md` |

## Reproducibility note

The archived files are snapshots, not independent forks. When rerunning an
experiment, use the matching working script under `work/`, record the model,
analyzer/rule versions, input paths, seed, and output artifact, and compare the
archived snapshot before claiming exact reproducibility.


