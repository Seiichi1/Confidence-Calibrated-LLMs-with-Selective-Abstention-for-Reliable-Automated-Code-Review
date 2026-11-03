# Thesis Project Progress Report

## Confidence-Calibrated LLMs with Selective Abstention for Reliable Automated Code Review

**Reporting date:** 2026-10-27  
**Project status:** Dataset audit, clean LLM-only validation baseline, post-hoc calibration, validation-only conformal abstention, static corroboration, hybrid ablation, operating-policy freeze, raw locked-test inference, frozen-policy test evaluation, record-level statistical uncertainty analysis, project-clustered sensitivity analysis, thesis-ready results/discussion tables, and the first higher-recall candidate study are complete; independent improvement evaluation and final thesis integration remain open.

## 1. Executive summary

This report documents the work completed from the beginning of the Thesis
project through the current protocol-freezing stage. The project studies
whether confidence calibration, selective abstention, and static-analysis
corroboration can make automated code-review decisions more reliable.

The work began as a methodology/proposal project rather than an empirical
paper. The first implementation priority was therefore to verify the supplied
dataset and prevent invalid baseline claims caused by split leakage. PrimeVul
was retained as the provisional primary dataset because it provides
function-level code, binary vulnerability labels, project and commit
provenance, CWE/CVE metadata, and predefined train/validation/test partitions.

The raw PrimeVul partitions were audited without rewriting them. A completed
memory-bounded SimHash scan processed all 224,533 raw records. A second-stage
token 5-gram Jaccard verification and provenance review then identified 2,872
strong approximate cross-partition candidates. Of these, 1,795 were classified
as high-priority provenance overlaps because they shared a project file path or
commit. This does not prove that every candidate is a semantic duplicate, but
it is sufficient to require explicit overlap handling before reporting
leakage-free generalization results.

A conservative derived evaluation manifest was created. It keeps all training
records, excludes 915 flagged validation records, and excludes 780 flagged test
records. The raw JSONL files remain unchanged. A code-only baseline protocol
and manifest-aware local smoke-test runner were also prepared. The selected
primary model is the open-source `Qwen/Qwen2.5-Coder-1.5B-Instruct` checkpoint
pinned to revision `2e1fd39`.

The first complete LLM-only validation baseline was executed on all 23,033
retained validation records. The raw baseline has very low selectivity: it
produces 524 true positives, 22,313 false positives, 19 true negatives, and
177 unparseable responses. Validation-only calibration, abstention,
static-analysis corroboration, and operating-policy selection are complete.
The same pinned model then processed all 24,008 retained test records. The raw
test baseline produces 479 true positives, 23,309 false positives, 8 true
negatives, 2 parseable false negatives, and 210 unparseable responses. The
test result is recorded in `qwen_test_baseline_report.md`; frozen-policy test
evaluation is recorded in `qwen_test_frozen_policy_report.md`.

## 2. Thesis objective and methodological foundation

The chapter defines a binary code-review task:

- **Flag (`1`):** an actionable defect or vulnerability is present.
- **Do not flag (`0`):** no actionable issue is present under the selected
  taxonomy.

The proposed research pipeline is:

1. LLM review of a code region.
2. Extraction of verdict and confidence features.
3. Post-hoc calibration using temperature scaling and Platt scaling.
4. Conformal/selective abstention with a target error rate of 10% and a target
   coverage of 90%.
5. Static-analysis corroboration using categories such as AGREE, DISAGREE,
   and NEUTRAL.
6. Reliability-tier and human-escalation reporting.

The chapter emphasizes that raw LLM confidence may be miscalibrated and that
uncertain decisions should be escalated rather than automatically delivered to
developers. The intended evaluation order is therefore:

```text
dataset and protocol
    -> LLM-only baseline
    -> confidence calibration
    -> selective abstention
    -> static-analysis corroboration
    -> ablations and statistical analysis
```

The chapter's expected outcomes, such as reductions in ECE or improvements in
accepted precision, are hypotheses and success criteria. They are not results
and are not reported as results here.

## 3. Project context and initial decisions

The durable Thesis context was reconstructed from the chapter and the prior
project conversations. The chapter is a methodology/proposal manuscript, not a
completed empirical study. The initial project decisions were:

