# Supervisor Briefing: Thesis Project Implementation and Results

## 1. Document purpose

This document is a supervisor-facing explanation of the Thesis project. It
records the research title, motivation, decisions, implementation sequence,
experimental results, limitations, and the exact locations of the scripts and
artifacts that can be shown during supervision meetings.

The document is deliberately evidence-based. It distinguishes completed
experiments from proposed chapter experiments that were not run, and it
distinguishes approximate similarity candidates from confirmed semantic
duplicates.

**Reporting date:** 2026-10-27  
**Primary dataset:** PrimeVul v0.1  
**Primary model:** `Qwen/Qwen2.5-Coder-1.5B-Instruct`, Hugging Face revision `2e1fd39`  
**Primary implementation status:** Core locked-test study complete; separate project-held-out improvement evaluation complete; optional chapter extensions remain open.

## 2. Thesis title and central idea

### Working title

**Confidence-Calibrated LLMs with Selective Abstention for Reliable Automated
Code Review: A Hybrid Pipeline Combining Post-Hoc Calibration, Conformal
Abstention Gating, and Rule Corroboration.**

### Central research problem

Large language models can identify vulnerable code, but their raw decisions may
be overconfident and may generate too many false alerts. A system that flags
almost everything is not sufficiently useful for practical code review because
developers must inspect a large number of incorrect alerts.

The project therefore studies a selective-review pipeline:

```text
source code
    -> LLM vulnerability decision and confidence features
    -> post-hoc calibration
    -> conformal/selective abstention
    -> static-analysis corroboration
    -> accepted alert or abstention for human review
```

The objective is not to make the model automatically decide every case. The
objective is to improve the reliability and precision of the cases that the
system is willing to accept, while explicitly abstaining on uncertain cases.

## 3. Research task and label interpretation

The task is binary vulnerability detection at function level:

| Value | Meaning |
|---:|---|
| `target = 1` | Vulnerable/actionable defect is present |
| `target = 0` | No vulnerable/actionable defect under the selected task definition |
| Model `YES` | Predicted vulnerable/flag |
| Model `NO` | Predicted non-vulnerable/do not flag |

The model's `YES`/`NO` output was not treated as a direct measure of accuracy.
It was parsed into a prediction and accompanied by top-token confidence
features. Unparseable responses were retained and reported rather than silently
converted into a class.

## 4. Why PrimeVul was selected

PrimeVul was selected provisionally because it provides:

- function-level C/C++ code;
- binary vulnerability labels;
- predefined train, validation, and test partitions;
- project and commit provenance;
- CWE/CVE-related metadata;
- function hashes and file/provenance information.

The raw partitions were used for the leakage audit. The balanced paired files
were not substituted for the natural benchmark distributions because they are
contrast files and do not represent the primary train/validation/test
population.

The raw dataset was not rewritten. A separate derived manifest was created to
record conservative exclusions after provenance review.

## 5. Complete implementation sequence

### Step 1: Interpret the source chapter

The chapter was treated as a methodology/proposal document rather than as a
report of already completed experiments. Its proposed order was converted into
an implementation plan:

1. freeze the task and data protocol;
2. audit the dataset and leakage risk;
3. run an LLM-only baseline;
4. fit calibration using validation data;
5. add conformal/selective abstention;
6. add static-analysis corroboration;
7. compare ablations and quantify uncertainty;
8. evaluate a separate project-held-out candidate.

This prevented proposed chapter outcomes from being presented as measured
results.

### Step 2: Audit the raw dataset

The raw partitions contained 224,533 records:

| Partition | Raw records | Vulnerable records | Vulnerable rate |
|---|---:|---:|---:|
| Train | 175,797 | 4,862 | 2.77% |
| Validation | 23,948 | 593 | 2.48% |
| Test | 24,788 | 549 | 2.21% |
| **Total** | **224,533** | **6,004** | — |

