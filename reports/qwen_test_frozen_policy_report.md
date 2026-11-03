# PrimeVul Locked-Test Frozen-Policy Evaluation Report

**Experiment date:** 2026-10-27  
**Experiment stage:** Locked-test Semgrep corroboration and frozen-policy application  
**Dataset role:** Leakage-controlled PrimeVul test partition  
**Status:** Complete

## 1. Purpose

This report records the application of the validation-derived operating policy
to the completed Qwen test output. The policy was frozen before test evaluation
and was not fitted, tuned, or selected using test labels.

## 2. Required inputs

| Input | Description |
|---|---|
| Qwen output | 24,008 retained PrimeVul test records |
| Semgrep rules | `work/semgrep_primevul_rules.yml` |
| Semgrep version | Community Edition `1.163.0` |
| Validation artifact | `thesis_qwen_conformal_artifacts.json` |
| Test manifest | High-priority leakage-controlled manifest |

The raw PrimeVul JSONL files were not modified. Semgrep scanned isolated
function snippets written to temporary files outside the project directory.

## 3. Semgrep corroboration scan

Semgrep was run in 47 batches using the same 512-record batch size as the
validation corroboration scan. The scan covered exactly the 24,008 Qwen test
records, with no missing or unexpected record numbers.

| Quantity | Count |
|---|---:|
| Qwen/test records scanned | 24,008 |
| Records with a static finding | 1,514 |
| Records with no finding | 22,494 |
| LLM/static `AGREE` | 1,434 |
| LLM/static `DISAGREE` | 3 |
| `NEUTRAL` | 22,571 |
| Static findings on vulnerable records | 104 |
| Static positive precision | 6.87% |
| Static positive recall | 19.92% |

No finding was treated as neutral evidence, not as proof that the function is
safe.

## 4. Frozen operating policy

The following settings were carried over unchanged from validation:

| Policy component | Frozen value |
|---|---|
| Calibration | Temperature scaling |
| Temperature | `445.683640902898` |
| Conformal significance level | `α = 0.10` |
| Static corroboration | Semgrep finding required |
| Automatic `YES` condition | Conformal prediction set exactly `[1]` and Semgrep finding present |
| All other cases | `ABSTAIN` |
| Test labels used for fitting/selection | No |

The policy does not automatically accept `NO`. Missing pairwise scores,
ambiguous conformal sets, no static finding, and other gate failures are
abstentions.

## 5. Policy output

| Decision/reason | Count |
|---|---:|
| Accepted `YES` | 452 |
| `ABSTAIN` | 23,556 |
| Abstain: frozen gate not satisfied | 23,342 |
| Abstain: missing pairwise score | 214 |
| Singleton positive with static finding | 452 |

The conformal prediction-set distribution was:

| Prediction set | Count |
|---|---:|
| `[0, 1]` | 21,475 |
| `[1]` | 2,319 |
| Empty set | 214 |

## 6. Locked-test evaluation metrics

The preserved test targets were joined only after policy application for final
evaluation.

| Ground truth | Accepted `YES` | `ABSTAIN` | Total |
|---|---:|---:|---:|
| `target=0` | 416 | 23,070 | 23,486 |
| `target=1` | 36 | 486 | 522 |
| **Total** | **452** | **23,556** | **24,008** |

| Metric | Value |
|---|---:|
| Accepted-decision coverage | 1.88% |
| Abstention rate | 98.12% |
| Precision among accepted `YES` decisions | 7.96% |
| Vulnerable-record acceptance/positive recall | 6.90% |
| Accepted false-positive rate among target-0 records | 1.77% |

The policy therefore substantially reduces the raw model's nearly universal
flagging behavior, but it accepts relatively few records and identifies only a
minority of vulnerable test records. The result is a selective review policy,
not a complete automated classifier.

## 7. Interpretation

The frozen gate produced a high abstention rate and increased the precision of
accepted positive decisions from the raw Qwen baseline's 2.01% to 7.96%.
This improvement comes with a reduction in vulnerable-record acceptance from
the raw baseline's 91.76% YES rate to 6.90% policy acceptance.

These test results support the central reliability trade-off studied in the
Thesis: stricter confidence and static corroboration requirements improve the
quality of accepted alerts while escalating most cases for review. The static
analyzer remains a corroboration signal rather than a semantic ground-truth
oracle.

## 8. Limitations

1. The policy was selected from validation results under the documented
   illustrative cost model and positive-recall floor; no test-driven tuning was
   performed.
2. The Semgrep rules operate on isolated C/C++ function snippets and do not
   provide repository-level build or interprocedural analysis.
3. The 214 missing pairwise scores were abstained rather than converted to a
   binary decision.
4. This is one locked-test evaluation of the selected policy. Record-level
   paired bootstrap intervals, ablations, and project-clustered sensitivity
   intervals are documented in the associated statistical reports.
5. The result should not be generalized to unseen-project performance because
   the supplied PrimeVul partitions contain project overlap.

## 9. Reproducibility artifacts

| Artifact | Location |
|---|---|
| Qwen test output | [qwen_test_results.jsonl](C:/Users/rehan/OneDrive/Desktop/Thesis/implementation/qwen_test_results.jsonl) |
| Semgrep test output | [semgrep_test_results.json](C:/Users/rehan/OneDrive/Desktop/Thesis/implementation/semgrep_test_results.json) |
| Frozen-policy output | [frozen_test_policy_results.json](C:/Users/rehan/OneDrive/Desktop/Thesis/implementation/frozen_test_policy_results.json) |
| Frozen-policy script | [apply_frozen_policy.py](C:/Users/rehan/Documents/Codex/2026-10-05/i-want-all-the-chats-and/work/apply_frozen_policy.py) |
| Semgrep script | [run_semgrep_corroboration.py](C:/Users/rehan/Documents/Codex/2026-10-05/i-want-all-the-chats-and/work/run_semgrep_corroboration.py) |
| Frozen operating policy | [THESIS_OPERATING_POLICY.md](C:/Users/rehan/Documents/Codex/2026-10-05/i-want-all-the-chats-and/outputs/thesis-codex-context/docs/THESIS_OPERATING_POLICY.md) |

### Artifact SHA-256 checksums

| Artifact | SHA-256 |
|---|---|
| `semgrep_test_results.json` | `48004DFBF1C6506970A9334712E26E5D398DEE8EC9E853A220A032168A41DF1C` |
| `frozen_test_policy_results.json` | `627C4E15697AB06E5E26E61F54CCAD920CED4604E04AC5CFD0B84A7CF7A69E8A` |

## 10. Thesis-ready result statement

> On the leakage-controlled PrimeVul test partition, the frozen policy using
> Qwen temperature scaling, split-conformal abstention at `α=0.10`, and
> Semgrep corroboration produced 452 accepted `YES` decisions and 23,556
> abstentions across 24,008 records. Accepted-decision coverage was 1.88%,
> abstention was 98.12%, accepted-positive precision was 7.96%, and vulnerable
> record acceptance was 6.90%. The policy was applied without fitting or
> selecting any parameter from test labels. These results quantify the
> precision-coverage trade-off of the frozen selective review pipeline.

