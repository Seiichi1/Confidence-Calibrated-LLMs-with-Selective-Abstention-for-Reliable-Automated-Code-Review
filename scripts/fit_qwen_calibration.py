#!/usr/bin/env python3
"""Fit validation-only temperature and Platt calibration for Qwen outputs.

The input JSONL is the completed LLM baseline output.  The raw top-five
probabilities contain the YES and NO first-token probabilities for nearly all
records.  Their normalized ratio is equivalent to a binary first-token score
because the common vocabulary softmax denominator cancels:

    p_yes_pair = p(YES) / (p(YES) + p(NO))

Records missing either token from the retained top-five list are reported but
excluded from calibration fitting and calibration evaluation.  The final test
partition is never read by this script.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter
from pathlib import Path
from typing import Any


EPS = 1e-12


def sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-min(value, 700.0))
        return 1.0 / (1.0 + z)
    z = math.exp(max(value, -700.0))
    return z / (1.0 + z)


def clamp_probability(value: float) -> float:
    return min(max(value, EPS), 1.0 - EPS)


def nll(probabilities: list[float], labels: list[int]) -> float:
    total = 0.0
    for probability, label in zip(probabilities, labels):
        probability = clamp_probability(probability)
        total -= label * math.log(probability) + (1 - label) * math.log(1 - probability)
    return total / max(len(labels), 1)


def extract_pair_probability(row: dict[str, Any]) -> float | None:
    top_tokens = {item.get("token"): item.get("probability") for item in row.get("first_token_top5", [])}
    yes_probability = top_tokens.get("YES")
    no_probability = top_tokens.get("NO")
    if not isinstance(yes_probability, (int, float)) or not isinstance(no_probability, (int, float)):
        return None
    denominator = float(yes_probability) + float(no_probability)
    if denominator <= 0:
        return None
    return clamp_probability(float(yes_probability) / denominator)


def metrics(rows: list[dict[str, Any]], probabilities: list[float]) -> dict[str, Any]:
    labels = [int(row["target"]) for row in rows]
    predictions = [1 if probability >= 0.5 else 0 for probability in probabilities]
    tp = sum(label == 1 and prediction == 1 for label, prediction in zip(labels, predictions))
    tn = sum(label == 0 and prediction == 0 for label, prediction in zip(labels, predictions))
    fp = sum(label == 0 and prediction == 1 for label, prediction in zip(labels, predictions))
    fn = sum(label == 1 and prediction == 0 for label, prediction in zip(labels, predictions))
    total = len(labels)
    brier = sum((probability - label) ** 2 for probability, label in zip(probabilities, labels)) / max(total, 1)

    bins: list[list[int]] = [[] for _ in range(10)]
    for index, probability in enumerate(probabilities):
        bin_index = min(9, int(probability * 10))
        bins[bin_index].append(index)
    ece = 0.0
    bin_details = []
    for bin_index, indices in enumerate(bins):
        if not indices:
            continue
        mean_probability = sum(probabilities[index] for index in indices) / len(indices)
        mean_label = sum(labels[index] for index in indices) / len(indices)
        ece += len(indices) / max(total, 1) * abs(mean_probability - mean_label)
        bin_details.append(
            {
                "bin": bin_index,
                "count": len(indices),
                "mean_probability": mean_probability,
                "empirical_positive_rate": mean_label,
            }
        )

    return {
        "records": total,
        "positive_records": sum(labels),
        "negative_records": total - sum(labels),
        "accuracy": (tp + tn) / max(total, 1),
        "precision_yes": tp / max(tp + fp, 1),
        "recall_yes": tp / max(tp + fn, 1),
        "brier_score": brier,
        "log_loss": nll(probabilities, labels),
        "ece_10_equal_width_bins": ece,
        "coverage": 1.0,
        "confusion": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
        "reliability_bins": bin_details,
    }


def fit_temperature(scores: list[float], labels: list[int]) -> float:
    """Minimize NLL for sigmoid(score / temperature) with a bounded search."""
    def objective(log_temperature: float) -> float:
        temperature = math.exp(log_temperature)
        probabilities = [sigmoid(score / temperature) for score in scores]
        return nll(probabilities, labels)

    grid = [(-6.0 + 12.0 * index / 240.0, objective(-6.0 + 12.0 * index / 240.0)) for index in range(241)]
    best_log_temperature, best_value = min(grid, key=lambda item: item[1])
    step = 12.0 / 240.0
    for _ in range(8):
        candidates = [
            (best_log_temperature - step, objective(best_log_temperature - step)),
            (best_log_temperature, best_value),
            (best_log_temperature + step, objective(best_log_temperature + step)),
        ]
        best_log_temperature, best_value = min(candidates, key=lambda item: item[1])
        step /= 2.0
    return math.exp(best_log_temperature)


def fit_platt(scores: list[float], labels: list[int]) -> tuple[float, float]:
    """Fit sigmoid(a * score + b) using damped Newton updates."""
    a = 1.0
    b = 0.0
    for _ in range(100):
        probabilities = [sigmoid(a * score + b) for score in scores]
        gradient_a = sum((probability - label) * score for probability, label, score in zip(probabilities, labels, scores))
        gradient_b = sum(probability - label for probability, label in zip(probabilities, labels))
        weights = [max(probability * (1.0 - probability), EPS) for probability in probabilities]
        h_aa = sum(weight * score * score for weight, score in zip(weights, scores)) + EPS
        h_ab = sum(weight * score for weight, score in zip(weights, scores))
        h_bb = sum(weights) + EPS
        determinant = h_aa * h_bb - h_ab * h_ab
        if abs(determinant) < EPS:
            break
        delta_a = (h_bb * gradient_a - h_ab * gradient_b) / determinant
        delta_b = (-h_ab * gradient_a + h_aa * gradient_b) / determinant
        current_loss = nll(probabilities, labels)
        step = 1.0
        while step > 1e-7:
            candidate_a = a - step * delta_a
            candidate_b = b - step * delta_b
            candidate_probabilities = [sigmoid(candidate_a * score + candidate_b) for score in scores]
            if nll(candidate_probabilities, labels) <= current_loss:
                a, b = candidate_a, candidate_b
                break
            step /= 2.0
        if max(abs(step * delta_a), abs(step * delta_b)) < 1e-8:
            break
    return a, b


def calibrated_probabilities(rows: list[dict[str, Any]], temperature: float, platt_a: float, platt_b: float) -> dict[str, list[float]]:
    scores = [row["raw_logit"] for row in rows]
    return {
        "raw_pair": [sigmoid(score) for score in scores],
        "temperature": [sigmoid(score / temperature) for score in scores],
        "platt": [sigmoid(platt_a * score + platt_b) for score in scores],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fit validation-only Qwen confidence calibration")
    parser.add_argument("--input", type=Path, required=True, help="Clean baseline JSONL output")
    parser.add_argument("--output", type=Path, required=True, help="Calibration artifact JSON")
    parser.add_argument("--calibration-fraction", type=float, default=0.8)
    parser.add_argument("--seed", type=int, default=12345)
    args = parser.parse_args()
    if not 0.5 <= args.calibration_fraction < 1.0:
        parser.error("--calibration-fraction must be at least 0.5 and below 1.0")

    rows: list[dict[str, Any]] = []
    missing_score_record_numbers: list[int] = []
    with args.input.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            probability = extract_pair_probability(row)
            if probability is None:
                missing_score_record_numbers.append(int(row["record_number"]))
                continue
            row = {
                "record_number": int(row["record_number"]),
                "idx": row.get("record", {}).get("idx"),
                "target": int(row["record"].get("target")),
                "parsed_prediction": row.get("prediction"),
                "raw_pair_probability": probability,
                "raw_logit": math.log(probability / (1.0 - probability)),
                "input_tokens": row.get("input_tokens"),
                "input_truncated": row.get("input_truncated"),
            }
            rows.append(row)

    groups: dict[int, list[dict[str, Any]]] = {0: [], 1: []}
    for row in rows:
        groups[row["target"]].append(row)
    rng = random.Random(args.seed)
    calibration_rows: list[dict[str, Any]] = []
    evaluation_rows: list[dict[str, Any]] = []
    for label in (0, 1):
        group = list(groups[label])
        rng.shuffle(group)
        split_index = max(1, min(len(group) - 1, int(len(group) * args.calibration_fraction)))
        calibration_rows.extend(group[:split_index])
        evaluation_rows.extend(group[split_index:])
    calibration_rows.sort(key=lambda row: row["record_number"])
    evaluation_rows.sort(key=lambda row: row["record_number"])

    calibration_scores = [row["raw_logit"] for row in calibration_rows]
    calibration_labels = [row["target"] for row in calibration_rows]
    temperature = fit_temperature(calibration_scores, calibration_labels)
    platt_a, platt_b = fit_platt(calibration_scores, calibration_labels)

    model_parameters = {
        "temperature": temperature,
        "platt_a": platt_a,
        "platt_b": platt_b,
    }
    calibration_record_numbers = {row["record_number"] for row in calibration_rows}
    split_metrics: dict[str, Any] = {}
    for split_name, split_rows in (("calibration", calibration_rows), ("heldout_validation", evaluation_rows), ("all_scored", rows)):
        scores = calibrated_probabilities(split_rows, temperature, platt_a, platt_b)
        split_metrics[split_name] = {
            method: metrics(split_rows, probabilities)
            for method, probabilities in scores.items()
        }

    output = {
        "status": "complete",
        "method": {
            "input": str(args.input),
            "score_definition": "p(YES)/(p(YES)+p(NO)) from first-token top-five probabilities",
            "logit_definition": "log(p_pair/(1-p_pair))",
            "calibration_fraction": args.calibration_fraction,
            "split": "deterministic stratified validation-only split",
            "seed": args.seed,
            "temperature_objective": "negative log likelihood",
            "platt_objective": "negative log likelihood",
            "final_test_used": False,
        },
        "counts": {
            "input_records": len(rows) + len(missing_score_record_numbers),
            "scored_records": len(rows),
            "missing_score_records": len(missing_score_record_numbers),
            "calibration_records": len(calibration_rows),
            "heldout_validation_records": len(evaluation_rows),
            "scored_target_counts": dict(sorted(Counter(row["target"] for row in rows).items())),
            "missing_score_record_numbers": missing_score_record_numbers,
        },
        "parameters": model_parameters,
        "metrics": split_metrics,
        "scored_records": [
            {
                **{key: value for key, value in row.items() if key != "raw_logit"},
                "split": "calibration" if row["record_number"] in calibration_record_numbers else "heldout_validation",
                "temperature_probability": sigmoid(row["raw_logit"] / temperature),
                "platt_probability": sigmoid(platt_a * row["raw_logit"] + platt_b),
            }
            for row in rows
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "complete", "output": str(args.output), "parameters": model_parameters}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