The audit checked parsing, schema, project overlap, commit overlap, file
provenance, function hashes, class concentration, and code-length feasibility.
The final test partition was treated as locked and was not used to fit a model,
calibrator, threshold, or operating policy.

### Step 3: Run the memory-bounded near-duplicate scan

The scan used token-based 64-bit SimHash with four 16-bit bands. Functions
shorter than 20 tokens were ignored, band buckets were capped at 256 records,
within-partition pairs were excluded, and the index was stored in temporary
SQLite rather than large Python dictionaries.

All 224,533 raw records were processed successfully. The approximate scan
produced cross-partition candidates, which were then reduced using token
5-gram Jaccard verification and provenance checks:

| Stage | Train/valid | Train/test | Valid/test | Total |
|---|---:|---:|---:|---:|
| Approximate SimHash candidates | 3,561,232 | 3,994,695 | 70,936 | 7,626,863 |
| Verified Jaccard candidates | 1,320 | 1,351 | 201 | 2,872 |

Among the 2,872 verified candidates, 1,795 were classified as high-priority
provenance overlaps. This classification identifies records requiring
conservative handling; it does not prove that every candidate is a semantic
duplicate.

### Step 4: Build the leakage-controlled manifest

The raw files remained unchanged. The derived manifest retained all training
records, excluded 915 validation records, and excluded 780 test records:

| Role | Total | Excluded | Retained |
|---|---:|---:|---:|
| Train | 175,797 | 0 | 175,797 |
| Validation/calibration | 23,948 | 915 | 23,033 |
| Locked test | 24,788 | 780 | 24,008 |

The retained validation partition was used for calibration and policy
selection. The retained test partition was used only after the protocol was
frozen.

### Step 5: Run the code-only Qwen baseline

The selected open-source model was:

```text
Qwen/Qwen2.5-Coder-1.5B-Instruct
Hugging Face revision: 2e1fd39
```

The initial prompt contained the function code and requested a structured
`YES`/`NO` decision. CWE, CVE, project, commit, file, and hash metadata were
not placed in the initial model prompt, preventing metadata leakage.

Inference used greedy decoding, CUDA when available, half precision, a fixed
seed, a 4,096-token input limit, and a short output limit. Smoke tests were
run first to identify loading, tokenization, output-parsing, and memory issues.
The full validation and locked-test runs were then completed.

The model produced many positive alerts. This was not a target-mapping error:
the high number of false positives is a property of the raw model behavior on
the imbalanced dataset.

### Step 6: Fit post-hoc calibration on validation only

Calibration used the retained validation results and was not fitted using test
labels. Temperature scaling was retained as the useful calibration branch.
Platt scaling was also tested, but it did not produce useful positive decisions
at the intended operating threshold. The selected temperature was:

```text
temperature = 445.683640902898
```

The calibration artifacts were saved separately and reused for the frozen
test application.

### Step 7: Add conformal/selective abstention

The conformal stage converted calibrated confidence into a prediction set. The
primary frozen significance level was:

```text
alpha = 0.10
```

The system accepted a positive decision only when the calibrated conformal
prediction set was exactly `[1]`. Other cases became `ABSTAIN` and were intended
for human review. This is why ordinary binary accuracy is not the primary
metric: most records are deliberately not converted into accepted automated
decisions.

### Step 8: Add Semgrep static corroboration

Semgrep Community Edition was used as an independent rule-based signal. A
function-local C/C++ rule pack was applied to the code. The absence of a
Semgrep finding was treated as neutral, not as proof that the code was safe.

On the 38,362-record project-held-out candidate, Semgrep found:

| Quantity | Result |
|---|---:|
| Records scanned | 38,362 |
| Records with a finding | 3,654 |
| Static true positives | 327 |
| Static positive precision | 8.95% |
| Static positive recall | 30.33% |

### Step 9: Evaluate the hybrid and ablations

The primary hybrid acceptance rule was:

