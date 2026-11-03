# Higher-Recall Policy Improvement Study

**Date:** 2026-10-27  
**Stage:** Validation-selected candidate policy and exploratory test transfer  
**Status:** Complete as an exploratory comparison; original frozen policy remains authoritative

## 1. Objective

The frozen hybrid policy achieved high accepted-positive precision but only
6.90% positive recall on the locked test partition. This study evaluates a
less conservative policy selected from validation data with an explicit higher-
recall requirement.

The original frozen policy was not changed. The candidate result is reported as
an additional operating point and must not be presented as a replacement final
policy without a new pre-registered locked evaluation.

## 2. Candidate-selection protocol

Candidate selection used retained validation data only. No test labels were
used to choose the candidate.

The validation sweep evaluated temperature-scaled conformal policies with and
without a Semgrep corroborated-positive gate over alpha values from 0.01 to
0.90. The selection assumptions were:

- minimum positive-recall floor: 20%;
- false-negative cost: 20;
- false-positive cost: 1;
- manual-review cost: 0.5;
- selection criterion: lowest normalized cost among candidates satisfying the
  recall floor;
- static absence remained neutral rather than proof of safety.

The selected candidate was:

```text
temperature scaling + split conformal alpha=0.50
+ Semgrep corroborated-positive gate
```

### Table 1. Validation candidate-selection result

| Candidate | Alpha | Coverage | Accepted-positive precision | Positive recall | Accepted records | Normalized cost |
|---|---:|---:|---:|---:|---:|---:|
| Selected temperature + corroborated positive | 0.50 | 6.78% | 6.77% | 20.00% | 310 | 0.5293 |
| Temperature + corroborated positive | 0.60 | 7.18% | 6.71% | 20.95% | 328 | 0.5311 |
| Temperature conformal-only | 0.10 | 10.57% | 6.00% | 27.62% | 483 | 0.5465 |
| Temperature conformal-only | 0.20 | 20.63% | 4.03% | 36.19% | 943 | 0.5948 |

Alpha `0.50` was selected because it was the lowest-cost candidate satisfying
the 20% validation positive-recall floor under the declared cost assumptions.
The selection was not based on the candidate's test result.

## 3. Candidate application to the retained test output

The selected candidate was applied to the existing retained test Qwen and
Semgrep artifacts. Test labels were read only after candidate selection for
metric calculation. The original frozen alpha `0.10` result remains the main
locked-test result.

### Table 2. Frozen policy versus higher-recall candidate

| Method | Accepted alerts | True positives | False positives | Abstentions | Coverage | Accepted-positive precision | Positive recall |
|---|---:|---:|---:|---:|---:|---:|---:|
| Original frozen hybrid, alpha=0.10 | 452 | 36 | 416 | 23,556 | 1.88% | 7.96% | 6.90% |
| Higher-recall candidate, alpha=0.50 | 1,221 | 79 | 1,142 | 22,787 | 5.09% | 6.47% | 15.13% |

### Table 3. Candidate change relative to the original frozen policy

| Metric | Change |
|---|---:|
| Coverage | +3.20 percentage points |
| Accepted-positive precision | −1.49 percentage points |
| Positive recall | +8.24 percentage points |
| Accepted true positives | +43 records |
| Accepted false positives | +726 records |

## 4. Interpretation

The candidate improves recall and coverage but does not improve every metric.
It identifies 79 vulnerable records instead of 36 and increases the fraction
of the test set receiving an automated positive alert. The cost is a modest
point-precision reduction and a substantially larger false-alert count.

This is the expected operating trade-off for a selective detector. The result
shows that the original policy was too conservative for a recall-oriented
objective, but it does not show that the candidate is globally superior.

The appropriate claim is:

> A validation-selected higher-recall operating point increased locked-test
> vulnerable-record acceptance from 6.90% to 15.13% and coverage from 1.88% to
> 5.09%, while reducing accepted-positive precision from 7.96% to 6.47%.

## 5. Reporting boundary

- The original alpha `0.10` hybrid remains the frozen primary result.
- The alpha `0.50` result is an exploratory candidate transfer because the
  supplied test partition has already been used for the primary evaluation.
- The candidate was selected without test labels, but the test result is not a
  new independent test because it uses the same retained partition.
- No conclusion of universal improvement should be drawn from this one
  operating point.
- A final higher-recall claim should use a new untouched or grouped test
  partition, especially if more candidates are compared.

## 6. Recommended next improvement experiment

Use the validation-only sweep to pre-register one higher-recall policy family,
then evaluate it on a new project-grouped or otherwise untouched holdout. The
primary comparison should report both operating points:

1. conservative high-precision triage: alpha `0.10` plus corroboration;
2. higher-recall triage: alpha `0.50` plus corroboration.

The paper should present these as two operating modes on a precision–coverage
frontier rather than declaring one universally best.

## 7. Reproducibility artifacts

| Artifact | Absolute path |
|---|---|
| Initial validation high-recall sweep | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\validation_high_recall_policy_sweep.json` |
| Extended validation sweep | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\validation_high_recall_extended_sweep.json` |
| Candidate test policy output | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\high_recall_candidate_test_policy_results.json` |
| Candidate application script | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\apply_high_recall_candidate_policy.py` |
| Extended validation sweep script | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\run_high_recall_validation_sweep.py` |
| Original frozen-policy output | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\frozen_test_policy_results.json` |