1. Use binary actionable-defect/vulnerability detection as the first task.
2. Treat PrimeVul as the provisional primary dataset.
3. Follow the experimental order baseline -> calibration -> abstention ->
   corroboration.
4. Keep the final test partition locked and never use its labels to fit
   calibration or select thresholds.
5. Preserve metadata for audit and stratified analysis, but do not place CWE,
   CVE, project, commit, file, or hash metadata in the initial model prompt.
6. Treat all dataset and provenance claims as provisional until reproduced from
   the actual files in the project directory.

The code-only prompt decision is intentionally stricter than the chapter's
generic reference to a CWE-aware prompt. The first baseline must measure what
the model can infer from code rather than allowing provenance or vulnerability
metadata to leak the answer. Metadata can be introduced later only as an
explicitly named ablation.

## 4. Dataset obtained and inspected

The supplied PrimeVul v0.1 data are located under:

`PrimeVul/PrimeVul_v0.1-20260930T034251Z-1-001/PrimeVul_v0.1`

The raw partitions used for the audit are:

| Partition | Records | Vulnerable target=1 | Rate | Invalid/blank records |
|---|---:|---:|---:|---:|
| Train | 175,797 | 4,862 | 2.77% | 0 |
| Validation | 23,948 | 593 | 2.48% | 0 |
| Test | 24,788 | 549 | 2.21% | 0 |
| **Total** | **224,533** | **6,004** | — | **0** |

The raw partitions, rather than the balanced paired files, were selected as the
leakage-audit target. The paired files are contrast sets intended to compare
vulnerable and patched functions; they are not substitutes for the natural
train/validation/test distributions.

The dataset includes function code and fields such as `idx`, `project`,
`commit_id`, `target`, `func`, `func_hash`, CWE, and CVE metadata. File-level
provenance is joined through `file_info.json`. The raw `file_hash` field is
often empty, so file-level checks use the metadata mapping where available.

## 5. Initial schema and provenance audit

The audit verified that all three raw JSONL partitions could be parsed and that
there were no invalid or blank records. It then compared identity and
provenance fields across partitions.

### 5.1 Exact identity checks

- Exact raw-code hashes were unique within each partition and had zero
  cross-partition intersection.
- Whitespace-canonical code hashes were unique within each partition and had
  zero cross-partition intersection.
- `func_hash` had zero cross-partition overlap.
- `idx` values were disjoint across the raw partitions.

These results rule out simple exact duplicate leakage under the tested code
identities. They do not rule out historical revisions, formatting changes,
function variants, or semantically equivalent code.

### 5.2 Provenance overlap checks

Cross-partition provenance overlap was present:

| Relation | Train/validation | Train/test | Validation/test |
|---|---:|---:|---:|
| Shared projects | 162 | 146 | 83 |
| Shared commits | 13 | 14 | 0 |
| Shared file hashes via `file_info.json` | 198 | 164 | 37 |

`file_info.json` coverage was 120,537/175,797 train records, 19,649/23,948
validation records, and 18,878/24,788 test records. The presence of shared
projects or files is not by itself proof of leakage, but it motivated the
near-duplicate and provenance review.

## 6. Approximate near-duplicate scan

### 6.1 Why the first approach was changed

The initial audit approach retained large Python sets and object-heavy
structures alongside the similarity index. It did not complete reliably. The
scan was redesigned as a standalone, memory-bounded process using SQLite for
the index and temporary outputs outside the project directory.

### 6.2 Scan method

The completed scan used:

- Raw train, validation, and test JSONL files only.
- Token-based 64-bit SimHash.
- Four 16-bit bands.
- Minimum function length of 20 tokens.
- A deterministic cap of 256 evenly spaced tokens for SimHash.
- Maximum band bucket size of 256 records.
- Cross-partition candidates only.
- Hamming distance threshold of 8.
- SQLite index outside the project directory.

All 224,533 raw records were processed successfully. The approximate candidate
counts were:

| Pair | Approximate candidates |
|---|---:|
| Train/validation | 3,561,232 |
| Train/test | 3,994,695 |
| Validation/test | 70,936 |

These numbers are triage candidates, not confirmed semantic duplicates.

## 7. Second-stage similarity verification

The approximate candidates were rechecked using token 5-gram Jaccard
similarity. The verification retained the SimHash Hamming-distance gate and
used a Jaccard threshold of at least 0.8. Functions shorter than 20 tokens were
excluded. Large functions were bounded by deterministic token sampling for the
verification calculation.