```text
accept YES only if:
    conformal prediction set == [1]
    AND at least one Semgrep finding exists
otherwise:
    ABSTAIN
```

This rule was compared with raw Qwen, temperature/conformal-only acceptance,
and Semgrep-only acceptance. The hybrid produced the best accepted-alert
precision on the official test, but also the lowest coverage and recall.

### Step 10: Freeze the operating policy and evaluate the locked test

The official leakage-controlled test partition contained 24,008 records,
including 522 vulnerable records. The frozen alpha `0.10` policy was applied
without test-label fitting or threshold retuning.

| Method | Coverage | Accepted-positive precision | Vulnerable recall |
|---|---:|---:|---:|
| Raw Qwen | 99.08% | 2.01% | 91.76% |
| Temperature + conformal only | 9.66% | 4.66% | 20.69% |
| Semgrep only | 6.31% | 6.87% | 19.92% |
| Frozen hybrid | 1.88% | 7.96% | 6.90% |

The main result is therefore a selective-review improvement: accepted-alert
precision increased from 2.01% for raw Qwen to 7.96% for the frozen hybrid, at
the cost of much lower coverage and vulnerable-record recall.

### Step 11: Quantify uncertainty

Five thousand record-level paired bootstrap resamples and 5,000 whole-project
clustered resamples were run. The frozen hybrid's precision advantage over raw
Qwen was:

```text
+5.95 percentage points
record-level 95% interval:    +3.60 to +8.54
project-clustered interval:   +3.48 to +8.75
```

The precision difference from Semgrep alone included zero, so the study does
not claim a statistically established precision advantage over Semgrep alone.

### Step 12: Run the separate project-held-out improvement evaluation

A separate candidate was created from 400 projects absent from the official
validation and test partitions. It contained 38,362 records, including 1,078
vulnerable records. This candidate was not used to alter the official locked
test result.

The higher-recall alpha `0.50` policy was compared with the frozen alpha `0.10`
policy:

| Policy | Coverage | Accepted-positive precision | Vulnerable recall |
|---|---:|---:|---:|
| Frozen alpha `0.10` | 2.89% | 11.01% | 11.32% |
| Higher-recall alpha `0.50` | 8.01% | 8.86% | 25.23% |

The paired difference for alpha `0.50` minus alpha `0.10` was:

| Metric | Difference | Project-clustered 95% interval |
|---|---:|---:|
| Coverage | +5.12 pp | +4.13 to +6.19 pp |
| Precision | −2.15 pp | −3.45 to −0.89 pp |
| Recall | +13.91 pp | +11.29 to +16.57 pp |

This is a stable operating-point trade-off, not an across-the-board
improvement. The alpha `0.10` frozen policy remains the primary result.

### Parameter choices and their rationale

The values below were not all chosen in the same way. Some are fixed
engineering/protocol settings, some are fitted using validation data, and some
are candidate operating points. The locked test was not used to choose any of
them.

