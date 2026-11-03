# Thesis Results and Discussion Tables

**Thesis project:** Confidence-Calibrated LLMs with Selective Abstention for Reliable Automated Code Review  
**Evaluation date:** 2026-10-27  
**Dataset:** Leakage-controlled PrimeVul test partition  
**Status:** Drafted from completed locked-test analyses

This document provides thesis-ready tables and result statements for the
locked-test evaluation. It combines the point estimates, record-level paired
bootstrap intervals, and project-clustered sensitivity intervals. The test
partition was not used to fit calibration, choose thresholds, or select the
operating policy.

## Table 1. Locked-test evaluation population

| Quantity | Count |
|---|---:|
| Retained test records | 24,008 |
| Non-vulnerable records (`target=0`) | 23,486 |
| Vulnerable records (`target=1`) | 522 |
| Project clusters | 217 |
| Median records per project | 36 |
| Largest project cluster | 3,970 |

The project-clustered figures are a sensitivity analysis of the same retained
test population. They do not represent a new split or an unseen-project test.

## Table 2. Locked-test point estimates by method

For this comparison, an accepted record is a positive vulnerability alert.
Non-alert outcomes are treated as abstentions. Precision is therefore the
precision among accepted positive alerts, not ordinary binary accuracy.

| Method | Accepted alerts | True positives | False positives | Abstentions | Coverage | Accepted-positive precision | Positive recall |
|---|---:|---:|---:|---:|---:|---:|---:|
| Raw Qwen | 23,788 | 479 | 23,309 | 220 | 99.08% | 2.01% | 91.76% |
| Temperature + conformal only | 2,319 | 108 | 2,211 | 21,689 | 9.66% | 4.66% | 20.69% |
| Semgrep only | 1,514 | 104 | 1,410 | 22,494 | 6.31% | 6.87% | 19.92% |
| Frozen hybrid | 452 | 36 | 416 | 23,556 | 1.88% | 7.96% | 6.90% |

The frozen hybrid required both the validation-derived conformal positive set
and a Semgrep finding. It produced the highest accepted-alert precision among
the compared methods, but it accepted the fewest records and had the lowest
positive recall.

## Table 3. Record-level paired-bootstrap 95% intervals

Intervals are percentile intervals from 5,000 paired record-level bootstrap
resamples with seed `20261027`.

| Method | Coverage | Accepted-positive precision | Positive recall |
|---|---:|---:|---:|
| Raw Qwen | 99.08% (98.96–99.20%) | 2.01% (1.84–2.19%) | 91.76% (89.31–94.02%) |
| Temperature + conformal only | 9.66% (9.28–10.03%) | 4.66% (3.81–5.52%) | 20.69% (17.17–24.26%) |
| Semgrep only | 6.31% (5.99–6.62%) | 6.87% (5.63–8.16%) | 19.92% (16.47–23.47%) |
| Frozen hybrid | 1.88% (1.71–2.05%) | 7.96% (5.59–10.58%) | 6.90% (4.81–9.18%) |

## Table 4. Project-clustered sensitivity intervals

Intervals are percentile intervals from 5,000 whole-project bootstrap
resamples with seed `20261027`. Projects, rather than individual records,
were sampled with replacement.

| Method | Coverage | Accepted-positive precision | Positive recall |
|---|---:|---:|---:|
| Raw Qwen | 99.08% (98.49–99.49%) | 2.01% (1.50–2.73%) | 91.76% (85.87–95.98%) |
| Temperature + conformal only | 9.66% (7.58–11.83%) | 4.66% (3.75–5.97%) | 20.69% (14.10–29.97%) |
| Semgrep only | 6.31% (5.03–7.77%) | 6.87% (5.56–8.79%) | 19.92% (13.04–30.00%) |
| Frozen hybrid | 1.88% (1.38–2.47%) | 7.96% (5.46–10.85%) | 6.90% (3.84–11.21%) |

The project-clustered intervals are wider than the record-level intervals for
several metrics, reflecting the concentration of records in a small number of
projects. They quantify sensitivity to project dependence; they do not
establish generalization to projects absent from training and evaluation.