The completed verification processed all 224,533 records and produced:

| Pair | Verified candidates at Jaccard >= 0.8 |
|---|---:|
| Train/validation | 1,320 |
| Train/test | 1,351 |
| Validation/test | 201 |
| **Total** | **2,872** |

The verified pairs had Jaccard values from 0.8 to 1.0, with a mean of
approximately 0.900. They remain approximate similarity findings; they are not
automatically semantic duplicates or confirmed leakage.

## 8. Provenance and representative-diff review

Each verified pair was joined to raw-record metadata and `file_info.json`.
Representative unified diffs were generated, along with raw and canonical code
hashes, line similarity, project, commit, path, file, CWE, CVE, and label
information.

The verified-pair classifications were:

| Classification | Pairs | Interpretation |
|---|---:|---|
| Same file/path | 1,745 | Same project file path or file identity across partitions |
| Shared commit | 50 | Same commit without the higher-priority same-file/path classification |
| Same project only | 496 | Same project but no same-file/path or shared-commit relation |
| Cross-project | 581 | Different projects with strong approximate code similarity |
| **Total** | **2,872** | — |

No verified pair was an exact raw-code or whitespace-canonical match. The
high-priority group therefore represents likely historical or related code
evolution rather than simple byte-identical duplication.

Representative diffs showed examples such as functions in the same source path
across different commits with small type, comparison, control-flow, or
formatting changes. These examples justify concern about evaluation dependence
on code history, but they do not justify automatic deletion or relabeling.

## 9. High-priority protocol triage

The high-priority set contains 1,795 pairs:

- 1,744 pairs share a project file path across different commits.
- 51 pairs share a commit; one of these also shares a file path.
- 82 pairs cross a vulnerable/non-vulnerable label boundary.
- 1,674 pairs are non-vulnerable/non-vulnerable.
- 39 pairs are vulnerable/vulnerable.

The affected-record counts are:

| Partition | Records in at least one high-priority pair |
|---|---:|
| Train | 1,531 |
| Validation | 915 |
| Test | 780 |
| **Total** | **3,226** |

The high-priority connected-component manifest contains 1,486 components. The
largest component contains seven records. This manifest is suitable for
review or grouped-split construction, but it is not a dataset rewrite.

## 10. Leakage-controlled evaluation manifest

A conservative derived manifest was created to support evaluation without
changing the supplied JSONL files. Its policy is:

- Keep all raw training records available for model fitting/reference.
- Exclude validation records involved in high-priority overlap.
- Exclude test records involved in high-priority overlap.
- Preserve all excluded rows in the raw files.

The resulting roles are:

| Role | Total | Excluded | Retained |
|---|---:|---:|---:|
| Train | 175,797 | 0 | 175,797 |
| Validation/calibration | 23,948 | 915 | 23,033 |
| Locked test | 24,788 | 780 | 24,008 |

Among excluded validation records, 882 were non-vulnerable and 33 vulnerable.
Among excluded test records, 753 were non-vulnerable and 27 vulnerable. This
is a conservative exclusion policy, not proof that every excluded record is
semantically leaked. Any thesis result using this manifest must report the
manifest rule and retained counts.

Three reporting modes are now distinguished:

1. **Supplied-split benchmark:** use the original partitions, but disclose the
   overlap audit and do not call the result leakage-free.
2. **Leakage-controlled evaluation:** use the derived manifest or a documented
   grouped split and report the exclusion rule.
3. **Clean generalization claim:** use a project/file/commit-grouped resplit or
   separately sourced holdout; do not infer this claim from the raw test score.

## 11. Baseline protocol prepared

The baseline is intentionally code-only and binary. The current protocol
specifies:

- System prompt: `You are a security expert that is good at static program
  analysis.`
- User prompt: provide the function code and request exactly `YES` or `NO`.
- No CWE, CVE, project, commit, file, or hash metadata in the initial prompt.
- Temperature: 0.0.
- Seed: 12345.
- Maximum output tokens: 16.
- Maximum input tokens: 4,096, with a 2,048-token retry budget for an OOM case.
- Top-5 token log probabilities requested for confidence extraction.
- Raw JSONL outputs preserved for later calibration and audit.