| Parameter or setting | Simple meaning | Value used | Why this value was used | Selection status |
|---|---|---|---|---|
| Primary model | The open-source program used to review code | `Qwen/Qwen2.5-Coder-1.5B-Instruct` | It is an openly available code model that can be loaded in Google Colab and is large enough to perform code reasoning while remaining practical for the available hardware | Fixed before full inference |
| Model revision | Exact saved version of the model | `2e1fd39` | Pinning the revision prevents a later model update from silently changing the results | Fixed for reproducibility |
| Prompt metadata | Extra information shown to the model | Code only; no CWE, CVE, project, commit, file, or hash | This measures what the model can infer from code and prevents the label or provenance from being accidentally revealed | Fixed protocol choice |
| Output format | How the model must answer | `YES` or `NO` | A short fixed vocabulary makes parsing reproducible and avoids interpreting long explanations differently | Fixed protocol choice |
| Decoding | How the next token is selected | Greedy, `do_sample=False` | The same input should produce the same output; random sampling would add avoidable variation to the baseline | Fixed protocol choice |
| Random seed | Number used to reproduce random operations | `12345` | A fixed seed makes reruns comparable; it is not a claim that this seed is scientifically optimal | Fixed reproducibility setting |
| Data type | Numerical precision used by the model | FP16/half precision | It reduces GPU memory use and makes the open-source model feasible in Colab; the task is classification rather than high-precision numerical simulation | Hardware setting |
| Input limit | Maximum code length sent to the model | 4,096 tokens | It matches the practical context limit used by the runner and prevents very long functions from exhausting GPU memory | Fixed feasibility setting |
| Output limit | Maximum generated answer length | 16 tokens | The required answer is only `YES`/`NO` plus a short structured response, so longer generation adds cost without useful information | Fixed efficiency setting |
| Minimum function length for SimHash | Smallest function considered in approximate similarity search | 20 tokens | Extremely short functions do not contain enough code structure for a meaningful near-duplicate comparison and would create noisy matches | Fixed triage rule |
| SimHash size | Compact fingerprint for code tokens | 64 bits | A 64-bit fingerprint is small enough for memory-bounded indexing while still supporting approximate comparison | Fixed algorithm setting |
| SimHash bands | Number of pieces used to retrieve likely matches | Four bands of 16 bits | Multiple bands make similar fingerprints likely to share an index bucket without comparing every record with every other record | Fixed retrieval setting |
| Band bucket cap | Maximum records retained in one similarity bucket | 256 | A popular bucket can otherwise create a very large number of pair comparisons; the cap keeps the scan memory-bounded | Fixed resource safeguard |
| Hamming threshold | Number of different bits allowed between fingerprints | At most 8 | This was used as a broad triage threshold to find plausible cross-partition candidates; it is not a semantic-duplicate decision | Fixed triage threshold |
| Token sample cap | Maximum tokens used to form one SimHash | 256 evenly spaced tokens | Long functions otherwise dominate computation and memory; evenly spaced tokens preserve information across the function | Fixed resource safeguard |
| Jaccard verification threshold | Required overlap between token 5-gram sets | At least 0.80 | A second, more direct lexical-overlap check removes many loose SimHash candidates; it is still approximate rather than semantic proof | Fixed verification threshold |
| Exclusion policy | Which provenance candidates are removed from evaluation | High-priority cross-partition candidates | The aim is conservative leakage control: likely related records are excluded from validation/test rather than risking an optimistic estimate | Protocol decision |
| Calibration data | Data used to learn confidence correction | Retained validation partition, 23,033 records | Calibration must be learned before the test is opened; validation is the appropriate development set | Fixed protocol choice |
| Temperature scaling | One number that reshapes model confidence | Fitted value `445.683640902898` | The value was optimized on validation labels to reduce confidence misalignment; it is large because it operates on the model's raw logit scale | Fitted on validation only |
| Conformal alpha | Allowed error level for the selective gate | Primary `0.10` | A 10% significance level corresponds to the chapter's target of conservative decisions and gives a clear frozen operating point | Selected using validation protocol |
| Higher-recall alpha | More permissive candidate gate | `0.50` | This was tested to examine whether accepting more cases could recover vulnerable records; it was retained as an alternative, not substituted for the frozen policy | Validation-selected candidate |
| Semgrep version | Static-analysis tool version | Community Edition `1.163.0` | Pinning the tool version ensures that rule behavior can be reproduced | Fixed tool version |
| Semgrep batch size | Number of functions processed together | 512 | This balances throughput and memory use for the project-held-out scan | Fixed execution setting |
| Hybrid acceptance rule | Condition for accepting an automated positive | Conformal set exactly `[1]` AND at least one Semgrep finding | Requiring both signals is conservative: the LLM must be confident and a rule must provide corroborating evidence | Frozen policy definition |
| Bootstrap repetitions | Number of resampled datasets used for uncertainty | 5,000 record-level and 5,000 project-level | This gives stable percentile intervals while remaining computationally manageable | Fixed statistical setting |
| Project clustering | Unit sampled in the sensitivity analysis | Whole projects, not individual records | Records from the same project may be related, so treating every record as independent can make uncertainty look too small | Fixed sensitivity analysis |
| Project-held-out candidate | Separate evaluation population | 400 train-only projects, 38,362 records | It tests the selected policies on projects absent from official validation/test without changing the locked benchmark | Prespecified candidate study |

