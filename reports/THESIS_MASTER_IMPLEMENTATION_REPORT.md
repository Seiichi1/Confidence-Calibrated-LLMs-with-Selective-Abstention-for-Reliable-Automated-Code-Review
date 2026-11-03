# Thesis Master Implementation Report

## Confidence-Calibrated LLMs with Selective Abstention for Reliable Automated Code Review

**Prepared for:** Thesis research-paper writing  
**Reporting date:** 2026-10-27  
**Primary dataset:** PrimeVul v0.1  
**Primary model:** `Qwen/Qwen2.5-Coder-1.5B-Instruct`, Hugging Face revision `2e1fd39`  
**Document status:** Consolidated implementation record; core locked-test study and independent project-held-out improvement evaluation complete; optional chapter extensions remain open

---

## 1. Purpose and scope of this document

This document is the master implementation and evidence record for the Thesis.
It consolidates the work performed from initial dataset selection through the
completed locked-test evaluation and statistical sensitivity analyses. It is
intended to support direct preparation of the research paper by providing:

1. the complete project history, progress, and decision rationale;
2. the implemented methodology and its relationship to the source chapter;
3. all scripts, notebooks, protocols, rules, and their absolute paths;
4. all principal generated outputs and their absolute paths;
5. thesis-ready tables containing the main quantitative results;
6. descriptions and caption drafts for figures that can be included in the
   paper; and
7. explicit boundaries between completed evidence, partial implementation,
   and experiments that remain open.

The original chapter is a methodology/proposal manuscript. It specifies a
broader experimental program than the currently completed Qwen/PrimeVul study.
Accordingly, this report does not silently present unperformed experiments as
completed results. The final paper must either report the implemented scope
accurately or perform the remaining experiments before claiming full coverage
of every chapter research question.

---

## 2. Executive summary

### 2.1 Research objective

The Thesis studies whether a code-specialized large language model can be made
more reliable for binary vulnerability review by combining:

1. a fixed code-only LLM baseline;
2. post-hoc confidence calibration;
3. conformal/selective abstention; and
4. static-analysis corroboration.

The intended operational behavior is not to force an automated answer for every
function. The system may accept a positive vulnerability alert or abstain and
escalate the record for manual review.

### 2.2 Dataset and leakage control

PrimeVul v0.1 was retained as the primary dataset because it supplies
function-level code, binary vulnerability labels, project and commit
provenance, CWE/CVE metadata, and predefined train/validation/test partitions.
The raw partitions were audited without modification.

A memory-bounded approximate near-duplicate scan processed all 224,533 raw
records using SQLite-backed token SimHash. Verification and provenance review
identified 2,872 strong approximate cross-partition candidates, including
1,795 high-priority provenance overlaps. A conservative derived manifest
excluded 915 validation records and 780 test records while keeping all raw
JSONL files unchanged.

### 2.3 Model and frozen evaluation

The primary model is the open-source
`Qwen/Qwen2.5-Coder-1.5B-Instruct` checkpoint at pinned revision `2e1fd39`.
Inference used a deterministic, code-only YES/NO prompt and retained first-token
top-five probabilities for later confidence analysis.

The validation partition was used for calibration, conformal construction,
static corroboration, ablation, and operating-policy selection. The retained
test partition was then evaluated under the frozen policy without using test
labels for fitting or policy selection.

### 2.4 Main locked-test result

| Method | Coverage | Accepted-positive precision | Positive recall | Interpretation |
|---|---:|---:|---:|---|
| Raw Qwen | 99.08% | 2.01% | 91.76% | Near-always-positive baseline |
| Temperature + conformal only | 9.66% | 4.66% | 20.69% | More selective, still low precision |
| Semgrep only | 6.31% | 6.87% | 19.92% | Static positive-alert baseline |
| Frozen hybrid | 1.88% | 7.96% | 6.90% | Most selective and highest point precision |

The frozen hybrid improved accepted-positive precision over raw Qwen by 5.95
percentage points, but reduced positive recall by 84.87 percentage points. It
should therefore be described as a selective high-precision review-triage mode,
not as a high-recall vulnerability detector.

### 2.5 Overall conclusion

The completed evidence supports the following bounded conclusion:

> Validation-derived calibration, conformal abstention, and Semgrep
> corroboration can reduce the false-alert burden of the raw Qwen baseline and
> improve precision among accepted positive alerts. The improvement is obtained
> through aggressive abstention and therefore comes with a substantial loss in
> coverage and vulnerable-record recall.

The original locked-test study does not establish unseen-project generalization,
universal model superiority, or that Semgrep findings are semantic
vulnerability ground truth. A subsequent project-held-out candidate now
provides an independent mixed-trade-off check, but it does not establish
universal generalization or high-recall autonomous detection.

### 2.6 First higher-recall candidate study

An additional validation-only sweep selected a temperature-scaled conformal
policy with `alpha=0.50` plus Semgrep corroboration under a 20% validation
positive-recall floor. When transferred to the existing test output, this
candidate increased positive recall from 6.90% to 15.13% and coverage from
1.88% to 5.09%, while reducing accepted-positive precision from 7.96% to
6.47%. This is an exploratory operating-point comparison; the original
alpha=0.10 policy remains the primary frozen result and a new untouched holdout
is required before claiming a final improved system.

---

## 3. Source chapter and research requirements

The source chapter is:

`C:\Users\rehan\OneDrive\Desktop\Thesis\draft\chapter.pdf`

The chapter defines the binary task as follows:

- `target=1`: an actionable defect or vulnerability is present; the expected
  model response is `YES`.
- `target=0`: no actionable defect or vulnerability is present under the chosen
  taxonomy; the expected model response is `NO`.

### 3.1 Research questions in the chapter

The chapter specifies five main research questions:

1. How do rule-based static-analysis and LLM-based review compare on precision,
   recall, F1, and false-positive rate across defect categories?
2. What is the calibration behavior of instruction-tuned LLMs, including
   verbal confidence, logit-based confidence, and self-consistency sampling?
3. Does post-hoc calibration using temperature scaling, Platt scaling, or an
   ensemble reduce ECE and Brier score, and does calibration vary by category,
   code complexity, and language?
4. Does calibration-driven conformal abstention improve precision of accepted
   reviews while maintaining acceptable coverage?
5. Does rule corroboration provide an independent reliability signal, or are
   LLM and static-analysis errors strongly correlated?

### 3.2 Proposed architecture in the chapter

The chapter proposes this seven-stage architecture:

1. normalize benchmark review instances;
2. run an instruction-tuned LLM;
3. extract verbal confidence, logit confidence, and self-consistency features;
4. fit temperature and Platt calibration on a calibration split;
5. apply a conformal abstention gate at `alpha=0.10`;
6. incorporate static-analysis corroboration using AGREE, DISAGREE, and NEUTRAL
   relations; and
7. emit a reliability tier, escalation flag, and human-review recommendation.

### 3.3 Proposed evaluation and ablations

The chapter proposes five principal settings:

1. LLM-only baseline;
2. LLM plus post-hoc calibration;
3. LLM plus calibration and conformal abstention;
4. full pipeline with static corroboration; and
5. a calibrator comparison involving temperature scaling, Platt scaling, and
   an ensemble.

The chapter also proposes precision, recall, F1, accuracy, false-positive rate,
ECE, Brier score, reliability diagrams, AUROC, Precision@Accepted, coverage,
abstention rate, error-reject curves, paired comparisons, Pearson correlation,
and Cohen's kappa.

---

## 4. Chronological project history and decisions

### 4.1 Project framing and initial methodological decision

The project began from a methodology/proposal chapter rather than an empirical
paper. The initial implementation order was fixed as:

```text
dataset and protocol
    -> LLM-only baseline
    -> confidence calibration
    -> conformal/selective abstention
    -> static-analysis corroboration
    -> ablations and statistical analysis
```

The key guardrail was that the final test partition could not be used to fit a
calibrator, choose a threshold, choose a rule pack, or select a policy.

### 4.2 PrimeVul selection

PrimeVul was selected provisionally because it provides function-level source
code, binary targets, project and commit metadata, file provenance, CWE/CVE
fields, and supplied train/validation/test partitions. The raw partitions were
treated as the primary audit target; the balanced paired files were not treated
as substitutes for the natural benchmark distribution.

### 4.3 Raw dataset audit

All supplied raw partitions were parsed and checked for invalid or blank rows.
The audit compared exact code identity, canonicalized code identity, function
hashes, index values, project overlap, commit overlap, and file provenance.
Simple exact-duplicate leakage was not found, but project, commit, and file
provenance overlap motivated similarity review.

### 4.4 Near-duplicate scan redesign

The first similarity audit retained large Python sets alongside the similarity
index and did not complete reliably. The scan was redesigned as a standalone,
memory-bounded SQLite process. This decision was made to guarantee completion,
bound memory usage, and preserve raw dataset files.

### 4.5 Verification and provenance policy

SimHash candidates were verified with token 5-gram Jaccard similarity and then
joined to project/file/commit provenance. Similarity candidates were not
automatically called semantic duplicates. The evidence was instead used to
identify high-priority records requiring conservative exclusion from evaluation.

### 4.6 Leakage-controlled manifest

