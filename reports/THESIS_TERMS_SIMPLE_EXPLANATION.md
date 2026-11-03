# Thesis Concepts Explained in Simple Terms

## A plain-language guide to the Thesis project

**Thesis title:**

**Confidence-Calibrated LLM with Selective Abstention for Reliable Automated
Code-Review Triage: A Hybrid Pipeline Combining Post-Hoc Calibration,
Conformal Gating, and Semgrep Rule Corroboration**

> Note: the correct technical spelling is **abstention**, not
> “abstentation.” Abstention means deliberately choosing not to make a
> decision when the system is not sufficiently sure.

This document explains the title and the implemented research in simple
language. It is written for a reader who may understand software and research
at a general level but may not be familiar with machine learning terminology.

## 1. The whole thesis in one paragraph

The thesis studies whether an open-source language model can help find
vulnerabilities in computer code without producing too many incorrect alerts.
The model first reviews a function and says whether it thinks the function is
vulnerable. Because the model can be overconfident, its confidence is adjusted
using validation data. The system is then allowed to refuse uncertain cases
instead of forcing an answer. Finally, a separate rule-based tool, Semgrep,
checks the code for suspicious patterns. The system accepts an alert only when
the model is sufficiently confident and the static-analysis tool provides
supporting evidence. This improves the quality of accepted alerts, but it also
means that many cases are sent to a human reviewer.

## 2. Explaining the title word by word

### 2.1 Confidence

**Simple meaning:** confidence is how sure the model appears to be about its
answer.

For example, a model might say:

```text
YES — confidence 0.95
```

This means the model strongly favors “vulnerable.” A confidence of `0.55`
means the model is only slightly more likely to choose `YES` than `NO`.

Confidence is not automatically the same as correctness. A model can be very
confident and still be wrong.

### 2.2 Calibrated confidence

**Simple meaning:** calibrated confidence is confidence adjusted so that it is
more closely related to real correctness.

Suppose a system gives 100 predictions with confidence around 80%. If 80 of
those predictions are actually correct, the confidence is well calibrated. If
only 40 are correct, the model is overconfident.

In this thesis, calibration is similar to checking and correcting a measuring
instrument. The model's original confidence is the uncorrected measurement;
the calibration stage adjusts it using a separate validation set.

### 2.3 LLM

**LLM** means **Large Language Model**.

**Simple meaning:** an LLM is a computer program trained to understand and
generate text. Because source code is also text with structure, an LLM can be
asked to inspect code and explain or classify it.

The model used in this thesis is:

```text
Qwen/Qwen2.5-Coder-1.5B-Instruct
Hugging Face revision: 2e1fd39
```

“Coder” means that the model was designed or adapted to work with programming
code. “1.5B” refers approximately to the number of model parameters. It was
selected because it is open source and practical to run in Google Colab.

The thesis evaluates one primary LLM. Therefore, “LLM” in the singular is more
precise for the completed experiment than “LLMs.”

### 2.4 Confidence-calibrated LLM

**Simple meaning:** an LLM whose confidence has been adjusted using known
examples so that the confidence is more trustworthy.

In the thesis:

1. Qwen reads a code function.
2. Qwen produces a vulnerability decision and confidence-related information.
3. Temperature scaling adjusts the confidence using validation data.
4. The final test data are not used to learn that adjustment.

This does not make the model correct in every case. It makes the decision
system more careful about how much trust it places in the model's output.

## 3. Selective abstention explained

### 3.1 What is abstention?

**Simple meaning:** abstention means saying, “I am not confident enough to
decide automatically; a human should review this case.”

A normal classifier tries to answer every question:

```text
Every input -> YES or NO
```

A selective classifier is allowed to say:

```text
Input -> YES, NO, or ABSTAIN
```

The third option is important in security review. A wrong vulnerability alert
creates wasted work, while a missed vulnerability can create risk. A cautious
system can send uncertain cases to a human instead of pretending that it knows
the answer.

### 3.2 Why abstention is useful

Imagine a junior security reviewer who is very good at recognizing obvious
problems but is unsure about difficult cases. It is safer for that reviewer to
say “please ask a senior reviewer” than to guess confidently.

Selective abstention gives the automated system the same behavior:

- obvious, well-supported cases may be accepted automatically;
- uncertain cases are escalated;
- the system's accepted alerts can become more precise;
- the system will not cover every record automatically.

### 3.3 Selective prediction

**Simple meaning:** selective prediction means making automatic predictions only
for cases that meet a reliability condition.

The system trades quantity for quality. It accepts fewer cases, but tries to
make the accepted cases more useful.

## 4. Post-hoc calibration

### 4.1 What does “post-hoc” mean?

**Simple meaning:** post-hoc means “after the model has already been trained.”

The model itself was not retrained in this thesis. Instead, its outputs were
observed on a validation set and a correction was learned afterward.

This is useful because retraining a large model can require considerable data,
time, and computing resources. Post-hoc calibration is a lighter method for
improving the interpretation of confidence.

### 4.2 Temperature scaling

Temperature scaling uses one learned number called a **temperature** to make
the model's confidence less exaggerated or more decisive.

An analogy is adjusting the sensitivity of a thermometer. The thermometer is
not replaced; its readings are rescaled so they better match known conditions.

The fitted temperature in this experiment was:

```text
445.683640902898
```

This unusually large-looking number is a value on the model's raw logit scale.
It should not be interpreted as a percentage, a probability, or a quality
score. It is simply the value produced by the validation-only fitting process.

### 4.3 Why validation data were used

The validation set is used for development decisions, such as calibration and
threshold selection. The test set is kept untouched until the final evaluation.
This prevents the system from being quietly designed to perform well on the
answers it will later be judged against.

## 5. Conformal gating in simple terms

### 5.1 What is conformal prediction?

**Simple meaning:** conformal prediction is a method that uses past validation
mistakes to decide how cautious the system should be.

Instead of asking only “what is the most likely answer?”, it asks:

> “Is there enough evidence to make this answer safely?”

If the evidence is not strong enough, the system abstains.

### 5.2 What is a gate?

**Simple meaning:** a gate is a rule that decides whether an output is allowed
to continue to the next stage.

The conformal gate works like a security checkpoint. A record must satisfy the
confidence condition before it is allowed to become an accepted positive alert.

### 5.3 What does alpha mean?

**Simple meaning:** alpha controls how strict the gate is.

The primary frozen value was:

```text
alpha = 0.10
```

The value `0.10` represents a conservative 10% significance level. A smaller
alpha generally makes the gate stricter, which usually means more abstentions.
The value was selected under the validation protocol and then frozen before the
official test evaluation.

A second candidate used:

```text
alpha = 0.50
```

This was a more permissive, higher-recall operating point. It was evaluated as
an alternative and did not replace the primary alpha `0.10` result.

### 5.4 Prediction set `[1]`

The label `1` means vulnerable. When the conformal prediction set is exactly
`[1]`, the system has enough evidence to keep only the vulnerable answer.

The primary hybrid accepted a positive alert only when:

```text
conformal prediction set == [1]
AND Semgrep found a supporting pattern
```

Every other case became `ABSTAIN` for the hybrid decision.

## 6. Rule corroboration

### 6.1 What is a rule?

**Simple meaning:** a rule is a fixed pattern that checks code for a known
warning sign.

For example, a rule might look for a dangerous function call or an unsafe way
of handling memory. Rules are not general reasoning systems; they check the
patterns that programmers have explicitly described.

### 6.2 What is corroboration?

**Simple meaning:** corroboration means getting independent supporting evidence.

In this thesis, Qwen provides one type of evidence and Semgrep provides
another. The system does not automatically trust either source by itself for
the frozen hybrid decision.

The analogy is a doctor checking a patient's symptom using both an interview
and a medical test. Agreement between two different sources can provide more
confidence, although it still does not guarantee correctness.

### 6.3 What is Semgrep?

Semgrep is a static-analysis tool. It scans source code using rules and reports
when a rule matches a suspicious pattern.

In this thesis:

- Semgrep Community Edition `1.163.0` was used;
- a local C/C++ rule pack was applied;
- a missing Semgrep finding was treated as **neutral**, not as proof of safety;
- the final hybrid required at least one Semgrep finding for an accepted
  positive alert.

## 7. What “hybrid pipeline” means

**Simple meaning:** a hybrid pipeline combines different kinds of tools into
one sequence of decisions.