The important methodological rule is that a parameter can be described as
“validation-selected” only when it was chosen without using the final test
labels. A value being numerically precise does not mean it is universally
optimal; it means that it was the value produced by the specified fitting or
selection procedure.

### Plain-language glossary

| Technical term | Short and simple meaning |
|---|---|
| Baseline | The first simple experiment used as a reference for later methods |
| Vulnerability | A coding weakness that can create a security or correctness problem |
| LLM | A language model that predicts text; here it is asked to review code |
| Confidence | How strongly the model favors one answer over another |
| Calibration | Adjusting confidence so that it better matches how often predictions are correct |
| Temperature scaling | A calibration method that changes the sharpness of model probabilities using one learned number |
| Conformal prediction | A method that uses validation errors to decide when a prediction is sufficiently reliable |
| Abstention | Deliberately refusing to make an automatic decision and sending the case for review |
| Selective prediction | Predicting only on cases judged reliable and abstaining on the rest |
| Corroboration | Independent supporting evidence from another method |
| Static analysis | Checking code with fixed rules instead of generating an answer with a language model |
| Semgrep | The static-analysis tool used to search code for suspicious patterns |
| Hybrid pipeline | A system that combines the LLM, calibration, abstention, and static rules |
| Precision | Of the alerts made, the percentage that are truly vulnerable |
| Recall | Of all vulnerable records, the percentage successfully alerted on |
| Coverage | The percentage of all records for which the selective system gives an accepted decision |
| Abstention rate | The percentage of records for which the system refuses to decide |
| False positive | A record flagged as vulnerable when it is not vulnerable |
| False negative | A vulnerable record that the system fails to flag |
| True positive | A vulnerable record correctly flagged |
| True negative | A non-vulnerable record correctly left unflagged |
| Accepted-positive precision | Precision calculated only among records that the selective policy accepts as positive |
| Locked test | A final evaluation set that is not used to make modelling decisions |
| Data leakage | Information from evaluation data accidentally influencing training or policy selection |
| Provenance | Information about where code came from, such as project, file, or commit |
| Near duplicate | Code that looks very similar to another record, but has not necessarily been proven to have the same meaning |
| SimHash | A compact fingerprint that helps quickly find possibly similar code |
| Hamming distance | The number of bit positions that differ between two fingerprints |
| Token | A small piece of text, such as a keyword, identifier, or punctuation item |
| 5-gram | A sequence of five neighboring tokens |
| Jaccard similarity | A score measuring how much two sets overlap; 1.0 means identical sets |
| Ablation | Removing or changing one component to see what contribution it makes |
| Bootstrap | Repeatedly resampling the results to estimate uncertainty around a metric |
| Project-clustered interval | An uncertainty interval that resamples whole projects to account for related records |
| Project-held-out evaluation | Testing on projects deliberately kept separate from the development partitions |
| Candidate result | A result that is useful for investigation but is not automatically a confirmed claim |
| Semantic duplicate | Two code records judged to have the same meaning; similarity alone does not prove this |
| pp | Percentage points; for example, 11% to 8% is a decrease of 3 percentage points |

## 6. What was achieved

### Methodological achievements