The derived manifest retained all train records, excluded high-priority overlap
records from validation and test, and preserved the raw files. The manifest is
a reporting and evaluation control, not a rewritten dataset.

### 4.7 Code-only baseline decision

The first LLM prompt was intentionally code-only. CWE, CVE, project, commit,
file, and hash metadata were retained for audit and analysis but were excluded
from the initial prompt to prevent metadata leakage.

### 4.8 Model decision

The chapter named GPT-4o and DeepSeek-Coder as examples. The actual primary
model was changed to the open-source
`Qwen/Qwen2.5-Coder-1.5B-Instruct` at revision `2e1fd39` because it is
code-specialized, Apache-2.0 licensed, compatible with the available hardware,
and capable of retaining token-level diagnostics for calibration.

### 4.9 Validation development and policy freeze

The validation partition was used for baseline measurement, calibration,
conformal construction, Semgrep corroboration, hybrid ablation, and a
cost-sensitive operating-policy sweep. Temperature scaling plus a positive
Semgrep finding was selected at `alpha=0.10` under an illustrative cost model
with false-negative cost 10, false-positive cost 1, review cost 0.5, and a
minimum positive-recall floor of 10%.

### 4.10 Locked test and statistical analysis

The selected policy was frozen before the test evaluation. The test output was
then joined to Semgrep and policy artifacts by record number. Record-level and
project-clustered paired bootstrap analyses were completed after the locked
evaluation.

### 4.11 Decision log

| Date | Decision | Reason and consequence |
|---|---|---|
| 2026-10-06 | Use PrimeVul provisionally and audit supplied partitions before splitting | Prevent unsupported leakage-free claims and preserve natural distributions |
| 2026-10-06 | Use a code-only binary baseline | Measure code evidence without CWE/CVE/project metadata leakage |
| 2026-10-06 | Use a manifest-aware protocol | Preserve raw files while excluding high-priority overlap from evaluation |
| 2026-10-07 | Select Qwen 1.5B at revision `2e1fd39` | Open-source, code-specialized, hardware-compatible, and logit-capable |
| 2026-10-26 | Complete clean retained validation baseline | Establish the raw LLM behavior before calibration or static corroboration |
| 2026-10-26 | Fit temperature and Platt calibration on validation only | Separate probability calibration from decision threshold selection |
| 2026-10-26 | Implement split-conformal abstention | Quantify coverage, abstention, accepted precision, and positive acceptance |
| 2026-10-26 | Select Semgrep as first static corroboration baseline | Function snippets do not provide complete repository/build context for CodeQL-style analysis |
| 2026-10-26 | Freeze temperature + conformal + Semgrep positive gate | Satisfy the selected validation recall guardrail under the illustrative cost model |
| 2026-10-27 | Complete raw test inference | Establish the locked-test pre-gating baseline without test-driven tuning |
| 2026-10-27 | Complete frozen hybrid test evaluation | Measure the final selected policy on 24,008 retained records |
| 2026-10-27 | Complete record-level paired bootstrap | Quantify uncertainty and compare component ablations on identical records |
| 2026-10-27 | Complete project-clustered paired bootstrap | Assess sensitivity to project-level dependence without changing the policy |
| 2026-10-27 | Draft thesis results/discussion tables | Make the quantitative evidence directly usable in the research paper |
| 2026-10-27 | Run validation-only higher-recall policy sweep and apply alpha=0.50 candidate | Test whether a less conservative corroborated gate improves recall; the candidate raised test recall to 15.13% but reduced precision to 6.47%, so it remains exploratory |

---

## 5. Dataset, provenance, and leakage-control results

### 5.1 Raw dataset locations

The supplied PrimeVul directory is:

`C:\Users\rehan\OneDrive\Desktop\Thesis\datasets\PrimeVul\PrimeVul_v0.1-20260930T034251Z-1-001\PrimeVul_v0.1`

Raw partitions:

