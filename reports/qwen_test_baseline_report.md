# Qwen PrimeVul Locked-Test Raw Baseline Report

**Experiment date:** 2026-10-27  
**Experiment stage:** Locked-test LLM-only baseline  
**Dataset role:** Leakage-controlled PrimeVul test partition  
**Status:** Complete raw inference; frozen-policy evaluation remains pending

## 1. Purpose

This report records the complete raw Qwen inference run on the retained
PrimeVul test partition. It establishes the locked-test LLM-only baseline
before conformal abstention and Semgrep corroboration are applied.

This is not the final hybrid-pipeline result. Test labels were used only for
post-run evaluation and were not used to fit calibration, choose thresholds,
or modify the operating policy.

## 2. Task definition and label mapping

| Dataset target | Meaning | Expected model response |
|---:|---|---|
| `0` | No actionable vulnerability under the dataset label | `NO` |
| `1` | Actionable vulnerability is present | `YES` |

The raw target values were not inverted or relabeled. The prompt contained
only the function code and the fixed YES/NO classification instruction.

## 3. Dataset and leakage-control protocol

The run used the raw PrimeVul test JSONL file together with the completed
high-priority leakage-controlled manifest. The raw JSONL file was not modified.

| Item | Value |
|---|---:|
| Raw test records | 24,788 |
| Records excluded by manifest | 780 |
| Retained test records | 24,008 |
| Records processed | 24,008 |
| Validation/test calibration fitting | None |

The test partition remained locked for model and policy development. The
manifest selection was completed before this inference run.

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
| OOM retries | `0` |
| Prompt metadata | Code only; no CWE/CVE/project/commit/hash fields |
| Sample count | `0`, meaning all retained records |
| Output format | Streamed JSONL |

The system instruction was:

```text
You are a security expert that is good at static program analysis.
```

The user instruction supplied the function code and requested exactly one of
`YES` or `NO`.

## 5. Execution completeness and integrity

| Check | Result |
|---|---:|
| Metadata status | `complete` |
| Records processed this run | 24,008 |
| Retained records in manifest | 24,008 |
| Unique record numbers | 24,008 |
| Duplicate record numbers | 0 |
| Missing retained records | 0 |
| Unexpected records | 0 |
| JSON parse errors | 0 |
| Records with first-token top-five probabilities | 24,008 |
| Unique prompt hashes | 24,008 |
| Input-truncated records | 214 (0.89%) |
| OOM retries | 0 |
| Empty responses | 1 |
| Runtime | 4,670.77 seconds |

The output contains exactly the 24,008 retained test record numbers from the
manifest, with no duplicates or missing records.

## 6. Class and prediction distributions

| Quantity | Count | Percentage of all records |
|---|---:|---:|
| Ground-truth `target=0` | 23,486 | 97.83% |
| Ground-truth `target=1` | 522 | 2.17% |
| Predicted `YES` | 23,788 | 99.08% |
| Predicted `NO` | 10 | 0.04% |
| Unparseable response | 210 | 0.87% |

The model again strongly favored `YES`, closely matching the behavior observed
on the retained validation partition. This is not a target-mapping error:
`YES` is the intended response for `target=1`.

## 7. Confusion matrix and response resolution

Unparseable responses are reported separately and are not silently converted
to `NO`.

| Ground truth | Predicted `YES` | Predicted `NO` | Unparseable | Total |
|---|---:|---:|---:|---:|
| `target=0` | 23,309 false positives | 8 true negatives | 169 | 23,486 |
| `target=1` | 479 true positives | 2 false negatives | 41 | 522 |
| **Total** | **23,788** | **10** | **210** | **24,008** |

## 8. Raw baseline metrics

| Metric | Value | Interpretation |
|---|---:|---|
| Overall exact accuracy, unresolved responses counted as incorrect | 2.03% | 487 correct decisions out of 24,008 |
| Parseable decision coverage | 99.13% | 23,798 records produced `YES` or `NO` |
| Accuracy among parseable decisions | 2.05% | 487 correct decisions out of 23,798 |
| Precision of `YES` predictions | 2.01% | 479 true positives among 23,788 flags |
| Recall among parseable decisions | 99.58% | 479 true positives and 2 parseable false negatives |
| Vulnerable records receiving `YES` | 91.76% | 479 of 522 vulnerable records |
| Non-vulnerable records explicitly flagged `YES` | 99.25% | 23,309 of 23,486 non-vulnerable records |