1. A reproducible code-only vulnerability-review protocol was defined.
2. The raw PrimeVul partitions were audited without altering the dataset.
3. Approximate near-duplicate and provenance risks were explicitly handled.
4. Calibration was separated from locked-test evaluation.
5. Abstention was implemented instead of forcing a prediction on every case.
6. Static corroboration was added as a separate evidence signal.
7. The system was evaluated through ablations rather than only one final score.
8. Record-level and project-clustered uncertainty intervals were reported.
9. An independent project-held-out candidate tested whether the operating-point
   trade-off persisted on projects absent from the official partitions.

### Empirical achievements

The frozen hybrid increased accepted-alert precision over raw Qwen from
2.01% to 7.96% on the official locked test. This supports the selective-review
hypothesis, but not a claim of high-recall autonomous vulnerability detection.

The separate alpha `0.50` candidate increased recall and coverage relative to
alpha `0.10`, but precision decreased. This demonstrates a useful configurable
operating-point trade-off rather than a universally superior system.

## 7. How the work is useful

The practical contribution is a risk-aware review triage design:

- high-confidence, multiply corroborated cases can be prioritized;
- uncertain cases are abstained and escalated to a human reviewer;
- the system does not pretend that a missing static-analysis finding proves
  safety;
- the operating point can be selected according to whether a team values
  precision or recall more strongly;
- the evaluation reports the cost of selectivity instead of hiding it inside a
  single accuracy number;
- the provenance audit provides a defensible basis for leakage-aware reporting.

In practical terms, the frozen policy is best described as a high-precision
review-triage mode, not as a complete replacement for expert vulnerability
analysis.

## 8. What cannot currently be claimed

The following claims would be unsupported:

- that the pipeline improves every metric simultaneously;
- that the model has high vulnerable-record recall after abstention;
- that the hybrid is universally better than Semgrep;
- that the official locked test is an unseen-project benchmark;
- that every approximate near-duplicate is a confirmed semantic duplicate;
- that Qwen is universally superior to other models;
- that all experiments proposed in the chapter have been completed;
- that the alpha `0.50` candidate should replace the frozen alpha `0.10` result.

The remaining optional chapter extensions include reliability diagrams,
error-reject curves, AUROC under an explicitly defined score policy,
F1/accuracy/FPR expansions, subgroup analysis, Pearson correlation, Cohen's
kappa, verbal-confidence prompts, self-consistency, and ensemble calibration.

## 9. Suggested thesis figures

The following figures can be produced directly from the recorded artifacts:

1. **Methodology flow diagram.** Show code input, Qwen prediction, calibration,
   conformal decision, Semgrep corroboration, and the final `ACCEPT` or
   `ABSTAIN` outcome.
2. **Dataset and leakage-control flow.** Show the 224,533 raw records, the
   approximate SimHash candidates, verified similarity candidates, provenance
   review, and the retained validation/test counts.
3. **Precision–coverage operating-point plot.** Plot raw Qwen,
   temperature/conformal-only, Semgrep-only, frozen hybrid, and higher-recall
   candidate policies. This figure should make the selectivity trade-off clear.
4. **Locked-test method comparison.** Use grouped bars for coverage,
   accepted-positive precision, and vulnerable-record recall. The caption must
   state that abstentions are excluded from accepted-positive precision.
5. **Project-held-out policy comparison with uncertainty.** Show the alpha
   `0.10` and alpha `0.50` policies with project-clustered intervals for
   coverage, precision, and recall.
6. **Error-reject curve.** This remains an optional future figure because the
   final score-ranking convention and full curve were not yet generated.

## 10. Supervisor demonstration checklist

If asked to demonstrate the work, show the files in this order:

1. This briefing document.
2. The source chapter PDF and the master implementation report.
3. The raw PrimeVul files and the leakage-controlled manifest.
4. The near-duplicate/provenance reports.
5. The Qwen validation and test output files.
6. The calibration and conformal reports.
7. The Semgrep rule pack and corroboration output.
8. The locked-test results and bootstrap statistics.
9. The project-held-out results and direct policy comparison statistics.
10. The thesis-ready tables and discussion document.