- `C:\Users\rehan\OneDrive\Desktop\Thesis\datasets\PrimeVul\PrimeVul_v0.1-20260930T034251Z-1-001\PrimeVul_v0.1\primevul_train.jsonl`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\datasets\PrimeVul\PrimeVul_v0.1-20260930T034251Z-1-001\PrimeVul_v0.1\primevul_valid.jsonl`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\datasets\PrimeVul\PrimeVul_v0.1-20260930T034251Z-1-001\PrimeVul_v0.1\primevul_test.jsonl`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\datasets\PrimeVul\PrimeVul_v0.1-20260930T034251Z-1-001\PrimeVul_v0.1\file_info.json`

Balanced paired files were present but were not used as the leakage-audit
target:

- `C:\Users\rehan\OneDrive\Desktop\Thesis\datasets\PrimeVul\PrimeVul_v0.1-20260930T034251Z-1-001\PrimeVul_v0.1\primevul_train_paired.jsonl`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\datasets\PrimeVul\PrimeVul_v0.1-20260930T034251Z-1-001\PrimeVul_v0.1\primevul_valid_paired.jsonl`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\datasets\PrimeVul\PrimeVul_v0.1-20260930T034251Z-1-001\PrimeVul_v0.1\primevul_test_paired.jsonl`

### Table 1. Raw partition counts

| Partition | Records | Vulnerable `target=1` | Vulnerability rate | Invalid/blank |
|---|---:|---:|---:|---:|
| Train | 175,797 | 4,862 | 2.77% | 0 |
| Validation | 23,948 | 593 | 2.48% | 0 |
| Test | 24,788 | 549 | 2.21% | 0 |
| **Total** | **224,533** | **6,004** | — | **0** |

### Table 2. Exact identity and provenance findings

| Check | Result |
|---|---|
| Exact raw-code hash cross-partition overlap | 0 |
| Whitespace-canonical code hash cross-partition overlap | 0 |
| `func_hash` cross-partition overlap | 0 |
| `idx` cross-partition overlap | 0 |
| Shared projects, train/validation | 162 |
| Shared projects, train/test | 146 |
| Shared projects, validation/test | 83 |
| Shared commits, train/validation | 13 |
| Shared commits, train/test | 14 |
| Shared commits, validation/test | 0 |
| Shared file hashes, train/validation | 198 |
| Shared file hashes, train/test | 164 |
| Shared file hashes, validation/test | 37 |

### Table 3. `file_info.json` provenance coverage

| Partition | Records with file-info coverage | Total records |
|---|---:|---:|
| Train | 120,537 | 175,797 |
| Validation | 19,649 | 23,948 |
| Test | 18,878 | 24,788 |

### Table 4. Approximate near-duplicate scan

| Pair | Candidates |
|---|---:|
| Train/validation | 3,561,232 |
| Train/test | 3,994,695 |
| Validation/test | 70,936 |
| **Total** | **7,626,863** |

Scan parameters:

- token-based 64-bit SimHash;
- four 16-bit bands;
- minimum function length: 20 tokens;
- deterministic cap of 256 evenly spaced tokens for SimHash;
- maximum band bucket size: 256 records;
- Hamming distance threshold: 8;
- SQLite index outside the project directory;
- cross-partition candidates only; within-partition pairs excluded.

### Table 5. Verified token 5-gram similarity candidates

| Pair | Candidates with Jaccard >= 0.8 |
|---|---:|
| Train/validation | 1,320 |
| Train/test | 1,351 |
| Validation/test | 201 |
| **Total** | **2,872** |

The verified candidates had Jaccard values from 0.8 to 1.0, with a mean of
approximately 0.900. These are approximate similarity findings, not automatic
semantic-duplicate or leakage labels.

### Table 6. Provenance classifications among verified candidates

| Classification | Pairs | Interpretation |
|---|---:|---|
| Same file/path | 1,745 | Same project file path or file identity across partitions |
| Shared commit | 50 | Same commit without the higher-priority same-file/path relation |
| Same project only | 496 | Same project but no shared file/path or commit |
| Cross-project | 581 | Different projects with strong approximate code similarity |
| **Total** | **2,872** | — |

No verified pair was an exact raw-code or whitespace-canonical match. The high-
priority group therefore represents likely historical or related code
evolution rather than byte-identical duplication.

### Table 7. High-priority provenance triage

| Quantity | Count |
|---|---:|
| High-priority pairs | 1,795 |
| Same project file path across different commits | 1,744 |
| Shared commit | 51 |
| Vulnerable/non-vulnerable label boundary | 82 |
| Non-vulnerable/non-vulnerable | 1,674 |
| Vulnerable/vulnerable | 39 |
| Connected components | 1,486 |
| Largest connected component | 7 records |

### Table 8. Records affected by high-priority pairs

| Partition | Records in at least one high-priority pair |
|---|---:|
| Train | 1,531 |
| Validation | 915 |
| Test | 780 |
| **Total** | **3,226** |

### Table 9. Leakage-controlled manifest roles

| Role | Total | Excluded | Retained |
|---|---:|---:|---:|
| Train | 175,797 | 0 | 175,797 |
| Validation/calibration | 23,948 | 915 | 23,033 |
| Locked test | 24,788 | 780 | 24,008 |

Excluded validation records included 882 non-vulnerable and 33 vulnerable
records. Excluded test records included 753 non-vulnerable and 27 vulnerable
records. Exclusion is conservative and does not prove that every excluded row
is semantically leaked.

---

## 6. Baseline protocol and model

### 6.1 Prompt and inference controls

| Configuration | Value |
|---|---|
| System instruction | `You are a security expert that is good at static program analysis.` |
| User input | Function code plus request for exactly `YES` or `NO` |
| Metadata in initial prompt | None; no CWE, CVE, project, commit, file, or hash |
| Model | `Qwen/Qwen2.5-Coder-1.5B-Instruct` |
| Hugging Face revision | `2e1fd39` |
| Dtype | `torch.float16` |
| Device | `cuda:0` |
| Decoding | Greedy, `do_sample=False` |
| Seed | `12345` |
| Maximum output tokens | 16 |
| Maximum input tokens | 4,096 |
| OOM retry budget | 2,048 input tokens |
| Top-token diagnostics | Top-five probabilities retained |

### 6.2 Label mapping

| Dataset target | Meaning | Expected response |
|---:|---|---|
| `0` | No actionable vulnerability | `NO` |
| `1` | Actionable vulnerability present | `YES` |

This mapping was checked in both validation and test reports. The near-
always-`YES` output was model behavior, not an inversion of the target values.

### 6.3 Why PrimeVul train was not used for model fine-tuning

The completed study is a zero-shot evaluation of a pretrained open-source
model. PrimeVul train was used for dataset and provenance audit, but no Qwen
fine-tuning was performed. This is valid for a zero-shot baseline and keeps the
core study focused on calibration and selective prediction. If the paper keeps
language implying that the model was trained or fine-tuned on PrimeVul train,
that wording must be changed or a separate fine-tuning experiment must be
performed.

---

## 7. Validation experiments and results

### 7.1 Clean validation baseline

The model processed all 23,033 retained validation records. It produced 22,837
`YES` responses, 19 `NO` responses, and 177 unparseable responses.

### Table 10. Validation baseline confusion matrix

| Ground truth | Predicted `YES` | Predicted `NO` | Unparseable | Total |
|---|---:|---:|---:|---:|
| `target=0` | 22,313 false positives | 19 true negatives | 141 | 22,473 |
| `target=1` | 524 true positives | 0 parseable false negatives | 36 | 560 |
| **Total** | **22,837** | **19** | **177** | **23,033** |

### Table 11. Validation baseline metrics

| Metric | Value |
|---|---:|
| Overall exact accuracy, unresolved counted incorrect | 2.36% |
| Parseable decision coverage | 99.23% |
| Accuracy among parseable decisions | 2.38% |
| Precision of `YES` predictions | 2.29% |
| Recall among parseable decisions | 100.00% |
| Vulnerable records receiving `YES` | 93.57% |
| Non-vulnerable records flagged `YES` | 99.29% |

### 7.2 Post-hoc calibration

For 22,850 records, the retained first-token probabilities contained both
`YES` and `NO`. The diagnostic probability was:

```text
p_yes_pair = p(YES) / (p(YES) + p(NO))
score = log(p_yes_pair / (1 - p_yes_pair))
```

The records were split deterministically and stratified using seed `12345`.

### Table 12. Calibration split

| Split | Records | Target 0 | Target 1 |
|---|---:|---:|---:|
| Calibration fit | 18,279 | 17,860 | 419 |
| Held-out validation evaluation | 4,571 | 4,466 | 105 |
| Missing pairwise score | 183 | Not fitted | Not fitted |

### Table 13. Calibration parameters

| Method | Parameterization | Fitted value |
|---|---|---|
| Temperature scaling | `sigmoid(score / T)` | `T=445.683640902898` |
| Platt scaling | `sigmoid(a*score+b)` | `a=1.5423058083548482`, `b=-5.991508345905061` |

### Table 14. Held-out validation calibration metrics

| Method | Accuracy | Precision `YES` | Recall `YES` | Brier | Log loss | ECE, 10 bins |
|---|---:|---:|---:|---:|---:|---:|
| Raw pairwise score | 2.32% | 2.30% | 100.00% | 0.6166 | 1.5716 | 0.7699 |
| Temperature scaling | 2.32% | 2.30% | 100.00% | 0.2507 | 0.6946 | 0.4778 |
| Platt scaling | 97.70% | 0.00% | 0.00% | 0.0226 | 0.1065 | 0.0027 |

Platt scaling improved proper scoring under class imbalance but assigned every
held-out record a probability below 0.5, producing no positive predictions at
that threshold. This is why calibration and operating-threshold selection were
treated as separate decisions.

### 7.3 Validation conformal abstention

The scored validation records were separated into model-calibration,
conformal-calibration, and evaluation subsets. Only singleton prediction sets
were accepted as decisions; both-label and empty sets were abstentions.

### Table 15. Validation split-conformal partitions

| Role | Records | Target 0 | Target 1 |
|---|---:|---:|---:|
| Model-calibration split | 13,709 | 13,395 | 314 |
| Conformal-calibration split | 4,570 | 4,465 | 105 |
| Evaluation split | 4,571 | 4,466 | 105 |

### Table 16. Temperature conformal validation results

| Alpha | Set coverage | Abstention | Accepted records | Accepted precision | Accepted `YES` | Vulnerable accepted as `YES` |
|---:|---:|---:|---:|---:|---:|---:|
| 0.01 | 99.04% | 98.99% | 46 | 4.35% | 46 | 1.90% |
| 0.05 | 95.45% | 95.12% | 223 | 6.73% | 223 | 14.29% |
| 0.10 | 90.07% | 89.43% | 483 | 6.00% | 483 | 27.62% |
| 0.20 | 80.20% | 79.37% | 943 | 4.03% | 943 | 36.19% |
| 0.30 | 69.70% | 68.50% | 1,440 | 3.82% | 1,440 | 52.38% |
| 0.50 | 50.49% | 48.76% | 2,342 | 3.37% | 2,342 | 75.24% |

### Table 17. Platt conformal validation results

| Alpha | Set coverage | Abstention | Accepted records | Accepted precision | Accepted `YES` | Vulnerable accepted as `YES` |
|---:|---:|---:|---:|---:|---:|---:|
| 0.01 | 98.64% | 25.84% | 3,390 | 98.17% | 0 | 0.00% |
| 0.05 | 95.12% | 2.78% | 4,444 | 97.84% | 0 | 0.00% |
| 0.10 | 90.79% | 7.37% | 4,234 | 98.02% | 0 | 0.00% |
| 0.20 | 80.25% | 18.20% | 3,739 | 98.10% | 0 | 0.00% |
| 0.30 | 69.83% | 29.01% | 3,245 | 98.37% | 0 | 0.00% |
| 0.50 | 50.40% | 48.98% | 2,332 | 98.80% | 0 | 0.00% |

The Platt precision is dominated by accepted negative decisions and does not
represent useful positive-vulnerability detection.

### 7.4 Validation static corroboration

Semgrep Community Edition `1.163.0` was selected because the supplied dataset
contains isolated C/C++ function snippets rather than complete buildable
repositories. The auditable local rule pack covered unsafe copy/format calls,
command execution calls, and low-level memory operations.

### Table 18. Validation Semgrep results

| Quantity | Count | Rate/interpretation |
|---|---:|---|
| Records scanned | 23,033 | 100% of retained validation |
| Records with at least one finding | 1,823 | 7.91% |
| Records with no finding | 21,210 | Neutral, not safe |
| Static true positives | 133 | `target=1` with finding |
| Static positive precision | 7.30% | 133 / 1,823 |
| Static positive recall | 23.75% | 133 / 560 |
| Static false-positive rate | 7.52% | 1,690 / 22,473 |

### Table 19. Validation LLM–Semgrep relations

| Relation | Count | Interpretation |
|---|---:|---|
| `AGREE` | 1,743 | LLM `YES` plus static finding |
| `DISAGREE` | 1 | LLM `NO` plus static finding |
| `NEUTRAL` | 21,289 | No finding or unresolved LLM output |

Among `AGREE` records, 116 had `target=1` and 1,627 had `target=0`. The single
`DISAGREE` record had `target=0`. Seventeen vulnerable records had a static
finding but an unparseable LLM response and were retained as neutral.

### 7.5 Validation hybrid ablation

### Table 20. Temperature corroborated-positive validation gate

| Alpha | Coverage | Abstention | Accepted precision | Positive recall | Accepted records |
|---:|---:|---:|---:|---:|---:|
| 0.01 | 0.11% | 99.89% | 0.00% | 0.00% | 5 |
| 0.05 | 1.14% | 98.86% | 15.38% | 7.62% | 52 |
| 0.10 | 2.28% | 97.72% | 13.46% | 13.33% | 104 |
| 0.20 | 3.70% | 96.30% | 10.06% | 16.19% | 169 |
| 0.30 | 5.10% | 94.90% | 8.58% | 19.05% | 233 |
| 0.50 | 6.78% | 93.22% | 6.77% | 20.00% | 310 |

### Table 21. Platt corroborated-positive validation gate

| Alpha | Coverage | Abstention | Accepted precision | Positive recall | Accepted records |
|---:|---:|---:|---:|---:|---:|
| 0.01 | 0.00% | 100.00% | 0.00% | 0.00% | 0 |
| 0.05 | 0.00% | 100.00% | 0.00% | 0.00% | 0 |
| 0.10 | 0.00% | 100.00% | 0.00% | 0.00% | 0 |
| 0.20 | 0.00% | 100.00% | 0.00% | 0.00% | 0 |
| 0.30 | 0.00% | 100.00% | 0.00% | 0.00% | 0 |
| 0.50 | 0.00% | 100.00% | 0.00% | 0.00% | 0 |

The corroborated-positive gate improved temperature precision at the expense
of coverage and positive recall. The exploratory dual-signal negative gate was
not adopted because absence of a static finding is not evidence of safety.

### 7.6 Validation operating-policy sweep

The normalized cost was:

```text
cost = (10*false_negatives + 1*false_positives + 0.5*abstentions) / N
```

The sweep varied false-negative costs 5, 10, 20, 50, and 100; review costs
0.1, 0.25, 0.5, 1, and 2; and positive-recall floors 5%, 10%, and 20%.

### Table 22. Unconstrained default-cost candidate

| Candidate | Coverage | Abstention | Accepted precision | Positive recall | Normalized cost |
|---|---:|---:|---:|---:|---:|
| Platt conformal singleton, alpha=0.10 | 92.63% | 7.37% | 98.02% | 0.00% | 0.2206 |

This candidate was rejected because it accepts no vulnerable records as `YES`.

### Table 23. Recall-constrained validation candidates

| Minimum positive recall | Candidate | Alpha | Coverage | Abstention | Accepted precision | Positive recall | Normalized cost |
|---:|---|---:|---:|---:|---:|---:|---:|
| 5% | Temperature + corroborated positive | 0.05 | 1.14% | 98.86% | 15.38% | 7.62% | 0.5039 |
| 10% | Temperature + corroborated positive | 0.10 | 2.28% | 97.72% | 13.46% | 13.33% | 0.5083 |
| 20% | Temperature + corroborated positive | 0.50 | 6.78% | 93.22% | 6.77% | 20.00% | 0.5293 |

The alpha `0.10` temperature-plus-Semgrep policy was frozen for final test
evaluation under the selected 10% positive-recall guardrail.

---

## 8. Locked-test experiments and results

### 8.1 Raw locked-test baseline

The model processed all 24,008 retained test records with no missing or
duplicate record numbers.

### Table 24. Raw test class and prediction distribution

| Quantity | Count | Percentage |
|---|---:|---:|
| Ground-truth `target=0` | 23,486 | 97.83% |
| Ground-truth `target=1` | 522 | 2.17% |
| Predicted `YES` | 23,788 | 99.08% |
| Predicted `NO` | 10 | 0.04% |
| Unparseable response | 210 | 0.87% |

### Table 25. Raw test confusion matrix

| Ground truth | Predicted `YES` | Predicted `NO` | Unparseable | Total |
|---|---:|---:|---:|---:|
| `target=0` | 23,309 false positives | 8 true negatives | 169 | 23,486 |
| `target=1` | 479 true positives | 2 false negatives | 41 | 522 |
| **Total** | **23,788** | **10** | **210** | **24,008** |

### Table 26. Raw test metrics

| Metric | Value |
|---|---:|
| Overall exact accuracy, unresolved counted incorrect | 2.03% |
| Parseable decision coverage | 99.13% |
| Accuracy among parseable decisions | 2.05% |
| Precision of `YES` predictions | 2.01% |
| Recall among parseable decisions | 99.58% |
| Vulnerable records receiving `YES` | 91.76% |
| Non-vulnerable records explicitly flagged `YES` | 99.25% |

### 8.2 Frozen Semgrep and policy configuration

The frozen test policy used:

- Qwen temperature scaling with `T=445.683640902898`;
- split-conformal significance `alpha=0.10`;
- Semgrep Community Edition `1.163.0`;
- acceptance only when the conformal set was exactly `[1]` and Semgrep had a
  finding;
- `ABSTAIN` in every other case, including singleton `[0]`, two-label sets,
  empty sets, missing pairwise scores, unparseable responses, and absent static
  findings.

### Table 27. Locked-test Semgrep corroboration

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

### Table 28. Frozen-policy output reasons

| Decision/reason | Count |
|---|---:|
| Accepted `YES` | 452 |
| `ABSTAIN` | 23,556 |
| Abstain: frozen gate not satisfied | 23,342 |
| Abstain: missing pairwise score | 214 |
| Singleton positive with static finding | 452 |

### Table 29. Frozen conformal prediction sets

| Prediction set | Count |
|---|---:|
| `[0,1]` | 21,475 |
| `[1]` | 2,319 |
| Empty set | 214 |

### Table 30. Frozen-policy test confusion table

| Ground truth | Accepted `YES` | `ABSTAIN` | Total |
|---|---:|---:|---:|
| `target=0` | 416 | 23,070 | 23,486 |
| `target=1` | 36 | 486 | 522 |
| **Total** | **452** | **23,556** | **24,008** |

### Table 31. Frozen-policy locked-test metrics

| Metric | Value |
|---|---:|
| Accepted-decision coverage | 1.88% |
| Abstention rate | 98.12% |
| Precision among accepted `YES` decisions | 7.96% |
| Vulnerable-record acceptance/positive recall | 6.90% |
| Accepted false-positive rate among target-0 records | 1.77% |

---

## 9. Statistical uncertainty and paired ablations

### 9.1 Record-level paired bootstrap

Five thousand paired record-level bootstrap resamples were generated with
replacement using seed `20261027`. The same resampled record indices were used
for both methods in each paired comparison.

### Table 32. Point estimates and record-level 95% intervals

| Method | Accepted records | Coverage | Accepted-positive precision | Positive recall |
|---|---:|---:|---:|---:|
| Raw Qwen | 23,788 | 99.08% (98.96–99.20%) | 2.01% (1.84–2.19%) | 91.76% (89.31–94.02%) |
| Temperature + conformal only | 2,319 | 9.66% (9.28–10.03%) | 4.66% (3.81–5.52%) | 20.69% (17.17–24.26%) |
| Semgrep only | 1,514 | 6.31% (5.99–6.62%) | 6.87% (5.63–8.16%) | 19.92% (16.47–23.47%) |
| Frozen hybrid | 452 | 1.88% (1.71–2.05%) | 7.96% (5.59–10.58%) | 6.90% (4.81–9.18%) |

### Table 33. Record-level paired differences: frozen hybrid minus comparator

| Comparator | Coverage difference | Precision difference | Recall difference |
|---|---:|---:|---:|
| Raw Qwen | −97.20 pp (−97.42, −96.98) | +5.95 pp (+3.60, +8.54) | −84.87 pp (−87.84, −81.77) |
| Temperature + conformal | −7.78 pp (−8.13, −7.44) | +3.31 pp (+1.27, +5.53) | −13.79 pp (−16.82, −10.79) |
| Semgrep only | −4.42 pp (−4.69, −4.16) | +1.10 pp (−0.90, +3.18) | −13.03 pp (−15.97, −10.14) |

### 9.2 Project-clustered sensitivity analysis

The same records were grouped into 217 PrimeVul projects. Whole projects were
resampled with replacement for 5,000 iterations using seed `20261027`.

### Table 34. Project-clustered interval summary

| Method | Coverage | Accepted-positive precision | Positive recall |
|---|---:|---:|---:|
| Raw Qwen | 99.08% (98.49–99.49%) | 2.01% (1.50–2.73%) | 91.76% (85.87–95.98%) |
| Temperature + conformal only | 9.66% (7.58–11.83%) | 4.66% (3.75–5.97%) | 20.69% (14.10–29.97%) |
| Semgrep only | 6.31% (5.03–7.77%) | 6.87% (5.56–8.79%) | 19.92% (13.04–30.00%) |
| Frozen hybrid | 1.88% (1.38–2.47%) | 7.96% (5.46–10.85%) | 6.90% (3.84–11.21%) |

### Table 35. Project-clustered paired differences

| Comparator | Coverage difference | Precision difference | Recall difference |
|---|---:|---:|---:|
| Raw Qwen | −97.20 pp (−97.76, −96.40) | +5.95 pp (+3.48, +8.75) | −84.87 pp (−89.98, −78.21) |
| Temperature + conformal | −7.78 pp (−9.52, −6.12) | +3.31 pp (+1.10, +5.56) | −13.79 pp (−19.84, −9.56) |
| Semgrep only | −4.42 pp (−5.46, −3.51) | +1.10 pp (−1.14, +3.06) | −13.03 pp (−20.44, −8.24) |

### 9.3 Statistical interpretation

The frozen hybrid precision advantage over raw Qwen and temperature/conformal-
only acceptance remains positive under both record-level and project-clustered
resampling. The precision difference from Semgrep alone includes zero under
both interval definitions. The recall reduction is substantial relative to all
comparators.

These intervals are uncertainty sensitivities, not hypothesis tests. They
describe the official test, whose projects overlap across supplied partitions;
the separate project-held-out candidate is reported in Section 17.

---

## 10. Thesis-ready result interpretation

### 10.1 Main result

The raw Qwen baseline is almost an always-flag rule. It captures most vulnerable
records but creates an impractically large false-alert burden. The frozen hybrid
accepts only a small fraction of records but improves precision among accepted
positive alerts.

### 10.2 What improved

The completed pipeline improved the reliability of accepted positive alerts:

- raw Qwen precision: 2.01%;
- frozen hybrid precision: 7.96%;
- absolute improvement: 5.95 percentage points;
- project-clustered precision interval for the improvement: +3.48 to +8.75
  percentage points.

### 10.3 What did not improve

The pipeline did not improve all dimensions simultaneously:

- coverage fell from 99.08% to 1.88%;
- positive recall fell from 91.76% to 6.90%;
- the frozen hybrid accepted 36 of 522 vulnerable test records.

The correct claim is a precision–coverage trade-off, not an unconditional
improvement in vulnerability detection.

### 10.4 Operational interpretation

The frozen hybrid is best described as a selective review-triage mode. It is
appropriate for identifying a small number of higher-priority positive alerts
while escalating the majority of records for manual review. It is not a
complete automated vulnerability detector and should not be presented as one.

### 10.5 Calibration interpretation

Temperature scaling improved Brier score and ECE relative to the raw pairwise
score, but did not change the near-always-positive behavior sufficiently for a
useful thresholded classifier. Platt scaling improved probability-proper scores
but accepted no vulnerable records as positive at the default threshold. This
demonstrates that calibration and operating-threshold selection must remain
separate under severe class imbalance.

### 10.6 Static-analysis interpretation

The Semgrep rule pack provides corroboration evidence but is not semantic ground
truth. A finding is positive review evidence; no finding is neutral. Requiring a
finding improves selectivity but further reduces coverage and recall.

### 10.7 Generalization boundary

Project-clustered resampling accounts for project concentration in uncertainty
sensitivity, but it does not create an unseen-project benchmark. The separate
unseen-project candidate does provide a project-held-out evaluation: alpha
`0.50` increases recall from 11.32% to 25.23% and coverage from 2.89% to 8.01%
relative to the frozen alpha `0.10` policy, while reducing accepted-positive
precision from 11.01% to 8.86%. The final paper should call this a mixed
project-held-out trade-off, not a universal or autonomous-detection result.

---

## 11. Experiment coverage audit against the chapter

### Table 36. Chapter requirement coverage

| Chapter requirement | Status | Evidence or limitation |
|---|---|---|
| Dataset/provenance audit | Complete | Raw train/validation/test audit and provenance review |
| LLM-only baseline | Complete for Qwen | Validation and test full runs |
| Temperature calibration | Complete | Validation-only fit and held-out metrics |
| Platt calibration | Complete | Validation-only fit; zero useful positive decisions at threshold 0.5 |
| Ensemble calibration | Not performed | No ensemble calibrator was implemented |
| Logit-based confidence | Partial/complete for pairwise diagnostic | First-token YES/NO pairwise score used |
| Verbal confidence | Not performed | Requires new prompt and inference run |
| Self-consistency `N=5` | Not performed | Requires repeated inference |
| Conformal abstention | Complete for implemented branch | Validation and frozen test application |
| Static corroboration | Complete with Semgrep | Function-local C/C++ rule pack, not repository CodeQL/SonarQube |
| Full hybrid pipeline | Complete | Frozen positive corroboration gate |
| Baseline/conformal/Semgrep/hybrid ablations | Complete | Validation and locked-test comparisons |
| F1/accuracy/FPR for every selective method | Partial | Binary and positive-alert metrics were prioritized; abstention conventions need explicit expansion |
| ECE/Brier | Complete on validation calibration | Test ECE was not the primary locked-test metric |
| Reliability diagrams | Not yet produced | Figure-generation task remains |
| AUROC | Not yet reported | Requires an explicit ranking definition and score handling policy |
| Error–reject curves | Not yet produced | Figure-generation task remains |
| Category/complexity/language stratification | Not performed | Requires subgroup analysis and derived complexity features |
| Pearson correlation | Not performed | Static/LLM relation was summarized by counts only |
| Cohen's kappa | Not performed | Agreement statistic remains open |
| Paired uncertainty analysis | Complete | Record-level and project-clustered bootstrap |
| Unseen-project grouped evaluation | Complete as a separate candidate study | 38,362-record, 400-project train-only holdout; reported separately from the official locked test |

### 11.1 How to use this audit in the paper

The paper can state the completed core study now, provided it uses the actual
Qwen, Semgrep, manifest, and metric definitions. It must not state that all
chapter experiments were performed unless the remaining rows are completed.
Alternatively, the chapter can be revised from a broad proposal into an
empirical paper describing the implemented subset and explicitly naming the
unperformed items as limitations or future work.

---

## 12. Scripts, notebooks, protocols, and rule files

All working source paths below are absolute. Archived snapshots are preserved
under the durable context package so the exact implementation associated with
the reports can be cited.

### 12.1 Dataset audit and leakage-control scripts

| Artifact | Absolute working path | Purpose | Status |
|---|---|---|---|
| PrimeVul audit | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\primevul_audit.py` | Schema, counts, missingness, identity, provenance | Used |
| Approximate scan | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\near_duplicate_scan.py` | SQLite-backed bounded SimHash scan | Used |
| Similarity verification | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\near_duplicate_verify.py` | Token 5-gram Jaccard verification | Used |
| Provenance review | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\review_near_duplicate_pairs.py` | Metadata join and representative diffs | Used |
| High-priority triage | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\triage_high_priority_pairs.py` | Priority summary and label mismatch review | Used |
| Component manifest | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\build_high_priority_group_manifest.py` | Connected components | Used |
| Evaluation manifest | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\build_leakage_controlled_manifest.py` | Conservative validation/test exclusions | Used |
| Unseen-project holdout builder | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\build_unseen_project_holdout.py` | Deterministic whole-project candidate from train-only projects | Used |

Archived directory:

`C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts`

### 12.2 Baseline and inference scripts

| Artifact | Absolute working path | Purpose | Status |
|---|---|---|---|
| OpenAI baseline runner | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\run_openai_baseline.py` | Earlier API baseline scaffold | Prepared, not used for final empirical results |
| Local Qwen smoke runner | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\run_qwen_sample.py` | Deterministic local smoke test | Used/prepared |
| Colab Qwen runner | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\run_qwen_colab.py` | Portable Qwen inference | Used |
| Validation Colab notebook | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\primevul_qwen_colab.ipynb` | Validation/full retained inference | Used |
| Test Colab notebook | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\primevul_qwen_test_colab.ipynb` | Locked test inference | Used |
| Unseen-project Colab notebook | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\primevul_qwen_unseen_project_colab.ipynb` | Project-held-out candidate inference | Prepared |
| Unseen-project Semgrep notebook | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\primevul_semgrep_unseen_project_colab.ipynb` | Project-held-out corroboration | Prepared |

