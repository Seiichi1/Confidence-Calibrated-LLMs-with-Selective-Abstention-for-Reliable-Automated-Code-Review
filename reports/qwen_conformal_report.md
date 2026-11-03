# Qwen Validation-Only Conformal Selective-Prediction Report

**Stage:** Split-conformal abstention on the clean validation baseline  
**Date:** 2026-10-26  
**Model:** `Qwen/Qwen2.5-Coder-1.5B-Instruct`, pinned revision `2e1fd39`  
**Partition:** Retained validation only; the retained test partition was not read

## 1. Purpose

This experiment evaluates whether calibrated Qwen scores can support a selective
prediction gate. The gate emits a decision only when the conformal prediction
set is a singleton; it abstains when the set contains both labels or no label.
The experiment is a validation-stage method check. It does not select or report
a final test threshold.

The label mapping is unchanged throughout the Thesis protocol:

- `target=1` means an actionable vulnerability is present and corresponds to
  `YES` / flag.
- `target=0` means no actionable vulnerability is present and corresponds to
  `NO` / do not flag.

## 2. Data and split design

The input was the completed clean validation output with 23,033 records. An
explicit pairwise score was available for 22,850 records; 183 records did not
contain both `YES` and `NO` in the retained top-five token probabilities and
were excluded from score-based fitting and evaluated as unresolved/missing.

The 22,850 scored records were split deterministically and stratified by target
using seed `12345`:

| Role | Records | `target=0` | `target=1` |
|---|---:|---:|---:|
| Model-calibration split | 13,709 | 13,395 | 314 |
| Conformal-calibration split | 4,570 | 4,465 | 105 |
| Evaluation split | 4,571 | 4,466 | 105 |

The model-calibration split fitted temperature and Platt parameters. The
conformal-calibration split constructed nonconformity scores. The evaluation
split was used only for the reported validation-stage measurements.

## 3. Method

The base score is

`p_pair = p(YES) / (p(YES) + p(NO))`,

where the probabilities are the first-token top-five probabilities retained by
the inference run. The nonconformity score for a candidate label is one minus
the calibrated probability assigned to that label. A label enters the
prediction set when its split-conformal p-value is greater than the selected
significance level. Only singleton prediction sets are accepted as decisions.

Temperature scaling used `T=445.683640902898`. Platt scaling used
`a=1.5575933849848282` and `b=-6.008092902979631`.

The coverage statement is limited to marginal prediction-set coverage under
the exchangeability assumptions of split conformal prediction. It is not a
claim that all vulnerable records are covered, nor is accepted precision a
substitute for positive-class recall.

## 4. Results

### 4.1 Temperature scaling

| Significance | Set coverage | Abstention | Accepted records | Accepted precision | Accepted `YES` | Vulnerable records accepted as `YES` |
|---:|---:|---:|---:|---:|---:|---:|
| 0.01 | 99.04% | 98.99% | 46 | 4.35% | 46 | 1.90% |
| 0.05 | 95.45% | 95.12% | 223 | 6.73% | 223 | 14.29% |
| 0.10 | 90.07% | 89.43% | 483 | 6.00% | 483 | 27.62% |
| 0.20 | 80.20% | 79.37% | 943 | 4.03% | 943 | 36.19% |
| 0.30 | 69.70% | 68.50% | 1,440 | 3.82% | 1,440 | 52.38% |
| 0.50 | 50.49% | 48.76% | 2,342 | 3.37% | 2,342 | 75.24% |

Temperature scaling generated mostly two-label prediction sets and accepted
singleton `YES` decisions. Its accepted precision remained low because the
underlying model ranked almost all records toward `YES`.

### 4.2 Platt scaling

| Significance | Set coverage | Abstention | Accepted records | Accepted precision | Accepted `YES` | Vulnerable records accepted as `YES` |
|---:|---:|---:|---:|---:|---:|---:|
| 0.01 | 98.64% | 25.84% | 3,390 | 98.17% | 0 | 0.00% |
| 0.05 | 95.12% | 2.78% | 4,444 | 97.84% | 0 | 0.00% |
| 0.10 | 90.79% | 7.37% | 4,234 | 98.02% | 0 | 0.00% |
| 0.20 | 80.25% | 18.20% | 3,739 | 98.10% | 0 | 0.00% |
| 0.30 | 69.83% | 29.01% | 3,245 | 98.37% | 0 | 0.00% |
| 0.50 | 50.40% | 48.98% | 2,332 | 98.80% | 0 | 0.00% |

The high Platt accepted precision is dominated by accepted `NO` decisions. No
vulnerable evaluation record was accepted as `YES` at any tested significance
level. Therefore this is not an operationally useful vulnerability detector,
despite its high overall accepted precision.

## 5. Interpretation and decision

The conformal implementation is complete as a validation-stage mechanism, but
neither fitted calibrator is ready to be frozen as the final operating policy.
Temperature scaling exposes the expected coverage/abstention trade-off but has
poor precision. Platt scaling produces excellent negative-class selectivity but
zero positive-class acceptance, which would make it unsuitable for a security
screening workflow if used alone.

The result supports three methodological decisions:

1. Report prediction-set coverage, abstention, accepted precision, and positive
   acceptance/recall together.
2. Do not choose a final threshold from these validation results alone without
   defining the operational cost of missed vulnerabilities and false alarms.
3. Continue to static-analysis corroboration and compare whether analyzer
   evidence can recover useful positive decisions among uncertain or abstained
   cases.

These results remain validation-stage evidence. They do not establish final
test performance or prove that the model generalizes without leakage.

## 6. Reproducibility

| Item | Value |
|---|---|
| Script | [run_conformal_abstention.py](C:/Users/rehan/Documents/Codex/2026-10-05/i-want-all-the-chats-and/work/run_conformal_abstention.py) |
| Archived script snapshot | [run_conformal_abstention.py](C:/Users/rehan/Documents/Codex/2026-10-05/i-want-all-the-chats-and/outputs/thesis-codex-context/scripts/run_conformal_abstention.py) |
| Input | `C:/Users/rehan/OneDrive/Desktop/Thesis/implementation/qwen_valid_results_fixed.jsonl` |
| Artifact | `C:/Users/rehan/AppData/Local/Temp/thesis_qwen_conformal_artifacts.json` |
| Seed | `12345` |
| Final test used | No |