## Table 5. Frozen-hybrid paired differences

Each value is frozen hybrid minus the comparator. Differences are in percentage
points. The first interval is record-level paired bootstrap; the second is the
project-clustered sensitivity interval.

| Comparator | Coverage difference | Precision difference | Positive-recall difference |
|---|---:|---:|---:|
| Raw Qwen | −97.20 pp (−97.42, −96.98); clustered (−97.76, −96.40) | +5.95 pp (+3.60, +8.54); clustered (+3.48, +8.75) | −84.87 pp (−87.84, −81.77); clustered (−89.98, −78.21) |
| Temperature + conformal only | −7.78 pp (−8.13, −7.44); clustered (−9.52, −6.12) | +3.31 pp (+1.27, +5.53); clustered (+1.10, +5.56) | −13.79 pp (−16.82, −10.79); clustered (−19.84, −9.56) |
| Semgrep only | −4.42 pp (−4.69, −4.16); clustered (−5.46, −3.51) | +1.10 pp (−0.90, +3.18); clustered (−1.14, +3.06) | −13.03 pp (−15.97, −10.14); clustered (−20.44, −8.24) |

The precision improvement over raw Qwen and temperature/conformal-only
acceptance remains positive under both uncertainty treatments. The precision
difference from Semgrep alone includes zero under both treatments and should
not be presented as an established improvement.

## Table 6. Frozen-policy configuration

| Component | Frozen setting |
|---|---|
| LLM | `Qwen/Qwen2.5-Coder-1.5B-Instruct`, pinned revision `2e1fd39` |
| Calibration | Temperature scaling, temperature `445.683640902898` |
| Conformal significance | `α = 0.10` |
| Static corroboration | Semgrep Community Edition `1.163.0` |
| Acceptance rule | Conformal prediction set exactly `[1]` and at least one Semgrep finding |
| Other outcomes | `ABSTAIN` |
| Test-label fitting or policy selection | None |

## Table 7. Project-held-out higher-recall evaluation

The candidate contains 38,362 records from 400 projects absent from the
official validation and test partitions, including 1,078 vulnerable records.

| Policy | Coverage | Accepted-positive precision | Positive recall |
|---|---:|---:|---:|
| Frozen alpha `0.10` | 2.89% | 11.01% | 11.32% |
| Higher-recall alpha `0.50` | 8.01% | 8.86% | 25.23% |

## Table 8. Project-held-out paired differences and uncertainty

Each value is higher-recall alpha `0.50` minus frozen alpha `0.10`. The
record-level interval uses 5,000 paired record resamples; the clustered
interval uses 5,000 whole-project resamples over 400 projects.

| Metric | Point difference | Record-level 95% interval | Project-clustered 95% interval |
|---|---:|---:|---:|
| Coverage | +5.12 pp | +4.90 to +5.34 pp | +4.13 to +6.19 pp |
| Accepted-positive precision | −2.15 pp | −3.61 to −0.78 pp | −3.45 to −0.89 pp |
| Positive recall | +13.91 pp | +11.89 to +15.99 pp | +11.29 to +16.57 pp |

The direction of every trade-off is stable under project clustering: alpha
`0.50` accepts more records and more vulnerable records, while precision falls.

## Thesis-ready results statement

On the 24,008-record leakage-controlled PrimeVul test partition, raw Qwen
produced positive alerts for 99.08% of records, with 2.01% precision among
those alerts and 91.76% vulnerable-record recall. The frozen selective hybrid
policy reduced accepted-alert coverage to 1.88% and increased precision to
7.96%, while positive recall decreased to 6.90%. The frozen policy therefore
improved the quality of accepted alerts at the cost of substantially reduced
coverage and vulnerable-record acceptance.

The frozen hybrid's precision advantage over raw Qwen was +5.95 percentage
points under record-level paired bootstrap uncertainty (95% CI: +3.60 to
+8.54) and +5.95 points under project-clustered sensitivity analysis (95% CI:
+3.48 to +8.75). Its precision advantage over temperature/conformal-only
acceptance was +3.31 points under record-level resampling and +3.31 points
under project-clustered resampling. The difference from Semgrep-only precision
was not statistically resolved because both paired intervals included zero.