The parseable recall is accompanied by extremely low flag precision. The
model's raw output behaves close to an always-flag rule and is therefore not
suitable as a final automated decision rule without selective gating.

## 9. Interpretation

The locked-test run demonstrates that the pinned open-source model and the
manifest-aware Colab pipeline can process the complete retained test
partition. It also confirms that the model's near-always-YES behavior is not
limited to validation data.

The raw test baseline is useful for measuring the effect of the frozen
validation-derived policy. It must not itself be presented as the final
system performance. In particular, the high number of false positives and the
210 unresolved generations show why calibration, conformal abstention, and
static corroboration are required by the Thesis methodology.

## 10. Limitations and reporting rules

1. This report describes raw test inference only; it is not the final hybrid
   test evaluation.
2. The 210 unparseable responses remain unresolved and are not `NO` decisions.
3. The 214 truncated inputs are part of the declared 4,096-token protocol and
   must be disclosed.
4. The retained top-five token values are raw diagnostics, not calibrated
   probabilities.
5. No calibration parameters or thresholds were fitted using test labels.
6. Semgrep corroboration and the frozen conformal policy have not yet been
   applied to this test output.

## 11. Reproducibility artifacts

| Artifact | Location |
|---|---|
| Full JSONL results | [qwen_test_results.jsonl](C:/Users/rehan/OneDrive/Desktop/Thesis/implementation/qwen_test_results.jsonl) |
| Full-run metadata | [qwen_test_results.jsonl.meta.json](C:/Users/rehan/OneDrive/Desktop/Thesis/implementation/qwen_test_results.jsonl.meta.json) |
| Test Colab notebook | [primevul_qwen_test_colab.ipynb](C:/Users/rehan/Documents/Codex/2026-10-05/i-want-all-the-chats-and/work/primevul_qwen_test_colab.ipynb) |
| Archived notebook snapshot | [primevul_qwen_test_colab.ipynb](C:/Users/rehan/Documents/Codex/2026-10-05/i-want-all-the-chats-and/outputs/thesis-codex-context/scripts/primevul_qwen_test_colab.ipynb) |
| Leakage-controlled manifest | [thesis_primevul_leakage_controlled_manifest.json](C:/Users/rehan/OneDrive/Desktop/Thesis/datasets/PrimeVul/PrimeVul_v0.1-20260930T034251Z-1-001/PrimeVul_v0.1/thesis_primevul_leakage_controlled_manifest.json) |
| Frozen-test protocol | [LOCKED_TEST_PROTOCOL.md](C:/Users/rehan/Documents/Codex/2026-10-05/i-want-all-the-chats-and/work/LOCKED_TEST_PROTOCOL.md) |

### Artifact SHA-256 checksums

| Artifact | SHA-256 |
|---|---|
| `qwen_test_results.jsonl` | `27B584B4C7CD8B5DF188CCA597A7906D29D6DE9097E431F89CBE572794DEE3DD` |
| `qwen_test_results.jsonl.meta.json` | `B4AF5F430E435F4BC56A7883D43A4FF3CAB9B78262C72AD1652BFAAA7533C096` |
| `thesis_primevul_leakage_controlled_manifest.json` | `4D19F14509EDDB7A68FF4E8118954572886A885D150FD70347C02C86A08934D4` |

## 12. Thesis-ready result statement

> The pinned `Qwen/Qwen2.5-Coder-1.5B-Instruct` model was evaluated on all
> 24,008 records retained by the leakage-controlled PrimeVul test manifest
> using a code-only YES/NO prompt and greedy decoding. The model produced
> parseable decisions for 99.13% of records and predicted `YES` for 23,788
> records. It produced 479 true positives, 23,309 false positives, 8 true
> negatives, and 2 parseable false negatives; 210 outputs were unparseable.
> Consequently, raw flag precision was 2.01% and overall accuracy was 2.03%
> when unresolved outputs were counted as incorrect. These values describe the
> pre-gating raw LLM baseline, not the final calibrated or hybrid test result.