The thesis pipeline is:

```text
1. Qwen reads the code.
2. Qwen produces a vulnerability decision.
3. Calibration adjusts how its confidence is interpreted.
4. Conformal gating decides whether the case is reliable enough.
5. Semgrep checks for an independent suspicious code pattern.
6. The system accepts a positive alert only when both conditions are met.
7. Otherwise, the case is abstained and can be reviewed by a human.
```

The word “pipeline” means that the output of one stage becomes the input to
the next stage.

## 8. Dataset and leakage terms

### 8.1 Dataset

A dataset is a collection of examples used to study or evaluate a system. In
this thesis, each example is a function taken from PrimeVul, together with a
label indicating whether it is vulnerable.

### 8.2 Training, validation, and test partitions

The dataset was divided into roles:

- **Training:** data used by the original model-development process;
- **Validation:** data used to calibrate confidence and select a policy;
- **Test:** final data used to measure performance after decisions are frozen.

The main experiment used the supplied partitions and did not create a random
replacement split.

### 8.3 Data leakage

**Simple meaning:** data leakage happens when information that should be
unknown during evaluation accidentally influences the system.

For example, if almost the same function appears in both development and test,
the test score may look better than the system's true ability to generalize.

### 8.4 Near duplicate

**Simple meaning:** two functions that look very similar in their code.

A near-duplicate match is a warning for further investigation. It is not by
itself proof that the two functions have identical meaning or that leakage has
definitely occurred.

### 8.5 SimHash

SimHash is a compact fingerprint for text or code.

An analogy is a short barcode for a function. Similar functions often produce
similar barcodes, so the scan can find possible matches without comparing every
pair directly.

The scan used a 64-bit SimHash, four 16-bit bands, a minimum length of 20
tokens, and a bucket cap of 256 records. These settings kept the scan
memory-bounded while finding broad candidate matches.

### 8.6 Hamming distance

Hamming distance counts how many bit positions differ between two fingerprints.

If two 64-bit fingerprints differ in only a few positions, their Hamming
distance is small and they may represent similar code. The scan reported
candidate pairs with distance at most 8.

### 8.7 Token

A token is a small piece of text, such as a keyword, variable name, number, or
punctuation mark. Code is converted into tokens so that similarity can be
measured more consistently than by comparing raw characters alone.

### 8.8 Jaccard similarity

Jaccard similarity measures how much two sets overlap.

If two functions have almost the same groups of five neighboring tokens, their
Jaccard score is high. A threshold of `0.80` was used for verification. This
was still treated as approximate evidence, not as a final semantic-duplicate
label.

### 8.9 Provenance

Provenance means the history or origin of a code record. The audit considered
project, file path, commit, hash, and related metadata.

### 8.10 Leakage-controlled manifest

A manifest is a file that records which records belong to which evaluation
role. The leakage-controlled manifest kept the raw JSONL files unchanged but
recorded conservative exclusions from validation and test.

## 9. Evaluation terms

### 9.1 True positive

A vulnerable function that the system correctly flags.

### 9.2 False positive

A non-vulnerable function that the system incorrectly flags. False positives
create unnecessary investigation work.

### 9.3 False negative

A vulnerable function that the system fails to flag. False negatives are
important because they represent missed security problems.

### 9.4 True negative

A non-vulnerable function that the system correctly leaves unflagged.

### 9.5 Precision

Precision answers:

> “When the system raises an alert, how often is that alert correct?”

Formula:

```text
precision = true positives / (true positives + false positives)
```

The frozen hybrid's accepted-positive precision on the official test was
`7.96%`, compared with `2.01%` for raw Qwen.

### 9.6 Recall

Recall answers:

> “Of all the vulnerable functions, how many did the system find?”

Formula:

```text
recall = true positives / (all truly vulnerable records)
```

The frozen hybrid had `6.90%` vulnerable-record recall on the official test.
This is low because the system abstained on most records.

### 9.7 Coverage

Coverage is the percentage of records for which the selective system makes an
accepted automatic decision.

The frozen hybrid had `1.88%` coverage on the official test. This means that
most records were not accepted automatically and could be sent for human
review.

### 9.8 Abstention rate

Abstention rate is the percentage of records for which the system does not
make an accepted automatic decision.