The manifest-aware runner was dry-run validated on the retained validation and
test partitions. It correctly found 23,033 retained validation records and
24,008 retained test records without making API calls.

The runner does not silently choose a model. It requires an explicit model ID,
which must be logged with every result. This prevents a moving model alias or
an undocumented model change from invalidating comparisons.

## 12. Model decision and current status

The chapter names GPT-4o and DeepSeek-Coder as practical model choices and
specifically recommends pinning model versions to control drift. The user then
selected an open-source local model. Based on the chapter, current hardware,
and the need to retain logits for calibration, the selected primary model is:

> **Qwen/Qwen2.5-Coder-1.5B-Instruct at revision `2e1fd39`.**

The checkpoint is Apache-2.0 licensed and approximately 3.1 GB, which is
compatible with the current machine's approximately 8 GiB RAM and 2 GiB GPU.
The larger 7B model is reserved for a future hardware-upgraded sensitivity
experiment. The revision must remain pinned; the moving `main` branch must not
be used for thesis results.

DeepSeek-Coder remains a possible comparison model, but it is not the primary
run. Newer or larger models may be tested later as sensitivity experiments,
but should not replace the primary model without updating the protocol and
reporting the change explicitly.

The model must provide usable token log probabilities or another documented
confidence signal. Without that, the central calibration and abstention
research questions cannot be evaluated as designed.

## 13. Clean validation baseline result

The clean bounded-input run processed all 23,033 retained validation records in
one non-resumed run. The model predicted `YES` for 22,837 records and `NO` for
19 records; 177 generations were not parseable as either label. The target
distribution was 22,473 records with `target=0` and 560 with `target=1`.

The resulting flag precision was 2.29%, overall accuracy was 2.36% when
unparseable outputs were counted as incorrect, and parseable decision coverage
was 99.23%. The model detected 524 vulnerable records but incorrectly flagged
22,313 non-vulnerable records. These are raw validation-baseline results, not
calibrated or final-test results. Full methods, tables, limitations, and source
artifacts are in `qwen_validation_baseline_report.md`.

## 14. Initial validation-only calibration result

An explicit pairwise YES/NO first-token score was derived for 22,850 records,
with 183 records lacking both tokens in the retained top-five list. A
deterministic stratified 80/20 split of the validation records was used for
temperature and Platt scaling. On the held-out validation portion, temperature
scaling reduced Brier score from 0.6166 to 0.2507, while Platt scaling reduced
it to 0.0226 and ECE to 0.0027. However, Platt scaling assigned every held-out
record a probability below 0.5, so it produced no positive predictions at the
default threshold. This demonstrates that probability calibration and decision
threshold selection must be treated as separate steps under the severe class
imbalance. The detailed analysis is in `qwen_calibration_report.md`.

## 15. Initial validation-only conformal/selective-abstention result

The scored validation records were split into separate model-calibration,
conformal-calibration, and evaluation subsets. Temperature and Platt scaling
were fitted only on the first subset; conformal nonconformity scores were
constructed only on the second. At significance 0.05, temperature scaling
achieved 95.45% prediction-set coverage with 95.12% abstention and 6.73%
accepted precision, while 14.29% of vulnerable evaluation records were
accepted as `YES`. Platt scaling achieved 95.12% prediction-set coverage,
2.78% abstention, and 97.84% accepted precision, but accepted zero vulnerable
records as `YES`. The latter precision is therefore dominated by accepted
negative decisions and cannot be treated as useful vulnerability-detection
recall. Full tables and interpretation are in `qwen_conformal_report.md`.

## 16. Raw locked-test baseline result

The complete retained test inference run processed 24,008 records with no
missing or duplicate record numbers. The model predicted `YES` for 23,788
records, `NO` for 10 records, and produced 210 unparseable responses. Raw flag
precision was 2.01%, parseable decision coverage was 99.13%, and overall
accuracy was 2.03% when unresolved responses were counted as incorrect.

This result confirms that the near-always-YES behavior also appears on the
locked test partition. It is a pre-gating baseline only; the validation-derived
temperature/conformal/static policy has not yet been applied, and no test
labels were used to fit or select it. Full tables and reproducibility paths
are in `qwen_test_baseline_report.md`.

## 17. Locked-test frozen-policy result

