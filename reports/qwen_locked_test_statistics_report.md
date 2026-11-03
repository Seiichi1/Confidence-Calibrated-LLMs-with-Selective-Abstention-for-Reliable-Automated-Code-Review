# Locked-Test Statistical Uncertainty and Paired Ablation Report

**Experiment date:** 2026-10-27  
**Experiment stage:** Statistical uncertainty analysis and paired ablations  
**Dataset role:** Leakage-controlled PrimeVul test partition  
**Status:** Complete; an optional grouped-split/unseen-project evaluation remains open

## 1. Purpose and evaluation rule

This report quantifies uncertainty around the locked-test operating points and
compares the raw Qwen baseline with the component ablations used to interpret
the frozen hybrid policy.

All methods were evaluated on the identical 24,008 retained test records. The
test labels were read only after all model, calibration, conformal, analyzer,
and policy choices were frozen. No parameter or threshold was fitted from test
labels.

For this positive-alert comparison, an accepted record means that the method
returns an affirmative vulnerability alert. All other outcomes are treated as
abstentions. This makes coverage, accepted-positive precision, and
vulnerable-record positive recall comparable across the methods.

## 2. Compared methods

| Method | Accepted positive alert condition |
|---|---|
| Raw Qwen | Raw model response is parseable `YES` |
| Temperature + conformal only | Frozen temperature-scaled conformal set is exactly `[1]`; no Semgrep gate |
| Semgrep only | Semgrep reports at least one finding |
| Frozen hybrid | Conformal set exactly `[1]` and Semgrep reports a finding |

The conformal temperature and score distribution are the validation-derived
values documented in `THESIS_OPERATING_POLICY.md`. The frozen hybrid is the
prespecified final operating policy.

## 3. Bootstrap method

Uncertainty intervals use 5,000 record-level bootstrap resamples with
replacement, seed `20261027`. Paired comparisons reuse the same resampled
record indices for both methods, preserving the within-record relationship.
The reported intervals are percentile 95% intervals.

The analysis is therefore conditional on record-level resampling. It does not
model project-level clustering or provide a project-held-out generalization
interval.

## 4. Point estimates and 95% intervals

Percentages are shown for readability. Interval endpoints are the bootstrap
95% lower and upper percentiles.

| Method | Accepted records | Coverage (95% CI) | Accepted-positive precision (95% CI) | Positive recall (95% CI) |
|---|---:|---:|---:|---:|
| Raw Qwen | 23,788 | 99.08% (98.96–99.20%) | 2.01% (1.84–2.19%) | 91.76% (89.31–94.02%) |
| Temperature + conformal only | 2,319 | 9.66% (9.28–10.03%) | 4.66% (3.81–5.52%) | 20.69% (17.17–24.26%) |
| Semgrep only | 1,514 | 6.31% (5.99–6.62%) | 6.87% (5.63–8.16%) | 19.92% (16.47–23.47%) |
| Frozen hybrid | 452 | 1.88% (1.71–2.05%) | 7.96% (5.59–10.58%) | 6.90% (4.81–9.18%) |

The raw-Qwen coverage here counts only accepted `YES` alerts; it differs from
parseable-decision coverage because raw `NO` decisions are treated as
non-alerts in this selective-positive comparison.

## 5. Paired differences: frozen hybrid minus comparator

| Comparator | Coverage difference (95% CI) | Precision difference (95% CI) | Recall difference (95% CI) |
|---|---:|---:|---:|
| Raw Qwen | −97.20 pp (−97.42 to −96.98) | +5.95 pp (+3.60 to +8.54) | −84.87 pp (−87.84 to −81.77) |
| Temperature + conformal only | −7.78 pp (−8.13 to −7.44) | +3.31 pp (+1.27 to +5.53) | −13.79 pp (−16.82 to −10.79) |
| Semgrep only | −4.42 pp (−4.69 to −4.16) | +1.10 pp (−0.90 to +3.18) | −13.03 pp (−15.97 to −10.14) |

The paired intervals show that the frozen hybrid's precision increase over raw
Qwen and temperature-conformal-only is positive under this resampling
analysis. Its recall reduction relative to all three comparators is also
substantial. The precision difference from Semgrep-only crosses zero, so a
precision improvement over that component baseline is not established by this
interval alone.

## 6. Interpretation

The results demonstrate the intended selective-review trade-off. The frozen
hybrid gate is substantially more selective than the raw model and accepts
fewer alerts, while its accepted-positive precision is higher. The cost is a
large reduction in vulnerable-record acceptance: only 6.90% of vulnerable test
records receive an accepted positive decision under the frozen gate.

The temperature-conformal-only ablation retains more vulnerable alerts but
also accepts more false positives. Adding Semgrep corroboration therefore
strengthens selectivity, but the resulting policy should be described as a
high-precision review triage mechanism rather than a complete vulnerability
detector.

## 7. Limitations and remaining analysis

1. These record-level intervals are complemented by the project-clustered
   sensitivity analysis in `qwen_project_clustered_statistics_report.md`; a
   project-held-out evaluation remains optional and has not been performed.
2. Bootstrap intervals are uncertainty summaries, not a substitute for a
   prespecified hypothesis test.
3. The supplied PrimeVul partitions contain project overlap, so these results
   do not establish unseen-project generalization.
4. The 214 missing pairwise scores remain abstentions under the frozen policy.
5. Additional ablations and sensitivity analyses should preserve the locked
   test partition and must not tune the policy on test labels.

## 8. Reproducibility artifacts

| Artifact | Location |
|---|---|
| Statistics JSON | [locked_test_statistics.json](C:/Users/rehan/OneDrive/Desktop/Thesis/implementation/locked_test_statistics.json) |
| Statistics script | [run_locked_test_statistics.py](C:/Users/rehan/Documents/Codex/2026-10-05/i-want-all-the-chats-and/work/run_locked_test_statistics.py) |
| Frozen-policy report | [qwen_test_frozen_policy_report.md](C:/Users/rehan/Documents/Codex/2026-10-05/i-want-all-the-chats-and/outputs/thesis-codex-context/docs/qwen_test_frozen_policy_report.md) |

### Artifact SHA-256 checksum

| Artifact | SHA-256 |
|---|---|
| `locked_test_statistics.json` | `F7739C78D8FC2CA6D2F4568EFFEAFD5F6644C115C851E622C4616F9CEB84642D` |

The current file was produced with 5,000 iterations and seed `20261027`.

## 9. Thesis-ready result statement

> On the identical leakage-controlled PrimeVul test records, the frozen hybrid
> policy achieved 1.88% positive-alert coverage, 7.96% accepted-positive
> precision, and 6.90% vulnerable-record positive recall. Compared with raw
> Qwen positive alerts, the frozen policy increased accepted-positive precision
> by 5.95 percentage points (paired bootstrap 95% CI: +3.60 to +8.54) while
> reducing positive recall by 84.87 percentage points (95% CI: −87.84 to
> −81.77). Compared with temperature-conformal-only acceptance, it increased
> precision by 3.31 percentage points and reduced recall by 13.79 points. These
> results quantify the precision–coverage trade-off of the selective review
> pipeline and do not establish project-held-out generalization.

