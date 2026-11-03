# Frozen operating policy for final-test evaluation

**Freeze status:** frozen for the next locked-test evaluation  
**Freeze date:** 2026-10-26  
**Selection data:** retained validation only  
**Test labels used for selection:** no

## Policy

The final-test pipeline will use:

1. Qwen `Qwen/Qwen2.5-Coder-1.5B-Instruct`, revision `2e1fd39`;
2. temperature scaling fitted on the validation model-calibration split;
3. split-conformal prediction using the validation conformal-calibration
   scores at significance `α=0.10`;
4. Semgrep Community Edition `1.163.0` with the archived local rule pack;
5. a corroborated-positive gate:
   - emit `YES` only when the conformal prediction set is the singleton `[1]`
     and Semgrep reports at least one finding;
   - emit `ABSTAIN` in every other case, including singleton `[0]`, both-label
     sets, empty sets, missing pairwise scores, unparseable outputs, and
     missing static-analysis results.

The policy deliberately does not auto-accept `NO`. Semgrep absence is neutral,
not proof of safety. Abstentions are escalated for manual review in the
operational interpretation.

## Selection rationale

The illustrative validation cost model was false-negative cost `10`,
false-positive cost `1`, and manual-review cost `0.5`, with a minimum positive
recall floor of `10%`. Under that guardrail, temperature scaling plus static
corroboration at `α=0.10` was the lowest-cost candidate among the tested
validation policies. It achieved 2.28% coverage, 97.72% abstention, 13.46%
accepted precision, and 13.33% positive recall on the 4,571-record hybrid
validation evaluation subset.

These validation metrics are not final-test results. The cost model and recall
floor are protocol assumptions and must be disclosed in the thesis.

## Test lock rules

- Do not refit temperature, conformal scores, thresholds, or rule weights on
  test labels.
- Do not use test labels to select among policies.
- Apply the frozen policy once to the retained test outputs and report all
  records, accepted `YES`, abstentions, analyzer findings, and unresolved
  outputs.
- Preserve the raw Qwen test JSONL, Semgrep test artifact, policy output, model
  revision, analyzer version, rule-pack hash, and input hashes.

The implementation is [apply_frozen_policy.py](C:/Users/rehan/Documents/Codex/2026-10-05/i-want-all-the-chats-and/work/apply_frozen_policy.py).