The retained test output was matched to the Semgrep artifact with exactly
24,008 records and no missing or unexpected record numbers. The frozen policy
accepted 452 `YES` decisions and abstained on 23,556 records. Accepted-decision
coverage was 1.88%, abstention was 98.12%, accepted-positive precision was
7.96%, and vulnerable-record acceptance was 6.90%.

This is the first complete locked-test result for the selected selective-review
policy. No test labels were used to fit calibration or select the policy. The
full Semgrep counts, policy reasons, metrics, limitations, and checksums are in
`qwen_test_frozen_policy_report.md`.

## 18. Locked-test statistical uncertainty and paired ablations

The final test artifacts were compared on identical records using 5,000
record-level paired bootstrap resamples with seed `20261027`. The frozen hybrid
policy achieved 1.88% positive-alert coverage, 7.96% accepted-positive
precision, and 6.90% positive recall. Its precision was 5.95 percentage points
higher than raw Qwen positive alerts, with a paired 95% interval of +3.60 to
+8.54 points, while positive recall was 84.87 points lower. Compared with the
temperature-conformal-only ablation, precision was 3.31 points higher and
positive recall was 13.79 points lower.

These are record-level uncertainty intervals. They do not establish
project-held-out generalization because PrimeVul projects overlap across the
official partitions. Full point estimates, intervals, paired differences, and
limitations are in `qwen_locked_test_statistics_report.md`.

## 19. Project-clustered locked-test sensitivity

To assess the effect of project concentration, a second uncertainty analysis
resampled whole PrimeVul projects rather than individual records. The 24,008
retained test records formed 217 project clusters; the median cluster size was
36 records, the largest was 3,970 records, and 13 projects contained one
record. Five thousand project-clustered bootstrap resamples were generated
with seed `20261027`.

The point estimates did not change because the predictions and frozen policy
were unchanged. The frozen hybrid had a project-clustered 95% interval of
1.38--2.47% coverage, 5.46--10.85% accepted-positive precision, and
3.84--11.21% positive recall. Its paired precision improvement over raw Qwen
was +5.95 percentage points (95% project-clustered interval +3.48 to +8.75),
while the paired improvement over Semgrep was +1.10 points with an interval
that included zero. This is a project-clustered uncertainty sensitivity, not a
grouped resplit or an unseen-project generalization result.

The thesis-ready report is `qwen_project_clustered_statistics_report.md`.

## 20. Thesis-ready results and discussion tables

The locked-test point estimates, record-level paired-bootstrap intervals,
project-clustered sensitivity intervals, paired differences, frozen-policy
configuration, and thesis-ready interpretation have been assembled in
`thesis_results_discussion_tables.md`. The tables explicitly distinguish
accepted-positive precision from positive recall and state that the frozen
hybrid is a selective review-triage mode rather than a high-recall detector.

The report is ready to use as the quantitative results/discussion foundation.
It does not claim unseen-project generalization and does not use test labels to
select a new policy.

A consolidated master implementation report, including the full chronology,
decision rationale, absolute script and output paths, thesis tables, figure
descriptions, reproducibility controls, and chapter-coverage audit is stored in
`THESIS_MASTER_IMPLEMENTATION_REPORT.md`.

The first higher-recall candidate study is documented in
`qwen_high_recall_improvement_report.md`. A validation-selected alpha `0.50`
corroborated-positive candidate increased exploratory test recall from 6.90%
to 15.13% and coverage from 1.88% to 5.09%, while reducing precision from
7.96% to 6.47%. The original alpha `0.10` policy remains the primary frozen
result.

## 21. Artifacts created

### Dataset audit and similarity

- `work/primevul_audit.py` - schema, counts, missingness, identity, and
  provenance audit.
- `work/near_duplicate_scan.py` - SQLite-backed bounded SimHash scan.
- `work/near_duplicate_verify.py` - token 5-gram Jaccard verification.
- `work/review_near_duplicate_pairs.py` - full verified-pair provenance and
  representative-diff review.
- `work/triage_high_priority_pairs.py` - high-priority summary and target
  mismatch report.

### Derived protocol artifacts

- `work/PRIMEVUL_LEAKAGE_PROTOCOL.md` - reporting modes and leakage policy
  recommendation.
- `work/build_high_priority_group_manifest.py` - connected-component manifest
  builder.
- `work/build_leakage_controlled_manifest.py` - conservative evaluation
  exclusion-manifest builder.
