# Qwen PrimeVul Validation Baseline Report

**Experiment date:** 2026-10-26  
**Experiment stage:** LLM-only baseline  
**Dataset role:** Leakage-controlled validation/development partition  
**Status:** Complete, preliminary empirical result

## 1. Purpose

This report records the first complete LLM-only baseline experiment for the
Thesis project. The experiment tests whether the selected open-source code
model can classify PrimeVul functions as vulnerable or non-vulnerable before
post-hoc calibration, selective abstention, or static-analysis corroboration
is added.

The result is a baseline measurement. It is not a calibrated confidence
result, a conformal prediction result, a final test result, or evidence that
the complete hybrid pipeline has improved reliability.

## 2. Task definition and label mapping

The binary task is defined as follows:

| Dataset target | Meaning | Expected model response |
|---:|---|---|
| `0` | No actionable vulnerability under the dataset label | `NO` |
| `1` | Actionable vulnerability is present | `YES` |

The raw target values were not inverted or relabeled during inference. Dataset
metadata was retained for evaluation, but the initial prompt contained only the
function code and the fixed classification instruction.

## 3. Dataset and leakage-control protocol

The experiment used the raw PrimeVul validation JSONL partition together with
the derived leakage-controlled manifest. The manifest excludes validation
records involved in the selected high-priority approximate-overlap review set;
the raw JSONL file itself was not modified.

| Item | Value |
|---|---:|
| Raw validation records | 23,948 |
| Retained validation records | 23,033 |
| Records excluded by manifest | 915 |
| Records processed | 23,033 |
| Final test partition used | No |

The validation partition is used for development and calibration work. It is
not the locked final evaluation partition.

## 4. Model and inference configuration

| Configuration item | Value |
|---|---|
| Model | `Qwen/Qwen2.5-Coder-1.5B-Instruct` |
| Hugging Face revision | `2e1fd39` |
| Model dtype | `torch.float16` |
| Device | `cuda:0` |
| Decoding | Greedy, `do_sample=False` |
| Seed | `12345` |
| Maximum generated tokens | `16` |
| Maximum input tokens | `4096` |
| OOM retry limit | `2048` input tokens |
| OOM retries used | `0` |
| Prompt metadata | Code only; no CWE/CVE/project/commit/hash fields |
| Output format | Streamed JSONL |

The system instruction was:

```text
You are a security expert that is good at static program analysis.
```

The user instruction supplied the function code and requested exactly one of
`YES` or `NO`. The model's raw response, parsed response, first-token top-five
probabilities, prompt hash, and record provenance were retained.

## 5. Execution completeness

The clean run was executed from the beginning rather than resumed from the
earlier interrupted output.

| Check | Result |
|---|---|
| Metadata status | `complete` |
| Records processed this run | 23,033 |
| Retained records in manifest | 23,033 |
| Unique record numbers | 23,033 |
| Input-token metadata present | All records |
| Truncated inputs | 183 (0.79%) |
| OOM retries | 0 |
| Runtime | 4,430.206 seconds |

The 183 truncated functions were processed under the declared 4,096-token
context policy. Their results remain valid observations of the bounded-input
protocol, but truncation must be disclosed in any final analysis.

## 6. Class and prediction distributions

| Quantity | Count | Percentage of all records |
|---|---:|---:|
| Ground-truth `target=0` | 22,473 | 97.57% |
| Ground-truth `target=1` | 560 | 2.43% |
| Predicted `YES` | 22,837 | 99.15% |
| Predicted `NO` | 19 | 0.08% |
| Unparseable response | 177 | 0.77% |

The output distribution shows that the model strongly favored the vulnerable
class. This is not a target-mapping error: `YES` is the intended response for
`target=1`. It is a model-baseline behavior characterized by very high flagging
and very low selectivity.

## 7. Confusion matrix and response resolution

Unparseable responses are shown separately and are not silently converted to
`NO`.

| Ground truth | Predicted `YES` | Predicted `NO` | Unparseable | Total |
|---|---:|---:|---:|---:|
| `target=0` | 22,313 false positives | 19 true negatives | 141 | 22,473 |
| `target=1` | 524 true positives | 0 false negatives | 36 | 560 |
| **Total** | **22,837** | **19** | **177** | **23,033** |

## 8. Baseline metrics

The following metrics use the explicit output resolution policy documented
above. Because unparseable responses are not binary decisions, metrics are
reported both over all records and over parseable accepted decisions where
appropriate.

