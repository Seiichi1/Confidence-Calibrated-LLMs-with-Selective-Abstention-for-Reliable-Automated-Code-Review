# Validation-Only Operating-Policy Sweep

**Stage:** Cost-sensitive operating-point analysis  
**Date:** 2026-10-26  
**Evaluation records:** 4,571 common conformal/Semgrep validation records  
**Final test used:** No

## 1. Purpose

The preceding experiments produced several conformal-only and hybrid candidate
gates. This analysis compares them under explicit operational costs rather than
selecting a threshold from accuracy alone. It is a validation-only policy
analysis. The resulting policy is now frozen for the next locked-test
evaluation in `THESIS_OPERATING_POLICY.md`.

The cost function is:

`normalized cost = (10 × false negatives) + (1 × false positives) + (0.5 × abstentions)`,

divided by the number of evaluation records in the default scenario. An
abstention represents escalation to manual review. The sweep also evaluates
false-negative costs of 5, 10, 20, 50, and 100, review costs of 0.1, 0.25,
0.5, 1, and 2, and positive-recall floors of 5%, 10%, and 20%.

## 2. Security guardrail

An unconstrained cost minimum is not sufficient for this Thesis because a
policy that accepts only negative decisions can have high accepted precision
and zero vulnerability recall. Therefore policy candidates are also ranked
under explicit minimum positive-recall floors.

## 3. Default-cost results

Without a positive-recall constraint, the lowest-cost candidate under the
default scenario was Platt conformal singleton at significance 0.10:

| Candidate | Coverage | Abstention | Accepted precision | Positive recall | Normalized cost |
|---|---:|---:|---:|---:|---:|
| Platt conformal singleton, α=0.10 | 92.63% | 7.37% | 98.02% | 0.00% | 0.2206 |

This candidate is rejected as a security operating policy because it accepts no
vulnerable records as `YES`. The result demonstrates why positive recall must
be constrained explicitly.

## 4. Recall-constrained candidates

| Minimum positive recall | Candidate | Significance | Coverage | Abstention | Accepted precision | Positive recall | Normalized cost |
|---:|---|---:|---:|---:|---:|---:|---:|
| 5% | Temperature + corroborated positive | 0.05 | 1.14% | 98.86% | 15.38% | 7.62% | 0.5039 |
| 10% | Temperature + corroborated positive | 0.10 | 2.28% | 97.72% | 13.46% | 13.33% | 0.5083 |
| 20% | Temperature + corroborated positive | 0.50 | 6.78% | 93.22% | 6.77% | 20.00% | 0.5293 |

These are candidate validation operating points, not final claims. The 10%
recall-floor candidate is a reasonable provisional reference because it keeps
the explicit security guardrail while retaining the static-corroboration
benefit. It still abstains on 97.72% of the evaluation records, so its manual
review burden must be considered before deployment.

## 5. Sensitivity and decision

The preferred policy changes when the relative cost of manual review or missed
vulnerabilities changes. A low review cost favors broad abstention; a high
false-negative cost favors higher-recall temperature operating points. The
validation data therefore do not justify silently freezing one threshold.

The cost weights and minimum positive-recall floor were accepted as the
validation-derived protocol assumptions. The analyzer version, rule pack,
calibrator, conformal significance level, unresolved-output policy, and
operating gate are now frozen before the retained test partition is opened.

## 6. Reproducibility

| Item | Value |
|---|---|
| Script | [select_validation_operating_policy.py](C:/Users/rehan/Documents/Codex/2026-10-05/i-want-all-the-chats-and/work/select_validation_operating_policy.py) |
| Archived script | [select_validation_operating_policy.py](C:/Users/rehan/Documents/Codex/2026-10-05/i-want-all-the-chats-and/outputs/thesis-codex-context/scripts/select_validation_operating_policy.py) |
| Conformal artifact | `C:/Users/rehan/AppData/Local/Temp/thesis_qwen_conformal_artifacts.json` |
| Static artifact | `C:/Users/rehan/AppData/Local/Temp/thesis_semgrep_valid_full.json` |
| Sweep artifact | `C:/Users/rehan/AppData/Local/Temp/thesis_validation_policy_sweep.json` |
| Policy frozen | Yes; see `THESIS_OPERATING_POLICY.md` |
| Final test used | No |