- `work/BASELINE_PROTOCOL.md` - code-only baseline contract.
- `work/run_qwen_sample.py` - deterministic local Qwen smoke-test runner.
- `work/primevul_qwen_colab.ipynb` - self-contained Colab inference notebook.
- `work/primevul_qwen_test_colab.ipynb` - self-contained locked-test Colab
  notebook for `primevul_test.jsonl`.
- `outputs/thesis-codex-context/docs/qwen_validation_baseline_report.md` -
  thesis-ready clean validation baseline report.
- `outputs/thesis-codex-context/docs/qwen_test_baseline_report.md` -
  thesis-ready raw locked-test baseline report.
- `outputs/thesis-codex-context/docs/qwen_test_frozen_policy_report.md` -
  thesis-ready locked-test Semgrep and frozen-policy report.
- `work/run_locked_test_statistics.py` - standard-library record-level paired
  bootstrap and ablation evaluator.
- `outputs/thesis-codex-context/docs/qwen_locked_test_statistics_report.md` -
  thesis-ready statistical uncertainty and paired-ablation report.
- `work/run_project_clustered_statistics.py` - standard-library project-
  clustered locked-test bootstrap and ablation evaluator.
- `outputs/thesis-codex-context/docs/qwen_project_clustered_statistics_report.md`
  - thesis-ready project-clustered sensitivity report.
- `work/run_high_recall_validation_sweep.py` - validation-only higher-recall
  policy sweep.
- `work/apply_high_recall_candidate_policy.py` - applies the validation-selected
  alpha `0.50` candidate without fitting on test labels.
- `outputs/thesis-codex-context/docs/qwen_high_recall_improvement_report.md` -
  exploratory higher-recall candidate comparison.
- `outputs/thesis-codex-context/docs/thesis_results_discussion_tables.md` -
  thesis-ready locked-test results, uncertainty tables, paired comparisons,
  and discussion text.
- `outputs/thesis-codex-context/docs/THESIS_MASTER_IMPLEMENTATION_REPORT.md` -
  consolidated thesis implementation, artifact inventory, tables, figure plan,
  and chapter-experiment coverage audit.
- `outputs/thesis-codex-context/docs/qwen_high_recall_improvement_report.md` -
  validation-selected higher-recall candidate study and exploratory transfer
  comparison.
- `work/fit_qwen_calibration.py` - dependency-free validation-only temperature
  and Platt calibration analysis.
- `outputs/thesis-codex-context/docs/qwen_calibration_report.md` - calibration
  methods, metrics, limitations, and thesis-ready result statement.
- `work/run_conformal_abstention.py` - three-way validation-only split-conformal
  selective-prediction evaluator with positive acceptance metrics.
- `outputs/thesis-codex-context/docs/qwen_conformal_report.md` - conformal
  coverage, abstention, selective precision, positive acceptance, and decision
  record.
- `work/semgrep_primevul_rules.yml` - auditable local C/C++ corroboration rules.
- `work/run_semgrep_corroboration.py` - temporary-file Semgrep adapter that
  joins findings with Qwen predictions without modifying PrimeVul.
- `work/STATIC_CORROBORATION_PROTOCOL.md` - analyzer choice, conservative
  categories, execution contract, and reporting requirements.
- `outputs/thesis-codex-context/docs/qwen_static_corroboration_report.md` -
  full validation-only analyzer counts, corroboration relations, limitations,
  and thesis-ready interpretation.
- `work/evaluate_hybrid_validation.py` - validation-only conformal/static
  ablation evaluator.
- `outputs/thesis-codex-context/docs/qwen_hybrid_validation_report.md` -
  corroborated-positive and exploratory dual-signal gate results.
- `work/select_validation_operating_policy.py` - validation-only cost and
  positive-recall-floor operating-policy sweep.
- `outputs/thesis-codex-context/docs/qwen_policy_sweep_report.md` - candidate
  operating points under explicit false-negative, false-positive, and review
  costs.
- `outputs/thesis-codex-context/docs/THESIS_OPERATING_POLICY.md` - frozen
  validation-derived operating policy for final-test evaluation.
- `work/apply_frozen_policy.py` - applies the frozen policy without fitting on
  test labels.