### 12.3 Calibration, conformal, static, and policy scripts

| Artifact | Absolute working path | Purpose | Status |
|---|---|---|---|
| Calibration | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\fit_qwen_calibration.py` | Validation-only temperature and Platt scaling | Used |
| Conformal | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\run_conformal_abstention.py` | Three-way split-conformal evaluation | Used |
| Semgrep adapter | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\run_semgrep_corroboration.py` | Batch static scan and join | Used |
| Semgrep rule pack | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\semgrep_primevul_rules.yml` | Auditable local C/C++ rules | Used |
| Hybrid validation | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\evaluate_hybrid_validation.py` | Conformal/static ablations | Used |
| Policy sweep | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\select_validation_operating_policy.py` | Validation-only cost/recall sweep | Used |
| Frozen-policy application | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\apply_frozen_policy.py` | Apply frozen test policy | Used |

### 12.4 Statistical scripts

| Artifact | Absolute working path | Purpose | Status |
|---|---|---|---|
| Record bootstrap | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\run_locked_test_statistics.py` | 5,000 paired record-level resamples | Used |
| Project bootstrap | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\run_project_clustered_statistics.py` | 5,000 whole-project resamples | Used |
| Higher-recall validation sweep | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\run_high_recall_validation_sweep.py` | Validation-only alpha sweep with recall floors | Used |
| Higher-recall candidate application | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\apply_high_recall_candidate_policy.py` | Apply validation-selected alpha=0.50 candidate | Used |

### 12.5 Protocol and documentation files

| Artifact | Absolute path | Purpose |
|---|---|---|
| Baseline protocol | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\BASELINE_PROTOCOL.md` | Baseline contract |
| Leakage protocol | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\PRIMEVUL_LEAKAGE_PROTOCOL.md` | Reporting and leakage modes |
| Static protocol | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\STATIC_CORROBORATION_PROTOCOL.md` | Analyzer and rule execution contract |
| Locked-test protocol | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\LOCKED_TEST_PROTOCOL.md` | Test lock and preservation rules |
| Working README | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\README.md` | Experiment-code guidance |
| Archived script manifest | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts\SCRIPT_ARCHIVE_MANIFEST.json` | Snapshot hashes and stage mapping |

Every completed experiment script except the unused OpenAI scaffold has an
archived snapshot under:

`C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts`

---

## 13. Generated outputs and absolute paths

### 13.1 Stable dataset and review artifacts

| Output | Absolute path | Purpose/status |
|---|---|---|
| Leakage-controlled manifest | `C:\Users\rehan\OneDrive\Desktop\Thesis\datasets\PrimeVul\PrimeVul_v0.1-20260930T034251Z-1-001\PrimeVul_v0.1\thesis_primevul_leakage_controlled_manifest.json` | Final derived evaluation manifest |
| Unseen-project holdout manifest | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\primevul_unseen_project_holdout_manifest.json` | 400 train-only projects; 38,362 records; Qwen run complete; policy pending |
| Verified review report | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\VERIFIED_REVIEW_REPORT.json` | Similarity/provenance review artifact |

### 13.2 Qwen inference outputs

| Output | Absolute path | Purpose/status |
|---|---|---|
| Validation smoke output | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\qwen_smoke_valid.json` | Three-record/small smoke check |
| Validation smoke metadata | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\qwen_smoke_valid.json.meta.json` | Smoke-run metadata |
| Full validation output | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\qwen_valid_results_full.jsonl` | Earlier full validation output |
| Clean fixed validation output | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\qwen_valid_results_fixed.jsonl` | Final clean validation baseline |
| Fixed validation metadata | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\qwen_valid_results.jsonl.meta_fixed.json` | Metadata for fixed validation run |
| Earlier validation metadata | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\qwen_valid_results.jsonl.meta_full.json` | Metadata for earlier full run |
| Full test output | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\qwen_test_results.jsonl` | Locked raw test baseline |
| Test output metadata | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\qwen_test_results.jsonl.meta.json` | Locked test execution metadata |
| Validation Colab notebook copy | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\primevul_qwen_colab.ipynb` | User-uploadable validation notebook |
| Memory-fix notebook | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\primevul_qwen_colab_memory_fix.ipynb` | Colab memory workaround |
| Test Colab notebook copy | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\primevul_qwen_test_colab.ipynb` | User-uploadable test notebook |
| Unseen-project Colab notebook copy | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\primevul_qwen_unseen_project_colab.ipynb` | User-uploadable project-held-out candidate notebook |
| Unseen-project Qwen output | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\qwen_unseen_project_results.jsonl` | Complete 38,362-record raw Qwen candidate run |
| Unseen-project Qwen metadata | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\qwen_unseen_project_results.jsonl.meta.json` | Execution metadata and completion proof |
| Unseen-project Semgrep output | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\semgrep_unseen_project_results.json` | Complete 38,362-record static corroboration |
| Unseen-project frozen-policy output | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\frozen_unseen_project_policy_results.json` | Alpha=0.10 frozen policy |
| Unseen-project higher-recall output | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\high_recall_unseen_project_policy_results.json` | Validation-selected alpha=0.50 candidate |
| Unseen-project direct policy statistics | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\unseen_policy_comparison_statistics.json` | 5,000 record/project paired comparison |
| Unseen-project frozen record statistics | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\unseen_frozen_record_statistics_5000.json` | 5,000 record-level resamples |
| Unseen-project candidate record statistics | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\unseen_high_recall_record_statistics_5000.json` | 5,000 record-level resamples |
| Unseen-project frozen project statistics | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\unseen_frozen_project_statistics_5000.json` | 5,000 project-clustered resamples |
| Unseen-project candidate project statistics | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\unseen_high_recall_project_statistics_5000.json` | 5,000 project-clustered resamples |
| Unseen-project Semgrep notebook copy | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\primevul_semgrep_unseen_project_colab.ipynb` | User-uploadable corroboration notebook |

