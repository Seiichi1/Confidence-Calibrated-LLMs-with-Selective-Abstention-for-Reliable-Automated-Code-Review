# Project-Clustered Locked-Test Sensitivity Report

**Thesis project:** Confidence-Calibrated LLMs with Selective Abstention for Reliable Automated Code Review  
**Analysis date:** 2026-10-27  
**Evaluation partition:** PrimeVul test partition after the frozen leakage-controlled manifest  
**Status:** Complete

## 1. Purpose

The locked-test evaluation was previously summarized with record-level paired
bootstrap intervals. Because PrimeVul contains many records from the same
software projects, record-level resampling can understate uncertainty when
records within a project are correlated. This analysis therefore repeats the
uncertainty calculation using the project as the resampling unit.

This is a sensitivity analysis only. It does not create a new train/validation/
test split, refit calibration, select a policy from test labels, or change the
frozen operating policy.

## 2. Inputs and reproducibility

The analysis joined the following aligned artifacts by `record_number`:

- `qwen_test_results.jsonl`: raw Qwen predictions and PrimeVul targets.
- `semgrep_test_results.json`: locked-test static-analysis findings.
- `frozen_test_policy_results.json`: the validation-derived conformal/static
  operating-policy decisions.

The 24,008 retained test records were grouped by the PrimeVul `project` field
into 217 project clusters. The smallest project cluster contained 1 record,
the median contained 36 records, the largest contained 3,970 records, and 13
projects contained a single record.

Whole projects were sampled with replacement for 5,000 bootstrap iterations.
The random seed was `20261027`. Each resample contained 217 sampled projects;
metrics were recomputed from the aggregated record counts in the sampled
projects. The analysis used no test labels for fitting or policy selection, and
the policy parameters were unchanged.

## 3. Point estimates

The point estimates are the same locked-test estimates reported previously,
because the project-clustered procedure changes the uncertainty calculation,
not the underlying predictions or decisions.

| Method | Coverage | Abstention | Accepted-positive precision | Positive recall |
|---|---:|---:|---:|---:|
| Raw Qwen | 99.08% | 0.92% | 2.01% | 91.76% |
| Temperature + conformal only | 9.66% | 90.34% | 4.66% | 20.69% |
| Semgrep only | 6.31% | 93.69% | 6.87% | 19.92% |
| Frozen hybrid | 1.88% | 98.12% | 7.96% | 6.90% |

The frozen hybrid accepted 452 positive alerts, including 36 vulnerable
records and 416 non-vulnerable records. It abstained on 23,556 records.

## 4. Project-clustered 95% intervals

| Method | Coverage 95% interval | Abstention 95% interval | Accepted-positive precision 95% interval | Positive recall 95% interval |
|---|---:|---:|---:|---:|
| Raw Qwen | 98.49–99.49% | 0.51–1.51% | 1.50–2.73% | 85.87–95.98% |
| Temperature + conformal only | 7.58–11.83% | 88.17–92.42% | 3.75–5.97% | 14.10–29.97% |
| Semgrep only | 5.03–7.77% | 92.23–94.97% | 5.56–8.79% | 13.04–30.00% |
| Frozen hybrid | 1.38–2.47% | 97.53–98.62% | 5.46–10.85% | 3.84–11.21% |

The clustered interval for frozen-hybrid accepted-positive precision is wider
than the corresponding record-level interval because the test set is strongly
project-concentrated. This is evidence that project composition is an
important source of uncertainty for the reported selective-review precision.

## 5. Paired frozen-hybrid differences

The following values are frozen-hybrid metric minus the indicated comparator.
Intervals are project-clustered paired 95% intervals and are reported in
percentage points.

| Comparison | Coverage difference | Precision difference | Positive-recall difference |
|---|---:|---:|---:|
| Frozen hybrid − raw Qwen | −97.20 pp (−97.76, −96.40) | +5.95 pp (+3.48, +8.75) | −84.87 pp (−89.98, −78.21) |
| Frozen hybrid − temperature/conformal | −7.78 pp (−9.52, −6.12) | +3.31 pp (+1.10, +5.56) | −13.79 pp (−19.84, −9.56) |
| Frozen hybrid − Semgrep | −4.42 pp (−5.46, −3.51) | +1.10 pp (−1.14, +3.06) | −13.03 pp (−20.44, −8.24) |

The frozen hybrid consistently trades coverage and positive recall for higher
precision relative to the raw Qwen baseline and the temperature/conformal
ablation. Relative to Semgrep alone, the precision improvement is uncertain:
its clustered interval includes zero, while coverage and positive recall are
lower for the frozen hybrid.

## 6. Interpretation for the thesis

The project-clustered sensitivity analysis supports three bounded conclusions:

1. The frozen policy remains highly selective under a resampling scheme that
   respects project-level concentration.
2. The precision advantage over raw Qwen and temperature/conformal-only
   acceptance remains positive throughout the project-clustered paired
   intervals.
3. The frozen hybrid does not dominate Semgrep on every metric: its precision
   advantage over Semgrep is not statistically resolved by this sensitivity
   analysis, and it accepts fewer vulnerable records.

These intervals should be described as project-clustered uncertainty
intervals, not as evidence of generalization to previously unseen projects.
The official PrimeVul partitions contain project overlap, so a true
unseen-project generalization claim would require a separately designed
grouped resplit and an additional locked evaluation.

## 7. Limitations and reporting boundary

- The resampling unit is the observed PrimeVul project, not an independently
  sampled population of projects.
- Project clusters with thousands of records can materially influence the
  estimate; this is a property of the supplied test partition and is retained
  rather than reweighted away.
- No semantic duplicate or vulnerability-label reclassification was performed.
- Approximate candidates and static findings remain triage/corroboration
  signals; they are not asserted to be confirmed semantic duplicates or
  independent ground truth.
- The analysis does not resolve the separate response-resolution issue for
  unparseable or incomplete Qwen generations.

## 8. Reproduction command

From the Thesis workspace:

```powershell
python work/run_project_clustered_statistics.py `
  --qwen-results "C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\qwen_test_results.jsonl" `
  --static-results "C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\semgrep_test_results.json" `
  --policy-results "C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\frozen_test_policy_results.json" `
  --iterations 5000 `
  --seed 20261027 `
  --output "C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\project_clustered_test_statistics.json"
```

The machine-readable output is stored outside the project directory at:

`C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\project_clustered_test_statistics.json`