- `work/LOCKED_TEST_PROTOCOL.md` - locked-test execution and preservation rules.
- `outputs/thesis-codex-context/scripts/` - archived snapshots of the scripts,
  rule pack, and Colab notebook used for the completed experiments.
- `outputs/thesis-codex-context/scripts/SCRIPT_ARCHIVE_MANIFEST.json` - archive
  date, stage mapping, file sizes, and SHA-256 hashes for the code snapshots.
- `outputs/thesis-codex-context/docs/thesis_decisions.md` - durable decision
  log.

Temporary scan, verification, review, triage, and manifest JSON outputs were
written outside the project directory under the local temporary directory.
They should be preserved or copied into an experiment archive before a formal
thesis run.

## 23. What has not been done

The following items remain open and must not be represented as completed
results:

1. Finalize the response-resolution policy for the 177 unparseable generations
   and the 183 records missing an explicit YES/NO pairwise score.
2. Run an optional grouped resplit/unseen-project evaluation if required by the
   thesis design.
3. Run additional prespecified model/calibrator/rule-pack sensitivity
   ablations, if required by the thesis design.
4. Finalize the response-resolution policy for the unparseable and missing
   pairwise-score cases and propagate it consistently through the analysis.
5. Decide whether a grouped resplit should supplement the conservative
   exclusion manifest for the final thesis protocol.

6. Run Semgrep corroboration and apply the frozen and higher-recall policies to
   the completed unseen-project Qwen output.

## 24. New unseen-project evaluation candidate

The next improvement experiment now has a non-destructive project-held-out
candidate. It contains 38,362 raw train records from 400 projects that do not
occur in the official validation or test partitions, including 1,078 vulnerable
records. The manifest is:

`C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\primevul_unseen_project_holdout_manifest.json`

The builder script is:

`C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\build_unseen_project_holdout.py`

The directly uploadable Colab notebook is:

`C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\primevul_qwen_unseen_project_colab.ipynb`

This candidate is independent of model outputs and policy selection. It is not
yet an evaluated result. The next required action is to run the existing pinned
Qwen Colab pipeline with `--data primevul_train.jsonl`,
`--manifest primevul_unseen_project_holdout_manifest.json`,
`--partition unseen_project_holdout`, and `--limit 0`, followed by the same
Semgrep and policy application steps used for validation and test.

The Qwen run has now completed successfully. All 38,362 retained records were
processed exactly once, with 0 missing and 0 duplicate records. The raw model
predicted YES for 38,025 records, NO for 15, and produced 322 unparseable
responses. This corresponds to 1,008 true positives, 37,017 false positives,
14 true negatives, 1 parseable false negative, and 69 unresolved vulnerable
records. Conservative all-record vulnerable recall is 93.51%, but raw YES
precision is only 2.65%, so this is not yet an improvement result. The detailed
run report is:

`C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\qwen_unseen_project_run_report.md`

The remaining step is Semgrep corroboration followed by applying the already
selected alpha `0.10` frozen policy and alpha `0.50` higher-recall candidate.

That step is now complete. Semgrep 1.163.0 found 3,654 static-positive
records, including 327 vulnerable records, with 3,509 Qwen/Semgrep agreements.
The frozen alpha `0.10` policy accepted 1,108 records with 11.01% precision and
11.32% vulnerable recall. The validation-selected alpha `0.50` candidate
accepted 3,071 records with 8.86% precision and 25.23% vulnerable recall. Thus
the candidate produces a project-held-out recall/coverage increase at a
precision cost; it is a mixed improvement rather than dominance. The detailed
report is:

`C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\unseen_project_policy_results_report.md`

Five thousand record-level and 5,000 project-clustered bootstrap resamples were
also completed. The alpha `0.50` minus alpha `0.10` comparison was +5.12
percentage points in coverage (project-clustered 95% interval +4.13 to +6.19),
−2.15 points in accepted-positive precision (−3.45 to −0.89), and +13.91
points in vulnerable recall (+11.29 to +16.57). The comparison remains a
stable trade-off under project clustering.

## 25. Recommended immediate next action

Use the completed project-held-out report and bootstrap intervals in the final
thesis results/discussion tables. Present alpha `0.50` as a mixed
recall/coverage improvement with a precision cost, retain alpha `0.10` as the
primary frozen policy, and keep the official locked-test result separate from
the project-held-out candidate.