### 13.3 Locked-test analysis outputs

| Output | Absolute path | Purpose/status |
|---|---|---|
| Semgrep test result | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\semgrep_test_results.json` | 24,008-record static corroboration |
| Frozen policy result | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\frozen_test_policy_results.json` | Final frozen decisions and target join |
| Record bootstrap result | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\locked_test_statistics.json` | 5,000 record-level resamples |
| Project bootstrap result | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\project_clustered_test_statistics.json` | 5,000 project-level resamples |
| Initial higher-recall sweep | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\validation_high_recall_policy_sweep.json` | Validation-only candidate sweep |
| Extended higher-recall sweep | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\validation_high_recall_extended_sweep.json` | Alpha values through 0.90 |
| Higher-recall candidate test output | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\high_recall_candidate_test_policy_results.json` | Exploratory alpha=0.50 candidate application |
| Unseen-project holdout manifest | `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\primevul_unseen_project_holdout_manifest.json` | 400 train-only projects; 38,362 records; Qwen run complete; policy pending |
| Unseen-project Qwen run report | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\qwen_unseen_project_run_report.md` | Integrity checks and raw Qwen baseline metrics |
| Unseen-project policy report | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\unseen_project_policy_results_report.md` | Semgrep, frozen-policy, and higher-recall candidate results |

### 13.4 Temporary analysis outputs

These files were generated outside the project directory and are useful for
reproducibility. They may be temporary and should be copied into a formal
experiment archive before final submission.

| Output | Absolute path |
|---|---|
| Calibration artifact | `C:\Users\rehan\AppData\Local\Temp\thesis_qwen_calibration_artifacts.json` |
| Semgrep validation smoke | `C:\Users\rehan\AppData\Local\Temp\thesis_semgrep_valid_smoke.json` |
| Batched Semgrep smoke | `C:\Users\rehan\AppData\Local\Temp\thesis_semgrep_valid_smoke_batched.json` |
| Full validation Semgrep | `C:\Users\rehan\AppData\Local\Temp\thesis_semgrep_valid_full.json` |
| Hybrid validation artifact | `C:\Users\rehan\AppData\Local\Temp\thesis_hybrid_validation_artifacts.json` |
| Validation policy sweep | `C:\Users\rehan\AppData\Local\Temp\thesis_validation_policy_sweep.json` |
| Conformal artifact | `C:\Users\rehan\AppData\Local\Temp\thesis_qwen_conformal_artifacts.json` |
| Validation frozen-policy check | `C:\Users\rehan\AppData\Local\Temp\thesis_frozen_policy_valid_check.json` |
| Near-duplicate verification SQLite index | `C:\Users\rehan\AppData\Local\Temp\thesis_primevul_near_duplicate_verify.sqlite3` |
| Near-duplicate verification JSON | `C:\Users\rehan\AppData\Local\Temp\thesis_primevul_near_duplicate_verify.json` |
| Near-duplicate verification stdout | `C:\Users\rehan\AppData\Local\Temp\thesis_primevul_near_duplicate_verify.stdout` |
| Near-duplicate verification stderr | `C:\Users\rehan\AppData\Local\Temp\thesis_primevul_near_duplicate_verify.stderr` |
| Near-duplicate provenance review | `C:\Users\rehan\AppData\Local\Temp\thesis_primevul_near_duplicate_review.json` |
| Representative diff file | `C:\Users\rehan\AppData\Local\Temp\thesis_primevul_near_duplicate_review.diff` |
| Semgrep test temporary result | `C:\Users\rehan\AppData\Local\Temp\thesis_semgrep_test.json` |
| Frozen test temporary result | `C:\Users\rehan\AppData\Local\Temp\thesis_frozen_test_policy.json` |

### 13.5 Durable report outputs

All thesis reports are under:

`C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs`

The principal report files are:

- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\thesis_progress_report.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\thesis_decisions.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\qwen_validation_baseline_report.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\qwen_calibration_report.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\qwen_conformal_report.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\qwen_static_corroboration_report.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\qwen_hybrid_validation_report.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\qwen_policy_sweep_report.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\qwen_test_baseline_report.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\qwen_test_frozen_policy_report.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\qwen_locked_test_statistics_report.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\qwen_project_clustered_statistics_report.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\thesis_results_discussion_tables.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\qwen_high_recall_improvement_report.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\THESIS_OPERATING_POLICY.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\THESIS_MASTER_IMPLEMENTATION_REPORT.md`