## 11. Exact file inventory

### 11.1 Source chapter and durable context

- `C:\Users\rehan\OneDrive\Desktop\Thesis\draft\chapter.pdf`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\THESIS_CONTEXT.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\chat_history.md`

### 11.2 Raw dataset and manifests

- `C:\Users\rehan\OneDrive\Desktop\Thesis\datasets\PrimeVul\PrimeVul_v0.1-20260930T034251Z-1-001\PrimeVul_v0.1\primevul_train.jsonl`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\datasets\PrimeVul\PrimeVul_v0.1-20260930T034251Z-1-001\PrimeVul_v0.1\primevul_valid.jsonl`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\datasets\PrimeVul\PrimeVul_v0.1-20260930T034251Z-1-001\PrimeVul_v0.1\primevul_test.jsonl`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\datasets\PrimeVul\PrimeVul_v0.1-20260930T034251Z-1-001\PrimeVul_v0.1\file_info.json`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\datasets\PrimeVul\PrimeVul_v0.1-20260930T034251Z-1-001\PrimeVul_v0.1\thesis_primevul_leakage_controlled_manifest.json`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\primevul_unseen_project_holdout_manifest.json`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\VERIFIED_REVIEW_REPORT.json`

### 11.3 Archived scripts and notebooks

The exact archived snapshots used for the implementation are stored in:

`C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts`

The principal scripts are:

| Purpose | Absolute path |
|---|---|
| Dataset audit | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts\primevul_audit.py` |
| SimHash scan | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts\near_duplicate_scan.py` |
| Similarity verification | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts\near_duplicate_verify.py` |
| Provenance review | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts\review_near_duplicate_pairs.py` |
| High-priority triage | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts\triage_high_priority_pairs.py` |
| High-priority group manifest | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts\build_high_priority_group_manifest.py` |
| Leakage manifest | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts\build_leakage_controlled_manifest.py` |
| Unseen-project manifest | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts\build_unseen_project_holdout.py` |
| Qwen smoke test | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts\run_qwen_sample.py` |
| Qwen inference runner | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts\run_qwen_colab.py` |
| Calibration | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts\fit_qwen_calibration.py` |
| Conformal abstention | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts\run_conformal_abstention.py` |
| Semgrep corroboration | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts\run_semgrep_corroboration.py` |
| Semgrep rules | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts\semgrep_primevul_rules.yml` |
| Validation hybrid evaluation | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts\evaluate_hybrid_validation.py` |
| Policy selection | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts\select_validation_operating_policy.py` |
| Frozen-policy application | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts\apply_frozen_policy.py` |
| Locked-test statistics | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts\run_locked_test_statistics.py` |
| Project-clustered statistics | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts\run_project_clustered_statistics.py` |
| Higher-recall validation sweep | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts\run_high_recall_validation_sweep.py` |
| Higher-recall policy | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts\apply_high_recall_candidate_policy.py` |
| Direct policy comparison | `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts\run_unseen_policy_comparison_statistics.py` |

An archived OpenAI-baseline runner also exists for a planned comparative
experiment, but it was not part of the completed Qwen/PrimeVul results:

`C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts\run_openai_baseline.py`

Archived Colab notebooks:

- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts\primevul_qwen_colab.ipynb`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts\primevul_qwen_test_colab.ipynb`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts\primevul_qwen_unseen_project_colab.ipynb`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts\primevul_semgrep_unseen_project_colab.ipynb`

The complete archive manifest, including SHA-256 hashes, is:

`C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts\SCRIPT_ARCHIVE_MANIFEST.json`

### 11.4 Primary inference and evaluation outputs

Validation and official locked-test outputs:

