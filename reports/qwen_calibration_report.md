# Qwen Validation Confidence Calibration Report

**Experiment date:** 2026-10-26  
**Stage:** Post-hoc confidence calibration  
**Source:** Clean Qwen PrimeVul validation baseline  
**Final test used:** No

## 1. Purpose

This report documents the first post-hoc calibration analysis for the raw
Qwen validation baseline. The calibration analysis uses only the retained
validation output and a deterministic stratified split. The locked test
partition was not read, used, or used for threshold selection.

The purpose is to measure whether raw first-token YES/NO scores can be mapped
to probabilities that better reflect the observed vulnerability frequency.
This report does not yet implement conformal abstention or static-analysis
corroboration.

## 2. Confidence-score definition

For records whose first-token top-five output contained both exact tokens
`YES` and `NO`, the binary score was defined as:

```text
p_yes_pair = p(YES) / (p(YES) + p(NO))
```

The corresponding logit score was:

```text
score = log(p_yes_pair / (1 - p_yes_pair))
```

This pairwise normalization is a diagnostic binary score derived from the
first-token probabilities. It is not the full-vocabulary probability of the
YES class and is not calibrated before fitting.

Records missing either token from the retained top-five list were excluded
from the calibration fit and reported explicitly rather than assigned a
default probability.

## 3. Calibration split

The 22,850 records with an extractable pairwise score were divided by a
deterministic stratified split using seed `12345`:

| Split | Records | Target 0 | Target 1 |
|---|---:|---:|---:|
| Calibration fit | 18,279 | 17,860 | 419 |
| Held-out validation evaluation | 4,571 | 4,466 | 105 |
| Missing score | 183 | Not fitted | Not fitted |

The calibration split is internal to the validation/development partition. It
does not change the locked-test policy.

## 4. Fitted calibration parameters

### Temperature scaling

Temperature scaling fits:

```text
p_calibrated = sigmoid(score / T)
T = 445.683640902898
```

### Platt scaling

Platt scaling fits:

```text
p_calibrated = sigmoid(a * score + b)
a = 1.5423058083548482
b = -5.991508345905061
```

Both methods were fitted by minimizing negative log likelihood on the
calibration split only.

## 5. Held-out validation metrics

The following metrics are calculated on the held-out portion of the validation
partition. Classification metrics use a probability threshold of `0.5`.

| Method | Accuracy | Precision (`YES`) | Recall (`YES`) | Brier | Log loss | ECE (10 bins) |
|---|---:|---:|---:|---:|---:|---:|
| Raw pairwise score | 2.32% | 2.30% | 100.00% | 0.6166 | 1.5716 | 0.7699 |
| Temperature scaling | 2.32% | 2.30% | 100.00% | 0.2507 | 0.6946 | 0.4778 |
| Platt scaling | 97.70% | 0.00% | 0.00% | 0.0226 | 0.1065 | 0.0027 |

The Platt-calibrated maximum probability on the held-out validation records
was approximately 0.354, so no record crossed the 0.5 classification
threshold. Its high accuracy is therefore dominated by the 97.7% negative
class prevalence and should not be interpreted as useful vulnerability
detection.

## 6. Interpretation

The raw score is severely overconfident relative to the validation prevalence:
the mean raw pairwise YES score was approximately 0.793, while the positive
rate of the scored validation records was approximately 2.29%.

Temperature scaling reduced the probability magnitude and improved Brier score,
log loss, and ECE, but it did not change the thresholded classification because
the fitted temperature moved scores close to 0.5 without producing useful
separation.

Platt scaling produced much better probability-proper scoring on the imbalanced
validation set, but its default threshold produced no positive predictions.
This is a calibration and decision-policy warning: probability calibration and
classification-threshold selection are separate decisions. A threshold of
0.5 is not automatically appropriate for a rare-vulnerability screening task.

These results support the Thesis motivation for selective prediction, but they
do not establish that calibration alone improves operational code review. The
next step must evaluate coverage/precision trade-offs over calibrated scores
and define an abstention rule without using the locked test partition.

## 7. Limitations

1. The score was derived from retained top-five token probabilities; 183 records
   lacked both YES and NO tokens and were excluded from calibration fitting.
2. The 177 unparseable text responses in the original baseline remain a
   separate response-resolution issue.
3. The calibration split and held-out evaluation split are both within the
   validation partition; neither is the final test evaluation.
4. ECE uses ten equal-width bins and should be reported with this definition.
5. The high Platt-scaled accuracy is misleading under the severe class
   imbalance and must be accompanied by precision, recall, and coverage.

## 8. Reproducibility artifacts

| Artifact | Location |
|---|---|
| Calibration script | [fit_qwen_calibration.py](C:/Users/rehan/Documents/Codex/2026-10-05/i-want-all-the-chats-and/work/fit_qwen_calibration.py) |
| Archived script snapshot | [fit_qwen_calibration.py](C:/Users/rehan/Documents/Codex/2026-10-05/i-want-all-the-chats-and/outputs/thesis-codex-context/scripts/fit_qwen_calibration.py) |
| Clean baseline JSONL | [qwen_valid_results_fixed.jsonl](C:/Users/rehan/OneDrive/Desktop/Thesis/implementation/qwen_valid_results_fixed.jsonl) |
| Calibration artifact JSON | `C:/Users/rehan/AppData/Local/Temp/thesis_qwen_calibration_artifacts.json` |
| Clean baseline report | [qwen_validation_baseline_report.md](C:/Users/rehan/Documents/Codex/2026-10-05/i-want-all-the-chats-and/outputs/thesis-codex-context/docs/qwen_validation_baseline_report.md) |

## 9. Thesis-ready result statement

> On 22,850 retained validation records with extractable YES/NO first-token
> scores, raw pairwise scores were calibrated using a deterministic stratified
> 80/20 validation-only split. Temperature scaling reduced the held-out Brier
> score from 0.6166 to 0.2507, while Platt scaling reduced it to 0.0226 and
> reduced ECE to 0.0027. However, Platt scaling assigned every held-out record
> a probability below 0.5, producing no positive predictions at the default
> threshold. Thus, calibration improved probability alignment under the
> imbalanced validation distribution but did not by itself provide an
> operational vulnerability decision rule. Threshold selection and selective
> abstention must therefore be evaluated separately without using the locked
> test partition.