---

## 14. Recommended tables for the research paper

The following table sequence is suitable for the main paper. The detailed
versions are included above and in
`C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\thesis_results_discussion_tables.md`.

### Main paper Table A: Dataset audit and retention

Use raw counts, target counts, exact identity checks, high-priority exclusions,
and retained validation/test counts. This table establishes that the test
result is based on a documented derived manifest rather than an undisclosed
dataset rewrite.

### Main paper Table B: Baseline and component ablations

Report raw Qwen, temperature/conformal-only, Semgrep-only, and frozen hybrid on
the same retained test records. Use coverage, accepted-positive precision,
positive recall, accepted records, true positives, and false positives.

### Main paper Table C: Calibration results

Report raw pairwise score, temperature scaling, and Platt scaling on held-out
validation records with Brier, ECE, log loss, precision, recall, and the
warning that Platt's high accuracy was negative-class dominated.

### Main paper Table D: Frozen policy and test outcome

Report the model revision, calibration temperature, alpha, Semgrep version,
acceptance rule, accepted `YES`, abstentions, and target-by-decision table.

### Main paper Table E: Statistical uncertainty

Report record-level and project-clustered intervals side by side. Include paired
precision, coverage, and recall differences for frozen hybrid minus raw Qwen,
temperature/conformal-only, and Semgrep-only.

---

## 15. Figures that can be included in the paper

The original chapter already contains conceptual figures for the architecture,
calibration workflow, conformal gate, split discipline, metric trade-off, and
ablation dependency. The following descriptions convert those concepts into
empirical or thesis-ready figures.