For the separate project-held-out candidate, the frozen alpha `0.10` policy
accepted 2.89% of records with 11.01% accepted-positive precision and 11.32%
positive recall. Raising the prespecified operating point to alpha `0.50`
increased coverage to 8.01% and positive recall to 25.23%, while reducing
precision to 8.86%. The paired alpha `0.50` minus alpha `0.10` differences were
therefore +5.12 percentage points in coverage, −2.15 points in precision, and
+13.91 points in recall. The corresponding project-clustered 95% intervals
were +4.13 to +6.19, −3.45 to −0.89, and +11.29 to +16.57 percentage points,
respectively. This result can be reported as an independent mixed
coverage/recall trade-off on 38,362 records from 400 train-only projects; it
must not be presented as proof of universal unseen-project generalization.

## Discussion

### Selective-review interpretation

The results support the intended selective-review interpretation of the
pipeline. Raw Qwen's near-universal positive-alert behavior gives high
vulnerable-record acceptance but produces an impractically large false-alert
burden. Calibration, conformal abstention, and static corroboration suppress
most alerts and improve precision among the alerts that are retained.

### Recall limitation

The frozen policy is not a high-recall vulnerability detector. It accepted only
36 of 522 vulnerable test records. It should therefore be described as a
high-precision review-triage mode that escalates most cases, not as a complete
automated replacement for vulnerability detection.

### Component interpretation

The temperature/conformal-only and Semgrep-only ablations retained roughly
20% vulnerable-record recall, whereas the intersection gate retained 6.90% on
the official test. This indicates that requiring both signals is the main
source of the final policy's conservatism. The validation-selected alpha `0.50`
mode provides a prespecified higher-recall alternative, but its project-held-
out precision is lower than the frozen mode.

### Project dependence and generalization

Project-clustered intervals are a more conservative uncertainty sensitivity
analysis for the supplied partition because records from the same project may
not be independent. The separate project-held-out candidate addresses the
official partition-overlap concern for this specific comparison. It supports
a mixed recall/coverage trade-off for the selected Qwen/Semgrep policies, not a
universal unseen-project generalization claim.

### Scope of claims

The analysis establishes a precision–coverage trade-off for one frozen
open-source Qwen configuration and one auditable Semgrep corroboration rule
pack. It does not establish that the model is universally calibrated, that
Semgrep findings are semantic ground truth, or that the pipeline dominates all
alternative models and operating points.

## Recommended placement in the thesis

- Use Tables 1–2 in the main locked-test results section.
- Use Tables 3–5 in the uncertainty and ablation subsection.
- Use Tables 6–8 in the implementation/protocol and improvement-study
  subsections or an appendix.
- Use the results statement as the main quantitative paragraph.
- Use the discussion subsections to state the precision–recall trade-off and
  avoid presenting the frozen hybrid as a high-recall detector.

## Source reports and artifacts

- [Locked-test frozen-policy report](C:/Users/rehan/Documents/Codex/2026-10-05/i-want-all-the-chats-and/outputs/thesis-codex-context/docs/qwen_test_frozen_policy_report.md)
- [Record-level statistical report](C:/Users/rehan/Documents/Codex/2026-10-05/i-want-all-the-chats-and/outputs/thesis-codex-context/docs/qwen_locked_test_statistics_report.md)
- [Project-clustered sensitivity report](C:/Users/rehan/Documents/Codex/2026-10-05/i-want-all-the-chats-and/outputs/thesis-codex-context/docs/qwen_project_clustered_statistics_report.md)
- [Project-clustered machine-readable output](C:/Users/rehan/OneDrive/Desktop/Thesis/implementation/project_clustered_test_statistics.json)
- [Project-held-out policy report](C:/Users/rehan/Documents/Codex/2026-10-05/i-want-all-the-chats-and/outputs/thesis-codex-context/docs/unseen_project_policy_results_report.md)
- [Project-held-out direct comparison statistics](C:/Users/rehan/OneDrive/Desktop/Thesis/implementation/unseen_policy_comparison_statistics.json)