- `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\qwen_smoke_valid.json`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\qwen_valid_results_full.jsonl`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\qwen_valid_results_fixed.jsonl`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\qwen_test_results.jsonl`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\semgrep_test_results.json`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\frozen_test_policy_results.json`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\locked_test_statistics.json`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\project_clustered_test_statistics.json`

Project-held-out outputs:

- `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\qwen_unseen_project_results.jsonl`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\qwen_unseen_project_results.jsonl.meta.json`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\semgrep_unseen_project_results.json`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\frozen_unseen_project_policy_results.json`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\high_recall_unseen_project_policy_results.json`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\unseen_policy_comparison_statistics.json`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\unseen_frozen_record_statistics_5000.json`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\unseen_high_recall_record_statistics_5000.json`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\unseen_frozen_project_statistics_5000.json`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\unseen_high_recall_project_statistics_5000.json`

Validation policy and calibration outputs:

- `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\validation_high_recall_policy_sweep.json`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\validation_high_recall_extended_sweep.json`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\high_recall_candidate_test_policy_results.json`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\frozen_test_policy_results.json`

### 11.5 Temporary and intermediate artifacts

These files support reproducibility but may be temporary or machine-specific:

- `C:\Users\rehan\AppData\Local\Temp\thesis_qwen_calibration_artifacts.json`
- `C:\Users\rehan\AppData\Local\Temp\thesis_qwen_conformal_artifacts.json`
- `C:\Users\rehan\AppData\Local\Temp\thesis_primevul_near_duplicate_verify.json`
- `C:\Users\rehan\AppData\Local\Temp\thesis_primevul_near_duplicate_review.json`
- `C:\Users\rehan\AppData\Local\Temp\thesis_semgrep_test.json`
- `C:\Users\rehan\AppData\Local\Temp\thesis_frozen_test_policy.json`

The conformal artifact used by the policy application is specifically:

`C:\Users\rehan\AppData\Local\Temp\thesis_qwen_conformal_artifacts.json`

### 11.6 Thesis reports and tables

- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\THESIS_MASTER_IMPLEMENTATION_REPORT.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\thesis_progress_report.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\thesis_decisions.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\thesis_results_discussion_tables.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\qwen_validation_baseline_report.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\qwen_calibration_report.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\qwen_conformal_report.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\qwen_static_corroboration_report.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\qwen_hybrid_validation_report.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\qwen_test_baseline_report.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\qwen_test_frozen_policy_report.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\qwen_locked_test_statistics_report.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\qwen_project_clustered_statistics_report.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\qwen_high_recall_improvement_report.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\qwen_unseen_project_run_report.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\unseen_project_policy_results_report.md`
- `C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\unseen_project_holdout_protocol.md`

## 12. Recommended explanation to the supervisor

The concise explanation is:

> The project investigates whether a calibrated, selective LLM code-review
> pipeline can improve the reliability of vulnerability alerts. We audited
> PrimeVul for cross-partition similarity, froze a leakage-controlled
> validation/test protocol, evaluated Qwen as an open-source baseline, fitted
> calibration only on validation data, added conformal abstention and Semgrep
> corroboration, and evaluated the frozen hybrid on the locked test. The
> hybrid improved accepted-alert precision from 2.01% to 7.96%, but reduced
> coverage and recall because it abstained on most records. A separate
> project-held-out study showed that a higher-recall operating point increased
> recall from 11.32% to 25.23% and coverage from 2.89% to 8.01%, while reducing
> precision from 11.01% to 8.86%. Therefore the contribution is a reliable
> selective-review and operating-point framework, not a claim that every metric
> improves simultaneously.

## 13. Final status

The main empirical pipeline and its thesis-ready evidence are complete. The
official alpha `0.10` locked-test hybrid is the primary result. The alpha
`0.50` project-held-out result is an auxiliary higher-recall operating mode.
Further experiments are possible, but they are optional extensions and must be
selected using validation data without retuning the completed locked test.

