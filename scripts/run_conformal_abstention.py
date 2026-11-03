#!/usr/bin/env python3
"""Evaluate split-conformal selective prediction on Qwen validation scores.

This script uses a three-way stratified split of the scored validation output:

1. model-calibration split: fit temperature and Platt parameters;
2. conformal-calibration split: compute nonconformity scores;
3. evaluation split: measure prediction-set coverage and selective precision.

The separation prevents the post-hoc calibrator from being fitted on the same
labels used to construct conformal scores. The final test partition is never
read.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter
from pathlib import Path
from typing import Any

from fit_qwen_calibration import (
    EPS,
    extract_pair_probability,
    fit_platt,
    fit_temperature,
    sigmoid,
)


def load_scored_rows(path: Path) -> tuple[list[dict[str, Any]], list[int]]:
    rows: list[dict[str, Any]] = []
    missing: list[int] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            source = json.loads(line)
            probability = extract_pair_probability(source)
            if probability is None:
                missing.append(int(source["record_number"]))
                continue
            rows.append(
                {
                    "record_number": int(source["record_number"]),
                    "idx": source.get("record", {}).get("idx"),
                    "target": int(source["record"].get("target")),
                    "raw_logit": math.log(probability / (1.0 - probability)),
                    "raw_pair_probability": probability,
                    "parsed_prediction": source.get("prediction"),
                    "input_truncated": source.get("input_truncated"),
                }
            )
    return rows, missing


def three_way_stratified_split(
    rows: list[dict[str, Any]],
    calibration_fraction: float,
    conformal_fraction: float,
    seed: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    groups: dict[int, list[dict[str, Any]]] = {0: [], 1: []}
    for row in rows:
        groups[row["target"]].append(row)
    rng = random.Random(seed)
    model_rows: list[dict[str, Any]] = []
    conformal_rows: list[dict[str, Any]] = []
    evaluation_rows: list[dict[str, Any]] = []
    for label in (0, 1):
        group = list(groups[label])
        rng.shuffle(group)
        model_end = max(1, int(len(group) * calibration_fraction))
        conformal_end = max(model_end + 1, int(len(group) * (calibration_fraction + conformal_fraction)))
        conformal_end = min(conformal_end, len(group) - 1)
        model_rows.extend(group[:model_end])
        conformal_rows.extend(group[model_end:conformal_end])
        evaluation_rows.extend(group[conformal_end:])
    for group in (model_rows, conformal_rows, evaluation_rows):
        group.sort(key=lambda row: row["record_number"])
    return model_rows, conformal_rows, evaluation_rows


def nonconformity(row: dict[str, Any], probability: float) -> float:
    return 1.0 - (probability if row["target"] == 1 else 1.0 - probability)


def p_value(nonconformity_scores: list[float], candidate_score: float) -> float:
    count = sum(score >= candidate_score - EPS for score in nonconformity_scores)
    return (1.0 + count) / (len(nonconformity_scores) + 1.0)


def prediction_set(probability: float, scores: list[float], significance: float) -> tuple[list[int], dict[str, float]]:
    p_value_zero = p_value(scores, probability)
    p_value_one = p_value(scores, 1.0 - probability)
    labels: list[int] = []
    if p_value_zero > significance:
        labels.append(0)
    if p_value_one > significance:
        labels.append(1)
    return labels, {"p_value_0": p_value_zero, "p_value_1": p_value_one}


def evaluate_selective(
    evaluation_rows: list[dict[str, Any]],
    probabilities: list[float],
    conformal_scores: list[float],
    significance: float,
) -> dict[str, Any]:
    sets: list[list[int]] = []
    p_values: list[dict[str, float]] = []
    for probability in probabilities:
        labels, values = prediction_set(probability, conformal_scores, significance)
        sets.append(labels)
        p_values.append(values)

    total = len(evaluation_rows)
    included = sum(row["target"] in labels for row, labels in zip(evaluation_rows, sets))
    accepted = [(row, labels) for row, labels in zip(evaluation_rows, sets) if len(labels) == 1]
    correct_accepted = sum(row["target"] == labels[0] for row, labels in accepted)
    accepted_yes = sum(labels == [1] for _, labels in accepted)
    accepted_yes_correct = sum(row["target"] == 1 and labels == [1] for row, labels in accepted)
    positive_total = sum(row["target"] == 1 for row in evaluation_rows)
    accepted_positive_correct = accepted_yes_correct
    prediction_set_sizes = Counter(str(len(labels)) for labels in sets)
    return {
        "significance": significance,
        "nominal_marginal_coverage_target": 1.0 - significance,
        "evaluation_records": total,
        "prediction_set_coverage": included / max(total, 1),
        "abstention_rate": 1.0 - len(accepted) / max(total, 1),
        "accepted_coverage": len(accepted) / max(total, 1),
        "accepted_precision": correct_accepted / max(len(accepted), 1),
        "accepted_correct": correct_accepted,
        "accepted_records": len(accepted),
        "accepted_yes_records": accepted_yes,
        "accepted_yes_correct": accepted_yes_correct,
        "accepted_yes_precision": accepted_yes_correct / max(accepted_yes, 1),
        "evaluation_positive_records": positive_total,
        "accepted_positive_correct": accepted_positive_correct,
        "accepted_positive_recall": accepted_positive_correct / max(positive_total, 1),
        "accepted_positive_coverage": accepted_positive_correct / max(positive_total, 1),
        "prediction_set_size_counts": dict(sorted(prediction_set_sizes.items())),
        "p_value_min": {
            "label_0": min(values["p_value_0"] for values in p_values),
            "label_1": min(values["p_value_1"] for values in p_values),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate split-conformal selective prediction")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--model-calibration-fraction", type=float, default=0.6)
    parser.add_argument("--conformal-calibration-fraction", type=float, default=0.2)
    parser.add_argument(
        "--significance-levels",
        type=float,
        nargs="+",
        default=[0.01, 0.05, 0.10, 0.20, 0.30, 0.50],
    )
    args = parser.parse_args()
    if args.model_calibration_fraction <= 0 or args.conformal_calibration_fraction <= 0:
        parser.error("split fractions must be positive")
    if args.model_calibration_fraction + args.conformal_calibration_fraction >= 1.0:
        parser.error("model and conformal fractions must leave evaluation records")

    rows, missing_records = load_scored_rows(args.input)
    model_rows, conformal_rows, evaluation_rows = three_way_stratified_split(
        rows,
        args.model_calibration_fraction,
        args.conformal_calibration_fraction,
        args.seed,
    )
    model_scores = [row["raw_logit"] for row in model_rows]
    model_labels = [row["target"] for row in model_rows]
    temperature = fit_temperature(model_scores, model_labels)
    platt_a, platt_b = fit_platt(model_scores, model_labels)

    method_outputs: dict[str, Any] = {}
    for method in ("temperature", "platt"):
        def calibrate(row: dict[str, Any]) -> float:
            if method == "temperature":
                return sigmoid(row["raw_logit"] / temperature)
            return sigmoid(platt_a * row["raw_logit"] + platt_b)

        conformal_probabilities = [calibrate(row) for row in conformal_rows]
        evaluation_probabilities = [calibrate(row) for row in evaluation_rows]
        conformal_scores = [nonconformity(row, probability) for row, probability in zip(conformal_rows, conformal_probabilities)]
        summaries = [
            evaluate_selective(evaluation_rows, evaluation_probabilities, conformal_scores, significance)
            for significance in args.significance_levels
        ]
        evaluation_records: list[dict[str, Any]] = []
        for row, probability in zip(evaluation_rows, evaluation_probabilities):
            prediction_sets: dict[str, list[int]] = {}
            p_values: dict[str, dict[str, float]] = {}
            for significance in args.significance_levels:
                labels, values = prediction_set(probability, conformal_scores, significance)
                key = str(significance)
                prediction_sets[key] = labels
                p_values[key] = values
            evaluation_records.append(
                {
                    "record_number": row["record_number"],
                    "idx": row["idx"],
                    "target": row["target"],
                    "probability": probability,
                    "prediction_sets": prediction_sets,
                    "p_values": p_values,
                }
            )
        method_outputs[method] = {
            "conformal_score_summary": {
                "count": len(conformal_scores),
                "mean": sum(conformal_scores) / max(len(conformal_scores), 1),
                "min": min(conformal_scores),
                "max": max(conformal_scores),
            },
            "conformal_scores": conformal_scores,
            "selective_metrics": summaries,
            "evaluation_records": evaluation_records,
        }

    output = {
        "status": "complete",
        "method": {
            "input": str(args.input),
            "score_definition": "p(YES)/(p(YES)+p(NO)) from first-token top-five probabilities",
            "split_design": "three-way stratified validation-only split",
            "model_calibration_fraction": args.model_calibration_fraction,
            "conformal_calibration_fraction": args.conformal_calibration_fraction,
            "evaluation_fraction": 1.0 - args.model_calibration_fraction - args.conformal_calibration_fraction,
            "seed": args.seed,
            "conformal_nonconformity": "1 - calibrated probability assigned to the candidate label",
            "prediction_set_rule": "include label when conformal p-value > significance; accept only singleton sets; otherwise abstain",
            "coverage_claim": "marginal coverage under exchangeability for the split-conformal prediction set, subject to the stated validation-only split and score construction",
            "final_test_used": False,
        },
        "counts": {
            "input_records": len(rows) + len(missing_records),
            "scored_records": len(rows),
            "missing_score_records": len(missing_records),
            "missing_score_record_numbers": missing_records,
            "model_calibration_records": len(model_rows),
            "conformal_calibration_records": len(conformal_rows),
            "evaluation_records": len(evaluation_rows),
            "model_calibration_target_counts": dict(sorted(Counter(row["target"] for row in model_rows).items())),
            "conformal_calibration_target_counts": dict(sorted(Counter(row["target"] for row in conformal_rows).items())),
            "evaluation_target_counts": dict(sorted(Counter(row["target"] for row in evaluation_rows).items())),
        },
        "calibration_parameters": {
            "temperature": temperature,
            "platt_a": platt_a,
            "platt_b": platt_b,
        },
        "methods": method_outputs,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "complete", "output": str(args.output), "counts": output["counts"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

