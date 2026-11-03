# Unseen Project-Held-Out Evaluation Candidate

## Status

The project-held-out candidate has been constructed successfully. It is an
evaluation candidate only; Qwen inference and policy evaluation on it are the
next execution steps.

## Purpose

The first higher-recall policy study used the existing validation partition for
selection and the already-evaluated official test output for an exploratory
comparison. That exploratory comparison showed a recall increase but also a
precision decrease, so it cannot serve as an independent confirmation.

This artifact provides a new evaluation target drawn from the raw training
partition at whole-project granularity. It allows the candidate policy to be
evaluated on projects that do not occur in either official validation or
official test, while leaving the locked official test result unchanged.

## Selection rule

The candidate includes every record from a train project satisfying both
conditions below:

1. The project does not occur in the official validation partition.
2. The project does not occur in the official test partition.

Records associated with high-priority verified cross-partition overlap are also
excluded. This second rule is a safeguard; most such records are already
removed because their projects overlap an official evaluation partition.
Selection is deterministic and uses no Qwen predictions, validation policy
scores, or test labels.

The raw JSONL files remain unchanged. Record numbers in the manifest are
1-based JSONL line numbers, matching the existing Qwen Colab runner.

## Candidate composition

| Quantity | Value |
|---|---:|
| Source partition | raw train |
| Source train records | 175,797 |
| Source train projects | 631 |
| Official validation projects | 217 |
| Official test projects | 220 |
| Union of official evaluation projects | 354 |
| Candidate projects | 400 |
| Candidate records | 38,362 |
| Candidate non-vulnerable records (`target=0`) | 37,284 |
| Candidate vulnerable records (`target=1`) | 1,078 |
| Candidate records excluded by project rule | 137,429 |
| Additional high-priority train records excluded | 1,531 |

The candidate therefore has a positive prevalence of approximately 2.81% and
contains substantially more positive examples than the official test
partition. This improves the precision of the independent comparison while
preserving project separation.

## Files

Manifest:

`C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\primevul_unseen_project_holdout_manifest.json`

Builder script:

`C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\build_unseen_project_holdout.py`

Archived implementation snapshot:

`C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\outputs\thesis-codex-context\scripts\build_unseen_project_holdout.py`

Source dataset files used:

- `C:\Users\rehan\OneDrive\Desktop\Thesis\datasets\PrimeVul\PrimeVul_v0.1-20260930T034251Z-1-001\PrimeVul_v0.1\primevul_train.jsonl`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\datasets\PrimeVul\PrimeVul_v0.1-20260930T034251Z-1-001\PrimeVul_v0.1\primevul_valid.jsonl`
- `C:\Users\rehan\OneDrive\Desktop\Thesis\datasets\PrimeVul\PrimeVul_v0.1-20260930T034251Z-1-001\PrimeVul_v0.1\primevul_test.jsonl`

Review source:

`C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\VERIFIED_REVIEW_REPORT.json`

Semgrep Colab notebook:

`C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\primevul_semgrep_unseen_project_colab.ipynb`

## Interpretation boundary

This candidate is not a replacement for the locked official test. The locked
test remains the primary thesis result for the original protocol. The new
candidate is an independent project-held-out evaluation of the previously
selected higher-recall policy.

The policy must not be changed after inspecting candidate labels or candidate
metrics. If the candidate comparison is favorable, it should be reported as
an additional project-held-out result. If it is unfavorable, it should still
be reported as a failed or mixed improvement attempt rather than omitted.

## Next execution step

Run the existing Qwen Colab inference script against the `train` JSONL and the
`unseen_project_holdout` manifest partition. The model, revision, prompt,
decoding settings, and output schema must remain identical to the existing
validation/test runs:

```text
--data primevul_train.jsonl
--manifest primevul_unseen_project_holdout_manifest.json
--partition unseen_project_holdout
--model Qwen/Qwen2.5-Coder-1.5B-Instruct
--limit 0
```

After inference, run the existing Semgrep corroboration on the same candidate,
then apply both the original frozen policy and the higher-recall candidate
policy. Only the resulting candidate metrics should be compared; no policy
selection should be performed using this candidate.

## Post-Colab local commands

After the Colab run, copy the JSONL output and metadata into the implementation
directory. Then run the same corroboration and policy code used for the
original study. The calibration artifact remains the validation-fitted
artifact and must not be refit on this candidate.

```powershell
python C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\run_semgrep_corroboration.py `
  --data C:\Users\rehan\OneDrive\Desktop\Thesis\datasets\PrimeVul\PrimeVul_v0.1-20260930T034251Z-1-001\PrimeVul_v0.1\primevul_train.jsonl `
  --llm-results C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\qwen_unseen_project_results.jsonl `
  --rules C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\semgrep_primevul_rules.yml `
  --output C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\semgrep_unseen_project_results.json `
  --limit 0 `
  --batch-size 512

python C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\apply_high_recall_candidate_policy.py `
  --qwen-results C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\qwen_unseen_project_results.jsonl `
  --calibration-artifact C:\Users\rehan\AppData\Local\Temp\thesis_qwen_conformal_artifacts.json `
  --static-results C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\semgrep_unseen_project_results.json `
  --alpha 0.50 `
  --output C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\high_recall_unseen_project_policy_results.json

python C:\Users\rehan\Documents\Codex\2026-10-05\i-want-all-the-chats-and\work\apply_frozen_policy.py `
  --qwen-results C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\qwen_unseen_project_results.jsonl `
  --calibration-artifact C:\Users\rehan\AppData\Local\Temp\thesis_qwen_conformal_artifacts.json `
  --static-results C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\semgrep_unseen_project_results.json `
  --alpha 0.10 `
  --output C:\Users\rehan\OneDrive\Desktop\Thesis\implementation\frozen_unseen_project_policy_results.json
```

Apply the original frozen alpha `0.10` policy to the same candidate as well for
a paired comparison. Candidate labels are used only after the policy is fixed,
for evaluation and reporting—not for selecting a new threshold.

