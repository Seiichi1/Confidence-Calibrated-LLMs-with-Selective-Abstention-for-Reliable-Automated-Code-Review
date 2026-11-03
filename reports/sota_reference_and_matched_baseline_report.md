# SOTA Reference and Matched Open-Source Baseline Plan

**Thesis title:** Confidence-Calibrated LLMs with Selective Abstention for Reliable Automated Code Review  
**Evaluation date:** 2026-11-03  
**Status:** Phoenix reference reproduced; T4-compatible quantized 14B natural-test run prepared, not yet executed

## 1. Purpose

This report records the comparison with a strong recent open-source reference
and defines the next apples-to-apples baseline for the Thesis. The purpose is
not to claim that one number is universally the state of the art: vulnerability
detection papers use different datasets, pair structures, prompts, models, and
metrics.

## 2. Published reference selected

Phoenix is a recent training-free multi-agent vulnerability-detection system.
Its three stages perform semantic slicing, requirement reverse engineering,
and contract judging. The released implementation uses Qwen3.5-9B for the
slicer and judge and Qwen2.5-Coder-14B-Instruct for the requirement reverser.

The authors report the following result on the PrimeVul **paired** test set:

| Metric | Published/reproduced value |
|---|---:|
| Evaluated samples | 854 |
| Unparsed samples | 5 |
| Effective pairs | 427 |
| Vulnerable precision | 79.18% |
| Vulnerable recall | 86.01% |
| Vulnerable F1 | 82.46% |
| Pair-correct | 64.40% (275/427) |

The result is reproducible from the public Phoenix experiment archive and the
released evaluator. The exact command used was:

```text
python scripts/evaluate.py \
  --input_file primevul_judged_paired_test_A2_Qwen2.5-Coder-14B-Instruct_A3_Qwen3.5-9B.jsonl \
  --raw_file primevul_test_paired.jsonl
```

The evaluator returned TP=369, FP=97, TN=328, FN=60, with 5 unparsed outputs.
The eight omitted pairs explain the difference between the original 435 pairs
and the effective 427-pair evaluation.

## 3. Why Phoenix is not a direct comparator for the Thesis test result

The Thesis locked-test evaluation uses 24,008 naturally occurring records after
the leakage-control manifest is applied. These records are not arranged as
vulnerable/fixed pairs, and the Thesis prompt supplies one function at a time.

Phoenix requires the paired setting because its central behavioral-contract
step derives a security distinction from vulnerable and fixed versions. Running
Phoenix on the paired file would therefore change both the input unit and the
available information. Its 82.46% F1 and 64.40% pair-correct result must be
reported as a **paired-benchmark reference**, not as evidence that it outperforms
or is outperformed by the Thesis hybrid on the natural locked test.

This distinction is methodologically important:

| Dimension | Thesis locked test | Phoenix reference |
|---|---|---|
| Input unit | Natural single functions | Vulnerable/fixed pairs |
| Test size | 24,008 retained records | 870 source samples, 427 effective pairs |
| Extra fixed-version information | Not available | Used by the contract-synthesis pipeline |
| Main metric | Accepted-alert precision, coverage, recall | Binary F1 and pair-correct |
| Selective abstention | Central to the method | Not the reported primary operating mode |

## 4. Existing Thesis locked-test result

The frozen hybrid on the natural locked test produced:

| Method | Accepted alerts | Precision among accepted alerts | Positive recall | Coverage |
|---|---:|---:|---:|---:|
| Raw Qwen 1.5B | 23,788 | 2.01% | 91.76% | 99.08% |
| Temperature + conformal | 2,319 | 4.66% | 20.69% | 9.66% |
| Semgrep only | 1,514 | 6.87% | 19.92% | 6.31% |
| Frozen hybrid | 452 | 7.96% | 6.90% | 1.88% |

The hybrid is a selective-review policy. Its contribution is the explicit
precision--coverage trade-off and abstention behavior, not a claim of highest
binary F1 against paired systems.

## 5. Matched exact-test comparator prepared

To obtain a fair model comparison on the Thesis protocol, the next experiment
uses the open-source model:

```text
Qwen/Qwen2.5-Coder-14B-Instruct
```

The Hugging Face revision is pinned to:

```text
aedcc2d42b622764e023cf882b6652e646b95671
```

Because the available free Colab runtime is a Tesla T4 with 15 GB VRAM, the
comparator will use NF4 4-bit bitsandbytes quantization. The comparator will
use:

- the same leakage-controlled 24,008-record test manifest;
- the same code-only YES/NO prompt;
- greedy decoding (`do_sample=False`);
- maximum 16 generated tokens;
- Hugging Face revision `aedcc2d42b622764e023cf882b6652e646b95671`;
- NF4 4-bit quantization with double quantization and float16 computation;
- no calibration fitting, threshold selection, or policy changes using test labels;
- the same explicit treatment of unparseable responses as unresolved;
- ordinary YES precision, recall, F1, and accuracy as a model baseline.

This run is a **matched quantized high-capacity open-model baseline**, not a reproduction
of the multi-agent Phoenix system and not a guaranteed improvement. It tests
whether the observed precision--coverage behavior is partly due to the 1.5B
backbone and whether a larger coder model provides a stronger starting point
for the calibrated selective pipeline.

The quantized run must be labeled separately from an FP16 run. If this model is
later used as the proposed calibrated pipeline, calibration and policy
selection must be refit using the quantized validation predictions before any
test evaluation.

## 6. Run instructions

Upload these files to the same Google Drive folder:

1. `run_qwen_colab.py`
2. `primevul_test.jsonl`
3. `thesis_primevul_leakage_controlled_manifest.json`
4. `primevul_qwen14b_locked_test_colab.ipynb`

Open the notebook in Colab, enable a GPU, and run all cells. The notebook
defaults to `sample_count=0`, meaning every retained test record. For a smoke
test, set it to `3` before the full run.

The notebook writes `qwen14b_4bit_test_results.jsonl`. After the run, evaluate
the JSONL output with:

```text
python evaluate_qwen_matched_baseline.py \
  --input qwen14b_4bit_test_results.jsonl \
  --output qwen14b_4bit_test_baseline_statistics.json \
  --model Qwen/Qwen2.5-Coder-14B-Instruct \
  --revision aedcc2d42b622764e023cf882b6652e646b95671
```

## 7. Current conclusion

The Phoenix reference has been successfully verified, but it does not answer
the Thesis question on the natural locked test. The correct next comparison is
the prepared 14B quantized matched baseline. Until that run completes, no claim
that the larger model improves the Thesis result should be made.

## 8. Source and reproducibility artifacts

- Phoenix paper: <https://arxiv.org/abs/2604.19012>
- Phoenix implementation: <https://github.com/Nothing256/Phoenix>
- Phoenix paired output archive: temporary reference copy used for evaluation,
  outside the Thesis project directory
- Phoenix evaluator: temporary reference copy used for verification
- Matched baseline script: `scripts/evaluate_qwen_matched_baseline.py`
- Matched baseline notebook: `scripts/primevul_qwen14b_locked_test_colab.ipynb`
- Existing Thesis locked-test report: `docs/qwen_test_frozen_policy_report.md`