| Metric | Value | Interpretation |
|---|---:|---|
| Overall exact accuracy, unresolved responses counted as incorrect | 2.36% | 544 correct decisions out of 23,033 |
| Parseable decision coverage | 99.23% | 22,856 records produced `YES` or `NO` |
| Accuracy among parseable decisions | 2.38% | 544 correct decisions out of 22,856 |
| Precision of `YES` predictions | 2.29% | 524 true positives among 22,837 flags |
| Recall among parseable decisions | 100.00% | 524 true positives and no parseable false negatives |
| Vulnerable records receiving `YES` | 93.57% | 524 of 560 vulnerable records |
| Non-vulnerable records explicitly flagged `YES` | 99.29% | 22,313 of 22,473 non-vulnerable records |

The 100% parseable recall is accompanied by a 2.29% flag precision. This
combination is consistent with a near-always-flag decision rule and should not
be interpreted as a useful high-performing classifier.

## 9. Confidence diagnostic

The run retained the top five probabilities for the first generated token. A
derived YES-versus-NO diagnostic ratio was available for 22,850 records. Its
mean was approximately 0.793, with a range of approximately 0.434 to 0.974.

These values are raw first-token diagnostics, not calibrated probabilities.
They were not used to fit a temperature, choose a test threshold, or claim a
coverage guarantee. The next calibration implementation must define a stable
YES/NO label-scoring procedure and handle unparseable generations explicitly.

## 10. Interpretation

The baseline demonstrates that the model and data pipeline can process the
complete retained validation partition on a Colab GPU under a bounded context
policy. It also reveals a severe selectivity problem: the model predicts a
vulnerability for nearly every function, including almost all non-vulnerable
records.

This is an important baseline finding for the Thesis research questions. It
provides a concrete case in which raw model decisions are unsuitable for
reliable automated review despite detecting the vulnerable class. The result
motivates the planned calibration and selective-abstention stages, but does not
guarantee that calibration alone will correct the model's ranking behavior.

## 11. Limitations and reporting rules

1. This is a validation/development result, not the locked test result.
2. The result uses the conservative derived leakage-control manifest and must
   be reported with that exclusion rule.
3. The 4,096-token input policy truncated 183 functions; truncation is part of
   this experiment and should be included in reproducibility reporting.
4. The 177 unparseable responses are unresolved outputs, not `NO` decisions.
5. The top-token values are not calibrated confidence estimates.
6. No calibration parameters, conformal thresholds, static-analysis outputs,
   or final-test metrics were fitted or reported here.
7. These results should not be generalized to a clean project-held-out
   benchmark without a separate grouped or external evaluation.

## 12. Reproducibility artifacts

| Artifact | Location |
|---|---|
| Full JSONL results | [qwen_valid_results_fixed.jsonl](C:/Users/rehan/OneDrive/Desktop/Thesis/implementation/qwen_valid_results_fixed.jsonl) |
| Full-run metadata | [qwen_valid_results.jsonl.meta_fixed.json](C:/Users/rehan/OneDrive/Desktop/Thesis/implementation/qwen_valid_results.jsonl.meta_fixed.json) |
| Colab notebook | [primevul_qwen_colab.ipynb](C:/Users/rehan/Documents/Codex/2026-10-05/i-want-all-the-chats-and/work/primevul_qwen_colab.ipynb) |
| Archived notebook snapshot | [primevul_qwen_colab.ipynb](C:/Users/rehan/Documents/Codex/2026-10-05/i-want-all-the-chats-and/outputs/thesis-codex-context/scripts/primevul_qwen_colab.ipynb) |
| Archived inference scripts | [run_qwen_sample.py](C:/Users/rehan/Documents/Codex/2026-10-05/i-want-all-the-chats-and/outputs/thesis-codex-context/scripts/run_qwen_sample.py), [run_qwen_colab.py](C:/Users/rehan/Documents/Codex/2026-10-05/i-want-all-the-chats-and/outputs/thesis-codex-context/scripts/run_qwen_colab.py) |
| Baseline protocol | [BASELINE_PROTOCOL.md](C:/Users/rehan/Documents/Codex/2026-10-05/i-want-all-the-chats-and/work/BASELINE_PROTOCOL.md) |
| Leakage-controlled manifest | `thesis_primevul_leakage_controlled_manifest.json` |

## 13. Thesis-ready result statement

> Using the leakage-controlled PrimeVul validation partition, the pinned
> `Qwen/Qwen2.5-Coder-1.5B-Instruct` model was evaluated on 23,033 retained
> records using a code-only YES/NO prompt and greedy decoding. The model
> produced parseable binary decisions for 99.23% of records and predicted
> `YES` for 99.15% of the validation set. It achieved 524 true positives,
> 22,313 false positives, 19 true negatives, and no parseable false negatives;
> 177 outputs were unparseable. Consequently, flag precision was 2.29% and
> overall accuracy was 2.36% when unresolved outputs were counted as incorrect.
> These results constitute the raw LLM baseline and motivate the subsequent
> calibration and selective-abstention experiments; they are not final-test or
> calibrated results.

