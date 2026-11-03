# Unseen-Project Policy Evaluation Report

## Status

Complete. The unseen-project Qwen output was joined with the Semgrep result and
evaluated under both preselected policies. No model, calibration parameter,
conformal threshold, or policy was fitted or selected using the candidate
labels.

## Input artifacts

| Artifact | Absolute path |
|---|---|
| Qwen output | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\qwen_unseen_project_results.jsonl` |
| Semgrep output | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\semgrep_unseen_project_results.json` |
| Frozen-policy output | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\frozen_unseen_project_policy_results.json` |
| Higher-recall output | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\high_recall_unseen_project_policy_results.json` |
| Validation conformal artifact | `C:\Users\rehan\AppData\Local\Temp\thesis_qwen_conformal_artifacts.json` |
| Policy scripts | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\apply_frozen_policy.py`; `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\apply_high_recall_candidate_policy.py` |

## Semgrep corroboration

Semgrep Community Edition version `1.163.0` processed all 38,362 records in
batches of 512 using the existing local C/C++ rule pack. The raw dataset was
not modified and temporary source files were removed after scanning.

| Quantity | Count |
|---|---:|
| Records scanned | 38,362 |
| Records with a static finding | 3,654 |
| Records with no finding | 34,708 |
| Static true positives | 327 |
| Static positive precision | 8.95% |
| Static positive recall | 30.33% |
| Qwen/Semgrep `AGREE` | 3,509 |
| Qwen/Semgrep `DISAGREE` | 1 |
| `NEUTRAL` | 34,852 |

Absence of a Semgrep finding remains neutral and is not treated as evidence of
absence of a vulnerability.

## Project-held-out policy results

The candidate contains 38,362 records, including 1,078 vulnerable records. An
accepted-positive precision is calculated only among records for which the
policy emits `YES`; abstentions are excluded from that denominator. Coverage is
the fraction of all candidate records receiving `YES`. Vulnerable-record recall
is accepted vulnerable records divided by all 1,078 vulnerable records.

| Policy | Alpha | Accepted YES | Abstentions | Coverage | TP | FP | Accepted-positive precision | Vulnerable recall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Frozen temperature + conformal + Semgrep gate | 0.10 | 1,108 | 37,254 | 2.89% | 122 | 986 | 11.01% | 11.32% |
| Higher-recall validation-selected candidate | 0.50 | 3,071 | 35,291 | 8.01% | 272 | 2,799 | 8.86% | 25.23% |

The higher-recall candidate therefore changes the unseen-project result by:

- coverage: `+5.12` percentage points;
- accepted-positive precision: `-2.15` percentage points;
- vulnerable recall: `+13.92` percentage points;
- true positives: `+150`;
- false positives: `+1,813`.

## Comparison with raw Qwen and official test results

| Evaluation | Policy | Coverage | Accepted-positive precision | Vulnerable recall |
|---|---|---:|---:|---:|
| Unseen-project candidate | Raw Qwen YES | 99.12% | 2.65% | 93.51% |
| Unseen-project candidate | Frozen alpha 0.10 | 2.89% | 11.01% | 11.32% |
| Unseen-project candidate | Higher-recall alpha 0.50 | 8.01% | 8.86% | 25.23% |
| Official locked test | Frozen alpha 0.10 | 1.88% | 7.96% | 6.90% |
| Official locked test | Exploratory alpha 0.50 | 5.09% | 6.47% | 15.13% |

The raw Qwen row is not directly comparable to the selective policies because
it counts nearly every record as a positive alert. Selective-policy precision
is prevalence-sensitive, and the unseen-project candidate has 2.81% vulnerable
prevalence versus approximately 2.17% in the retained official test. The
project-held-out results should therefore be interpreted primarily as an
independent generalization check and as a precision–recall trade-off, not as a
claim of universal superiority over the official test result.

## Thesis interpretation

The higher-recall candidate generalizes in the intended direction: on projects
not present in official validation or test, it increases vulnerable-record
recall from 11.32% to 25.23% and coverage from 2.89% to 8.00%, at the cost of
reducing accepted-positive precision from 11.01% to 8.86%. This is a mixed
improvement, not a dominance result.

The original alpha `0.10` policy remains the frozen primary policy. The alpha
`0.50` policy can be reported as a validation-selected higher-recall operating
point supported by an independent project-held-out evaluation. It should not
be described as high-recall autonomous detection: 74.77% of vulnerable records
remain unaccepted under the candidate, and the majority of accepted alerts are
false positives.

The candidate result is stronger evidence than the earlier exploratory alpha
`0.50` application to the existing official test output because the candidate
uses projects disjoint from official validation and test. It still does not
replace the locked official test, which remains the primary result under the
original protocol.

## Uncertainty intervals

Five thousand record-level paired bootstrap resamples and five thousand
whole-project clustered resamples were run. The direct comparison below is
candidate alpha `0.50` minus frozen alpha `0.10`; positive values indicate a
higher value for the higher-recall candidate.

| Difference | Point estimate | Record-level 95% interval | Project-clustered 95% interval |
|---|---:|---:|---:|
| Coverage | +5.12 pp | +4.90 to +5.34 pp | +4.13 to +6.19 pp |
| Accepted-positive precision | −2.15 pp | −3.61 to −0.78 pp | −3.45 to −0.89 pp |
| Vulnerable recall | +13.91 pp | +11.89 to +15.99 pp | +11.29 to +16.57 pp |

The recall and coverage increases remain positive under both bootstrap units,
while the precision decrease remains negative. This supports describing alpha
`0.50` as a statistically stable operating-point trade-off on the candidate,
not as an across-the-board improvement.

Bootstrap artifacts:

- `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\unseen_policy_comparison_statistics.json`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\unseen_frozen_record_statistics_5000.json`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\unseen_high_recall_record_statistics_5000.json`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\unseen_frozen_project_statistics_5000.json`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\unseen_high_recall_project_statistics_5000.json`

The direct comparison implementation is:

`C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\run_unseen_policy_comparison_statistics.py`

