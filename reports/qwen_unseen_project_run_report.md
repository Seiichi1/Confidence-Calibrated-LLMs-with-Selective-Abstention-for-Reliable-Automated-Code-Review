# Qwen Unseen-Project Evaluation Run Report

## Status

Complete. The full Qwen inference run processed every record retained by the
unseen-project holdout manifest exactly once. This is a raw Qwen baseline, not
yet the final hybrid-policy result.

## Run artifacts

| Artifact | Absolute path |
|---|---|
| Qwen JSONL output | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\qwen_unseen_project_results.jsonl` |
| Qwen metadata | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\qwen_unseen_project_results.jsonl.meta.json` |
| Holdout manifest | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\primevul_unseen_project_holdout_manifest.json` |
| Colab notebook | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\primevul_qwen_unseen_project_colab.ipynb` |
| Source partition | `C:\Users\rehan\OneDrive\Desktop\Thesis\datasets\PrimeVul\PrimeVul_v0.1-20260930T034251Z-1-001\PrimeVul_v0.1\primevul_train.jsonl` |

## Execution configuration

| Parameter | Value |
|---|---|
| Model | `Qwen/Qwen2.5-Coder-1.5B-Instruct` |
| Hugging Face revision | `2e1fd39` |
| Device | `cuda:0` |
| Dtype | `torch.float16` |
| Partition | `unseen_project_holdout` |
| Sample count | `0` = all retained records |
| Records processed | 38,362 |
| Maximum new tokens | 16 |
| Maximum input tokens | 4,096 |
| OOM retries | 0 |
| Input truncations | 326 |
| Elapsed time | 8,243.905 seconds, approximately 2 hours 17 minutes 24 seconds |
| Prompt contract | Code-only YES/NO classification |

## Integrity checks

| Check | Result |
|---|---:|
| Manifest-retained records | 38,362 |
| JSONL output records | 38,362 |
| Missing record numbers | 0 |
| Duplicate record numbers | 0 |
| Extra record numbers | 0 |
| Target-0 records | 37,284 |
| Target-1 records | 1,078 |

The minimum and maximum raw JSONL line numbers were 2 and 175,797. The missing
line 1 and other gaps are expected because the holdout manifest retains only
whole projects that are absent from the official validation and test projects.

## Raw prediction results

| Outcome | Count | Percentage of all records |
|---|---:|---:|
| YES | 38,025 | 99.12% |
| NO | 15 | 0.04% |
| Unparseable | 322 | 0.84% |

Against the PrimeVul targets, with unresolved outputs treated as incorrect for
the conservative recall calculation:

| Quantity | Count |
|---|---:|
| True positives (`target=1`, prediction YES) | 1,008 |
| False positives (`target=0`, prediction YES) | 37,017 |
| True negatives (`target=0`, prediction NO) | 14 |
| Parseable false negatives (`target=1`, prediction NO) | 1 |
| Unresolved vulnerable records | 69 |
| Unresolved non-vulnerable records | 253 |

The raw YES-alert precision is 2.65% (`1,008 / 38,025`). Vulnerable-record
recall is 93.51% (`1,008 / 1,078`) when the 69 unresolved vulnerable outputs
are counted as missed. Among only the 1,009 vulnerable records with a parseable
YES/NO response, the conditional recall is 99.90%; this conditional quantity
must not replace the conservative all-record recall in the thesis.

## Interpretation

The model again exhibits the same severe positive-class bias observed on the
official validation and test partitions. It identifies most vulnerable
examples, but it flags almost every non-vulnerable example as vulnerable. Thus,
the raw Qwen result does not demonstrate an improvement in operational
precision or alert burden.

This result does demonstrate that the new candidate executed correctly and
that project-held-out evaluation is feasible. The candidate remains useful for
the next comparison because it contains 1,078 vulnerable records from 400
projects not present in official validation or test.

## Required next analysis

Run the same Semgrep corroboration protocol on the 38,362 candidate records,
then apply without refitting:

1. the original frozen alpha `0.10` policy; and
2. the validation-selected higher-recall alpha `0.50` candidate policy.

Only after those outputs exist can the project-held-out precision, coverage,
and positive recall be compared with the official locked-test results. The
candidate labels must not be used to select a new operating point.