### Figure 1. End-to-end system architecture

**Purpose:** Show the proposed pipeline from source code to automated alert or
manual review.

**Content:**

```text
PrimeVul function code
        |
        v
Qwen code-only YES/NO inference
        |
        v
Pairwise first-token score extraction
        |
        v
Validation-only temperature calibration
        |
        v
Split-conformal prediction set
        |
        +-----------------------------+
        |                             |
        v                             v
Semgrep corroboration             ABSTAIN
        |                             |
        v                             v
Accepted positive alert       Manual-review escalation
```

**Caption draft:** “Architecture of the implemented confidence-calibrated
selective code-review pipeline. Calibration and policy selection use retained
validation data; the retained test partition is evaluated only after the policy
is frozen.”

**Status:** Can be included now; distinguish the implemented Qwen/Semgrep
version from the broader chapter proposal.

### Figure 2. Dataset audit and leakage-control flow

**Purpose:** Explain why the raw partitions were not merged or rewritten.

**Content:** Raw train, validation, and test files flow through exact identity
checks, SimHash candidates, Jaccard verification, provenance review, and the
derived manifest. Show 224,533 raw records, 2,872 verified approximate pairs,
1,795 high-priority pairs, 915 validation exclusions, and 780 test exclusions.

**Caption draft:** “Dataset and provenance audit used to define the
leakage-controlled evaluation manifest without modifying the supplied PrimeVul
JSONL partitions.”

**Status:** Empirically supported by completed audit artifacts.

### Figure 3. Class distribution and raw-model behavior

**Purpose:** Make the extreme class imbalance and near-always-`YES` baseline
visible.

**Recommended layout:** Two panels:

- Panel A: target distribution for validation and retained test;
- Panel B: raw Qwen response distribution (`YES`, `NO`, unparseable) for both
  partitions.

**Key values:** Test target prevalence is 2.17%; raw test `YES` rate is 99.08%.

**Caption draft:** “Class imbalance and raw Qwen output distribution. The model
produces a positive alert for nearly every record, motivating calibration and
selective abstention.”

### Figure 4. Calibration reliability diagrams

**Purpose:** Visualize the relationship between predicted confidence and
empirical vulnerability frequency.

**Recommended layout:** Reliability diagrams for raw pairwise score,
temperature scaling, and Platt scaling on the held-out validation subset, with
bin counts shown below or encoded by marker size.

**Caution:** Platt scaling's high accuracy is dominated by the negative class;
the diagram must be accompanied by positive recall and accepted-positive
metrics.

**Caption draft:** “Validation reliability diagrams for raw, temperature-scaled,
and Platt-scaled pairwise scores. Calibration alignment improves under Platt
scaling, but its default threshold accepts no vulnerable records as positive.”

**Status:** Not yet generated; the calibration outputs are available.

### Figure 5. Calibration metric comparison

**Purpose:** Show Brier score, log loss, and ECE before and after calibration.

**Recommended layout:** Grouped bars for raw, temperature, and Platt methods.

**Values:** Raw Brier 0.6166, temperature 0.2507, Platt 0.0226; raw ECE
0.7699, temperature 0.4778, Platt 0.0027.

**Caption draft:** “Held-out validation calibration metrics. Proper scoring
metrics improve after calibration, but operational positive detection remains a
separate problem under severe class imbalance.”

### Figure 6. Conformal risk–coverage curve

**Purpose:** Show the relationship between conformal significance, accepted
coverage, abstention, accepted-positive precision, and vulnerable-record
acceptance.

**Recommended layout:** Plot coverage on the x-axis and accepted-positive
precision and positive recall as separate y-series; use alpha values as labels.

**Caption draft:** “Validation risk–coverage behavior of temperature-scaled
conformal prediction. More selective settings reduce coverage and alter the
precision–recall trade-off.”

### Figure 7. Static corroboration relation diagram

**Purpose:** Show how Qwen predictions and Semgrep findings overlap.

**Recommended layout:** A 2x2 table or Sankey-style diagram with LLM `YES/NO`,
Semgrep finding/no finding, and `AGREE`, `DISAGREE`, `NEUTRAL` categories.

**Key validation values:** `AGREE=1,743`, `DISAGREE=1`, `NEUTRAL=21,289`.

**Caption draft:** “Relationship between raw LLM decisions and local Semgrep
findings. No finding is treated as neutral evidence rather than proof of safety.”

### Figure 8. Ablation precision–coverage frontier

**Purpose:** Show that the frozen hybrid is a trade-off point, not a universal
dominant method.

**Recommended layout:** x-axis coverage, y-axis accepted-positive precision,
marker size or labels for positive recall. Include raw Qwen, temperature+
conformal, Semgrep-only, and frozen hybrid.

**Key test points:**

- Raw Qwen: 99.08% coverage, 2.01% precision, 91.76% recall;
- temperature/conformal: 9.66%, 4.66%, 20.69%;
- Semgrep-only: 6.31%, 6.87%, 19.92%;
- frozen hybrid: 1.88%, 7.96%, 6.90%.
- higher-recall candidate: 5.09%, 6.47%, 15.13%.

**Caption draft:** “Locked-test precision–coverage trade-off across the raw
baseline and selective ablations. The frozen hybrid has the highest point
precision but the lowest coverage and positive recall.”

### Figure 9. Frozen-policy decision composition

**Purpose:** Show how the final policy partitions records into accepted alerts
and abstentions by ground truth.

**Recommended layout:** Stacked bars for `target=0` and `target=1`, dividing
accepted `YES` and abstention.

**Key values:** For `target=0`, 416 accepted and 23,070 abstained; for
`target=1`, 36 accepted and 486 abstained.

**Caption draft:** “Ground-truth composition of frozen-policy decisions on the
locked test partition. The policy accepts a small number of alerts and
escalates the majority of vulnerable and non-vulnerable records.”

### Figure 10. Bootstrap uncertainty intervals

**Purpose:** Show point estimates and uncertainty for each method.

**Recommended layout:** Forest plots for coverage, accepted-positive precision,
and positive recall. Use separate panels for record-level and project-clustered
intervals.

**Caption draft:** “Record-level and project-clustered 95% bootstrap intervals.
Project clustering widens several intervals because PrimeVul records are
concentrated in a small number of projects.”

### Figure 11. Project cluster-size distribution

**Purpose:** Justify the project-clustered sensitivity analysis.

**Recommended layout:** Histogram or log-scale bar chart of records per project;
annotate 217 projects, median 36, maximum 3,970, and 13 single-record projects.

**Caption draft:** “Project concentration in the retained PrimeVul test
partition. The concentration motivates project-clustered uncertainty analysis
and limits record-level independence assumptions.”

### Figure 12. Experiment decision timeline

**Purpose:** Provide a reproducibility-oriented project history.

**Content:** Dataset audit -> similarity verification -> manifest -> Qwen
baseline -> calibration -> conformal -> Semgrep -> hybrid ablation -> policy
freeze -> raw test -> frozen test -> bootstrap analyses.

**Caption draft:** “Chronological implementation sequence and test-lock
boundary. Validation-stage decisions precede the locked-test evaluation.”

---

## 16. Reproducibility and integrity controls

### 16.1 Test-lock rule

The retained test labels were not used to fit calibration, compute conformal
calibration scores, select thresholds, choose the Semgrep rule pack, or select
the frozen policy. Test labels were joined only after inference and policy
application for final evaluation.

### 16.2 Raw-data preservation

No raw PrimeVul JSONL file was modified. All exclusions are represented in the
derived manifest and reports.

### 16.3 Alignment checks

The Qwen, Semgrep, and frozen-policy test artifacts were aligned by
`record_number`. All 24,008 retained test records were present with no missing
or duplicate record numbers.

### 16.4 Key checksums