For a selective system, low coverage and high abstention are not necessarily a
bug. They are the cost of being cautious. The quality of the accepted alerts
and the number of cases requiring human review must be considered together.

### 9.9 Accuracy

Accuracy is the percentage of all predictions that are correct. It is often
easy to understand for a normal classifier, but it can be misleading here
because the system intentionally abstains on many records and the dataset is
imbalanced.

For this reason, the thesis emphasizes coverage, accepted-positive precision,
and vulnerable-record recall rather than claiming that a single accuracy value
proves the system is reliable.

### 9.10 Operating point

An operating point is a chosen balance between accepting more alerts and being
more selective.

- alpha `0.10` is the stricter frozen operating point;
- alpha `0.50` is the more permissive higher-recall candidate.

The higher-recall candidate increased coverage from `2.89%` to `8.01%` and
recall from `11.32%` to `25.23%`, but precision decreased from `11.01%` to
`8.86%`.

## 10. Statistical terms

### 10.1 Bootstrap

Bootstrap analysis repeatedly samples the observed results to estimate how
uncertain a metric may be.

Instead of reporting only one number, it reports a range such as:

```text
estimated precision: 7.96%
95% interval: 5.59% to 10.58%
```

The interval is not a guarantee. It shows how much the estimate changes under
the chosen resampling procedure.

### 10.2 Record-level bootstrap

Record-level bootstrap resamples individual functions. It treats each record
as the sampling unit.

### 10.3 Project-clustered bootstrap

Project-clustered bootstrap resamples whole projects. It is more cautious when
records from the same project may be related.

If many functions come from one project, treating them as completely
independent can make the result appear more certain than it really is.

### 10.4 Percentage points

Percentage points describe the direct difference between percentages.

For example:

```text
11.01% - 8.86% = 2.15 percentage points
```

This is different from saying that precision changed by 2.15 percent.

### 10.5 Ablation

An ablation removes one part of the pipeline to see what that part contributes.

The thesis compared:

- raw Qwen;
- temperature plus conformal gating;
- Semgrep alone;
- the frozen hybrid using both signals.

This helps explain not only whether the final system works, but which
components are responsible for its behavior.

## 11. What the results mean in everyday language

The raw Qwen model was willing to flag almost everything. This gave high recall
but very low precision: most alerts were wrong.

The frozen hybrid became much more cautious. It accepted far fewer records, but
the accepted alerts were more useful. This supports the idea of automated
review triage, where the tool highlights a small number of stronger cases and
sends uncertain cases to humans.

The higher-recall policy showed that the system can be made less cautious. It
found more vulnerable records and covered more of the dataset, but it also
created more false alerts. Therefore, there was no single setting that improved
precision, recall, and coverage all at once.

The main conclusion is not “the system solves vulnerability detection.” The
more accurate conclusion is:

> Calibration, selective abstention, and rule corroboration can create a more
> conservative and higher-precision review-triage mode, but the improvement is
> obtained by abstaining on many cases and does not eliminate the need for
> human review.

## 12. One-minute explanation for a non-technical listener

> We asked an open-source AI model to inspect computer functions and identify
> possible security weaknesses. The model initially marked almost everything,
> so many of its warnings were incorrect. We used a separate validation set to
> adjust how much trust we place in its confidence. We then allowed the system
> to refuse uncertain cases instead of forcing an answer. A second program,
> Semgrep, checked the code using fixed security rules. We accepted an alert
> only when both the confidence-based check and the rule-based check supported
> it. This reduced the number of accepted alerts and improved their precision,
> but it also missed or deferred many vulnerable cases. The result is best
> understood as a cautious assistant for prioritizing human code review, not as
> a complete replacement for a security expert.

## 13. Main evidence files

The complete supervisor briefing is available at:

`C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\THESIS_SUPERVISOR_BRIEFING.md`

The thesis-ready tables and discussion are available at:

`C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\thesis_results_discussion_tables.md`

The master implementation record is available at:

`C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\THESIS_MASTER_IMPLEMENTATION_REPORT.md`

The official locked-test report is available at:

`C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\qwen_test_frozen_policy_report.md`

The project-held-out report is available at:

`C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\docs\unseen_project_policy_results_report.md`


