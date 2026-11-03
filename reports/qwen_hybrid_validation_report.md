# Qwen–Semgrep Hybrid Validation Ablation Report

**Stage:** Conformal decision plus static corroboration  
**Date:** 2026-10-26  
**Partition:** Validation only; final test was not read

## 1. Purpose

This ablation asks whether requiring a Semgrep finding before accepting a
conformal `YES` decision improves the precision of vulnerability flags. It is a
validation-stage comparison, not a final operating-policy selection.

The comparison joins the 4,571-record conformal evaluation subset with the
matching Semgrep rows by `record_number`. All 4,571 records were present in
both artifacts. No calibration parameters were refitted and no test record was
used.

## 2. Candidate gates

### Corroborated-positive gate

Accept `YES` only when the conformal prediction set is the singleton `[1]` and
Semgrep reports at least one finding. All other records abstain. This is the
primary conservative ablation because no static finding is not treated as
evidence of safety.

### Dual-signal exploratory gate

Accept `YES` only with a singleton `[1]` plus a finding, and accept `NO` only
with a singleton `[0]` plus no finding. All other records abstain. This is
reported only as an exploratory comparison because the absence of a static
finding is not proof of non-vulnerability.

## 3. Results

### 3.1 Temperature scaling

| Significance | Gate | Coverage | Abstention | Accepted precision | Positive recall | Accepted records |
|---:|---|---:|---:|---:|---:|---:|
| 0.01 | Corroborated-positive | 0.11% | 99.89% | 0.00% | 0.00% | 5 |
| 0.05 | Corroborated-positive | 1.14% | 98.86% | 15.38% | 7.62% | 52 |
| 0.10 | Corroborated-positive | 2.28% | 97.72% | 13.46% | 13.33% | 104 |
| 0.20 | Corroborated-positive | 3.70% | 96.30% | 10.06% | 16.19% | 169 |
| 0.30 | Corroborated-positive | 5.10% | 94.90% | 8.58% | 19.05% | 233 |
| 0.50 | Corroborated-positive | 6.78% | 93.22% | 6.77% | 20.00% | 310 |

For temperature scaling, the dual-signal gate produced the same values because
the conformal singleton decisions in this evaluation were all `YES`; no
singleton `NO` decisions were available to add negative coverage.

At significance 0.05, static corroboration improved accepted precision from
6.73% for temperature-only conformal acceptance to 15.38%, but reduced
accepted coverage from 4.88% to 1.14% and vulnerable-record acceptance from
14.29% to 7.62%. This is a precision–coverage trade-off, not an unconditional
improvement.

### 3.2 Platt scaling

| Significance | Gate | Coverage | Abstention | Accepted precision | Positive recall | Accepted records |
|---:|---|---:|---:|---:|---:|---:|
| 0.01 | Corroborated-positive | 0.00% | 100.00% | 0.00% | 0.00% | 0 |
| 0.05 | Corroborated-positive | 0.00% | 100.00% | 0.00% | 0.00% | 0 |
| 0.10 | Corroborated-positive | 0.00% | 100.00% | 0.00% | 0.00% | 0 |
| 0.20 | Corroborated-positive | 0.00% | 100.00% | 0.00% | 0.00% | 0 |
| 0.30 | Corroborated-positive | 0.00% | 100.00% | 0.00% | 0.00% | 0 |
| 0.50 | Corroborated-positive | 0.00% | 100.00% | 0.00% | 0.00% | 0 |

The dual-signal exploratory gate accepted mostly negative decisions, with
98.10% accepted precision and 89.81% coverage at significance 0.05, but its
positive recall was 0.00%. This reproduces the earlier warning: a high overall
accepted precision can be obtained by accepting negatives while detecting no
vulnerabilities.

## 4. Interpretation

The hybrid ablation shows that static corroboration can increase the precision
of positive vulnerability flags for the temperature-scaled branch, but only by
accepting a very small fraction of records. Platt scaling remains unsuitable
for positive vulnerability screening in this validation setup because it
produces no accepted positive decisions, with or without corroboration.

The result does not justify freezing significance 0.05 as the final policy. The
operating point must be selected using an explicit cost model for missed
vulnerabilities, false alarms, and manual review capacity. The locked test
partition must remain untouched until that policy, rule pack, and analyzer
version are frozen.

## 5. Reproducibility

| Item | Value |
|---|---|
| Evaluator | [evaluate_hybrid_validation.py](C:/Users/rehan/Documents/Codex/2026-10-05/i-want-all-the-chats-and/work/evaluate_hybrid_validation.py) |
| Archived evaluator snapshot | [evaluate_hybrid_validation.py](C:/Users/rehan/Documents/Codex/2026-10-05/i-want-all-the-chats-and/outputs/thesis-codex-context/scripts/evaluate_hybrid_validation.py) |
| Conformal artifact | `C:/Users/rehan/AppData/Local/Temp/thesis_qwen_conformal_artifacts.json` |
| Static artifact | `C:/Users/rehan/AppData/Local/Temp/thesis_semgrep_valid_full.json` |
| Hybrid artifact | `C:/Users/rehan/AppData/Local/Temp/thesis_hybrid_validation_artifacts.json` |
| Final test used | No |