| Artifact | SHA-256 |
|---|---|
| `qwen_test_results.jsonl` | `27B584B4C7CD8B5DF188CCA597A7906D29D6DE9097E431F89CBE572794DEE3DD` |
| `qwen_test_results.jsonl.meta.json` | `B4AF5F430E435F4BC56A7883D43A4FF3CAB9B78262C72AD1652BFAAA7533C096` |
| Leakage-controlled manifest | `4D19F14509EDDB7A68FF4E8118954572886A885D150FD70347C02C86A08934D4` |
| `semgrep_test_results.json` | `48004DFBF1C6506970A9334712E26E5D398DEE8EC9E853A220A032168A41DF1C` |
| `frozen_test_policy_results.json` | `627C4E15697AB06E5E26E61F54CCAD920CED4604E04AC5CFD0B84A7CF7A69E8A` |
| `locked_test_statistics.json` | `F7739C78D8FC2CA6D2F4568EFFEAFD5F6644C115C851E622C4616F9CEB84642D` |
| `run_locked_test_statistics.py` archive | `775B5794C4E3DD60B5288603C05900200F652E7353FBD6FC8A88383A3DB2CD0A` |
| `run_project_clustered_statistics.py` archive | `F41086C2E82C90DEB26D4BD68DBA66A63433146058ACE17F487617DED3F887F1` |
| `run_high_recall_validation_sweep.py` archive | `33EB9D7036375496B49C4E7FF6E9E33633430230EC3AD8BE484659BADD540897` |
| `apply_high_recall_candidate_policy.py` archive | `02AE81479292CE66B1BA7819E4A492BB7D221ABF638180CA20ED3CF550A9CAFD` |
| `primevul_qwen_unseen_project_colab.ipynb` archive | `F45261DFEDFDD4875E954102ACA857CBDB721023F7CD96405B095DAF6A4CFA6E` |
| `build_unseen_project_holdout.py` archive | `B00FF08D21BBB7EF3E275EB5E38328053B193DD909DA1B79B4C2A7EF17152B40` |
| `primevul_semgrep_unseen_project_colab.ipynb` archive | `7002DEBB52541C93D6E1CB33BCAE6DFD44FB2EC60C7244AAEECA9EC188DA003E` |
| `semgrep_unseen_project_results.json` | `CD4E183BE87A2DEF93FE67E1E1304D01C246E616894EF48F9C89DDD480A39A09` |
| `frozen_unseen_project_policy_results.json` | `4A439432442B27E924D16963027054124A3A3A2748085670CC27D3E00E6B413D` |
| `high_recall_unseen_project_policy_results.json` | `B688BE90CD72D6FBF8B9CC01E71BA7B10F053CCD7BBEE9D3A5397C0F2C5DFAED` |
| `unseen_policy_comparison_statistics.json` | `966B68089D0030029554AF3795070E480B3289E109A5E89793689DA10FE41BD2` |
| `unseen_frozen_record_statistics_5000.json` | `A8BC8907D6020D792F98FC3E7FEDAC35BE3B35BFB81A415AD5CD8B04F97E8C69` |
| `unseen_high_recall_record_statistics_5000.json` | `C87C0D50A1C9E7FD1D48CC86BC84F4ED7A0408E58D145D78BBDD671585725F13` |
| `unseen_frozen_project_statistics_5000.json` | `755C5BF9851B6B2DEEA5AF07F70A447F9547BD28ABC51A6F3F4820A461EBEBBC` |
| `unseen_high_recall_project_statistics_5000.json` | `CECBCF1A1AD2B0FAD3B54428077AEBA90C94BB15961CBCC7F1761E5698FB4532` |

### 16.5 Reproduction commands

#### Record-level statistics

```powershell
python C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\run_locked_test_statistics.py `
  --qwen-results C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\qwen_test_results.jsonl `
  --static-results C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\semgrep_test_results.json `
  --policy-results C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\frozen_test_policy_results.json `
  --iterations 5000 `
  --seed 20261027 `
  --output C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\locked_test_statistics.json
```

#### Project-clustered statistics

```powershell
python C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\run_project_clustered_statistics.py `
  --qwen-results C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\qwen_test_results.jsonl `
  --static-results C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\semgrep_test_results.json `
  --policy-results C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\frozen_test_policy_results.json `
  --iterations 5000 `
  --seed 20261027 `
  --output C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\project_clustered_test_statistics.json
```

---

## 17. Higher-recall improvement study and remaining boundary

The first higher-recall candidate study is complete. A validation-only sweep
selected temperature scaling plus Semgrep corroboration at alpha `0.50` under a
20% validation positive-recall floor. On the existing test output, it achieved
5.09% coverage, 6.47% accepted-positive precision, and 15.13% positive recall,
compared with 1.88%, 7.96%, and 6.90% for the original frozen policy. The
candidate increases recall and coverage but reduces precision and remains an
exploratory transfer result.

To provide an independent evaluation target, a deterministic whole-project
holdout was constructed from the raw training partition. It contains all
records from 400 train-only projects absent from both official validation and
official test: 38,362 records in total, including 1,078 vulnerable records.
The manifest is
`C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\primevul_unseen_project_holdout_manifest.json`.
The builder excludes high-priority verified train records as an additional
safeguard and does not modify any raw dataset file. Qwen inference on this
candidate is now complete: all 38,362 records were processed exactly once,
with 38,025 YES, 15 NO, and 322 unparseable outputs. Raw YES precision was
2.65% and conservative all-record vulnerable recall was 93.51%, confirming the
same near-always-YES behavior seen on the official partitions. Semgrep and both
fixed policy applications are also complete. Semgrep found 3,654 records with
findings, including 327 vulnerable records. The frozen alpha `0.10` policy
accepted 1,108 records at 11.01% accepted precision and 11.32% vulnerable
recall. The validation-selected alpha `0.50` candidate accepted 3,071 records
at 8.86% precision and 25.23% vulnerable recall. The higher-recall candidate
therefore improves coverage and recall on disjoint projects at a precision
cost; it is a mixed improvement, not a dominance result.

Five thousand record-level and 5,000 project-clustered bootstrap comparisons
confirmed the direction of this trade-off. Alpha `0.50` minus alpha `0.10` was
+5.12 percentage points in coverage (project-clustered 95% interval +4.13 to
+6.19), −2.15 points in accepted-positive precision (−3.45 to −0.89), and
+13.91 points in vulnerable recall (+11.29 to +16.57). These intervals support
the mixed-improvement interpretation while preserving alpha `0.10` as the
primary frozen policy.

The core implementation record, official locked-test results, and independent
project-held-out improvement evaluation are complete. The following optional
extensions remain open:

1. decide how unparseable generations and missing pairwise scores should be
   represented in the final paper;
2. optionally run reliability diagrams, error-reject curves, AUROC, F1/FPR
   expansions, Pearson correlation, Cohen's kappa, and subgroup analyses;
3. optionally run verbal-confidence and self-consistency experiments;
4. optionally implement ensemble calibration;
5. optionally expand the improvement study with further prespecified models,
   confidence features, or grouped resplits without retuning the locked test.

The existing locked test must not be retuned. Any new operating point, model,
prompt, calibrator, or static rule pack must be selected without using the
completed test labels.

The completed higher-recall project-held-out policy is an auxiliary mixed
trade-off result, not a replacement for the frozen locked-test result. Any
further improvement study must remain prespecified and must not retroactively
substitute a new operating point for the current frozen result.

---

## 18. Recommended paper structure

1. **Introduction:** reliability problem, false-alert burden, and selective
   review motivation.
2. **Background and related work:** LLM code review, calibration, conformal
   prediction, static analysis, and leakage concerns.
3. **Research questions and hypotheses:** retain only claims supported by the
   implemented scope or clearly identify additional questions as future work.
4. **Dataset and leakage audit:** PrimeVul counts, provenance overlap, similarity
   review, and manifest construction.
5. **Methodology:** Qwen prompt, pairwise score extraction, validation-only
   calibration, conformal gate, Semgrep rule pack, frozen policy, and lock rules.
6. **Experimental setup:** hardware/software versions, seeds, paths, and
   response-resolution policy.
7. **Results:** validation calibration, conformal and static ablations, raw test
   baseline, frozen policy, and uncertainty intervals.
8. **Discussion:** precision–coverage trade-off, recall limitation, project
   dependence, and operational interpretation.
9. **Threats to validity:** label construction, unparseable outputs, function-
   local static analysis, project overlap, and model-specific scope.
10. **Conclusion and future work:** higher-recall policy, broader confidence
    features, grouped resplits, additional models, and external datasets.

---

## 19. Final paper claims that are currently safe

The following claims are supported by the completed artifacts:

- PrimeVul raw partitions were audited without modification.
- Exact duplicate leakage was not found under the tested identity checks, but
  strong approximate/provenance overlaps were present.
- The leakage-controlled manifest retains 23,033 validation and 24,008 test
  records.
- The pinned Qwen model has a severe near-always-positive raw baseline.
- Validation-only calibration improved probability-proper metrics but did not
  by itself solve the positive-decision problem.
- Semgrep provides a measurable but limited function-local corroboration signal.
- The frozen hybrid improves accepted-positive precision over raw Qwen on the
  locked test at the cost of severe coverage and recall reduction.
- The precision advantage over raw Qwen and temperature/conformal-only
  acceptance remains positive under record-level and project-clustered paired
  bootstrap intervals.
- The current evidence supports selective review triage and a mixed
  project-held-out recall/coverage trade-off, not high-recall autonomous
  vulnerability detection.

## 20. Claims that must not currently be made

- That every experiment proposed in the original chapter was completed.
- That the model was fine-tuned on PrimeVul train.
- That Qwen is universally superior to GPT-4o, DeepSeek-Coder, or other models.
- That the final hybrid dominates Semgrep on every metric.
- That no Semgrep finding proves a function is safe.
- That the official locked test is an unseen-project benchmark; the separate
  project-held-out candidate must be described separately.
- That the final hybrid has high vulnerability recall.
- That the conformal gate's `alpha=0.10` makes the final hybrid automatically
  cover 90% of records as accepted automated decisions; final accepted-decision
  coverage is 1.88% because the static corroboration gate is stricter.

---

## 21. Source documents consolidated here

The master report consolidates the following durable sources:

- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\THESIS_CONTEXT.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\chat_history.md`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\draft\chapter.pdf`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\thesis_progress_report.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\thesis_decisions.md`
- all experiment-specific reports listed in Section 13.5;
- all archived script snapshots listed in Section 12.

This master document is the recommended starting point when drafting the
research paper. The experiment-specific reports should remain the authoritative
source for detailed methods, output schemas, and artifact-specific checksums.


