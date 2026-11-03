# Qwen–Semgrep Validation-Only Corroboration Report

**Stage:** Static-analysis corroboration baseline  
**Date:** 2026-10-26  
**LLM:** `Qwen/Qwen2.5-Coder-1.5B-Instruct`, pinned revision `2e1fd39`  
**Analyzer:** Semgrep Community Edition `1.163.0`  
**Partition:** Retained validation only; the retained test partition was not read

## 1. Purpose and scope

This experiment tests whether a lightweight static-analysis signal can provide
independent corroboration for the LLM-only validation baseline. The analyzer
was applied after the dataset audit, clean baseline, calibration, and
validation-only conformal experiment. It was not used to fit the calibrator or
to alter the locked test partition.

PrimeVul supplies function snippets rather than complete, buildable repository
trees. Therefore the first analyzer is a deterministic, local Semgrep rule
pack over isolated C/C++ snippets. It is a corroboration baseline, not a
semantic vulnerability oracle.

## 2. Input and execution

The scan processed the 23,033 records represented in the clean retained Qwen
validation output. The raw validation JSONL was used only to recover each
function body by `idx`; the Qwen JSONL supplied the retained-record list,
prediction, and target. Each function was written to a temporary `.c` file
outside the project directory. The scan ran in 45 batches of at most 512
records to avoid the Windows large-directory hang observed with a single
23,033-file Semgrep invocation. Temporary source files were deleted after the
scan, and neither the raw dataset nor the Qwen output was modified.

The local rules cover three auditable syntactic families:

1. unbounded copy/format operations such as `strcpy`, `strcat`, `sprintf`,
   `vsprintf`, and `gets`;
2. command execution through `system` and `popen`-like calls;
3. low-level memory operations such as `memcpy`, `memmove`, and `memset`.

The complete rule file is `work/semgrep_primevul_rules.yml`.

## 3. Conservative corroboration policy

The target mapping remains `target=1` = vulnerability present and `target=0` =
no vulnerability. A Semgrep finding is recorded as static `YES`; no finding is
recorded as `NO_FINDING`, not as a proof of safety.

For the LLM relation:

- `AGREE`: parsed LLM `YES` and at least one Semgrep finding;
- `DISAGREE`: parsed LLM `NO` and at least one Semgrep finding;
- `NEUTRAL`: no finding, unparseable LLM output, or unavailable scan.

This asymmetric policy avoids treating limited rule coverage as evidence that a
function is secure.

## 4. Results

### 4.1 Analyzer-level counts

| Quantity | Count | Rate/interpretation |
|---|---:|---|
| Records scanned | 23,033 | 100% of retained validation output |
| Records with at least one finding | 1,823 | 7.91% of records |
| Records with no finding | 21,210 | Neutral, not safe |
| Static true positives | 133 | `target=1` with a finding |
| Static positive precision | 7.30% | 133 / 1,823 |
| Static positive recall | 23.75% | 133 / 560 vulnerable records |
| Static false-positive rate | 7.52% | 1,690 / 22,473 non-vulnerable records |

The target-by-analyzer table was:

| Target | Static finding | No finding |
|---:|---:|---:|
| 0 | 1,690 | 20,783 |
| 1 | 133 | 427 |

The rule match totals were 803 for the unsafe-copy/format family, 8 for the
command-execution family, and 2,758 for the low-level-memory family. These are
finding totals rather than unique-record totals, so one function can contribute
more than one rule match.

### 4.2 LLM–analyzer relation

| Relation | Count | Interpretation |
|---|---:|---|
| `AGREE` | 1,743 | LLM `YES` plus a static finding |
| `DISAGREE` | 1 | LLM `NO` plus a static finding |
| `NEUTRAL` | 21,289 | No finding or unresolved LLM output |

Among the `AGREE` records, 116 had `target=1` and 1,627 had `target=0`. The
single `DISAGREE` record had `target=0`, so the static finding contradicted the
LLM's `NO` decision on a non-vulnerable labeled record. Seventeen vulnerable
records had a static finding but an unparseable LLM response and were therefore
kept neutral under the conservative policy.

## 5. Interpretation

The rule pack provides a measurable independent signal, but its positive
precision is only 7.30% and its positive recall is 23.75% on this validation
sample. The high number of low-level memory-operation matches shows why a raw
API-presence rule cannot be treated as a confirmed vulnerability detector.

The corroboration signal should therefore be used as a review-prioritization
and escalation feature rather than as an automatic relabeling mechanism. In
the next pipeline comparison, the appropriate conditions are:

1. LLM accepted by the conformal gate;
2. LLM abstained but static analysis reports a finding;
3. LLM and static analysis both report positive evidence;
4. neither source provides positive evidence.

These conditions must be evaluated with the same validation records and later
with a frozen policy on the locked test partition. No category in this report
proves semantic leakage or semantic vulnerability.

## 6. Limitations

- The scan is function-local and cannot perform repository-level data-flow,
  interprocedural, build-aware, or dependency-aware analysis.
- The rules cover a deliberately small and auditable subset of security
  patterns; absence of a finding is neutral.
- The isolated snippets may omit declarations, macros, and surrounding context
  required for deeper analysis.
- Semgrep open-source C/C++ support is not equivalent to a complete repository-
  level CodeQL or commercial interfile analysis. A stronger analyzer remains a
  possible follow-up if complete repositories become available.
- The results are validation-stage results and do not justify changing labels,
  deleting records, or opening the final test partition.

## 7. Reproducibility

| Item | Value |
|---|---|
| Adapter | [run_semgrep_corroboration.py](C:/Users/rehan/Documents/Codex/2026-10-05/i-want-all-the-chats-and/work/run_semgrep_corroboration.py) |
| Rule pack | [semgrep_primevul_rules.yml](C:/Users/rehan/Documents/Codex/2026-10-05/i-want-all-the-chats-and/work/semgrep_primevul_rules.yml) |
| Archived adapter snapshot | [run_semgrep_corroboration.py](C:/Users/rehan/Documents/Codex/2026-10-05/i-want-all-the-chats-and/outputs/thesis-codex-context/scripts/run_semgrep_corroboration.py) |
| Archived rule-pack snapshot | [semgrep_primevul_rules.yml](C:/Users/rehan/Documents/Codex/2026-10-05/i-want-all-the-chats-and/outputs/thesis-codex-context/scripts/semgrep_primevul_rules.yml) |
| Protocol | [STATIC_CORROBORATION_PROTOCOL.md](C:/Users/rehan/Documents/Codex/2026-10-05/i-want-all-the-chats-and/work/STATIC_CORROBORATION_PROTOCOL.md) |
| Full JSON artifact | `C:/Users/rehan/AppData/Local/Temp/thesis_semgrep_valid_full.json` |
| Semgrep version | `1.163.0` |
| Batch size | 512 records |
| Final test used | No |


