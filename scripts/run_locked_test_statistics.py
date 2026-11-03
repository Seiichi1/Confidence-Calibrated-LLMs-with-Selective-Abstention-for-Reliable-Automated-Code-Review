#!/usr/bin/env python3
"""Compute locked-test paired ablations and record-level bootstrap intervals.

This evaluator uses already-produced test artifacts only for evaluation. It
does not fit calibration, select thresholds, or alter the frozen policy. The
positive-alert comparison treats a record as accepted only when the method
returns an affirmative vulnerability alert; all other records are abstentions.
"""

from __future__ import annotations

import argparse
import json
from random import Random
from pathlib import Path
from typing import Any

def metric_summary(accepted: list[bool], targets: list[int]) -> dict[str, Any]:
    accepted_count = sum(accepted)
    true_positive = sum(flag and target == 1 for flag, target in zip(accepted, targets))
    false_positive = sum(flag and target == 0 for flag, target in zip(accepted, targets))
    positive_total = sum(target == 1 for target in targets)
    total = len(targets)
    return {
        "records": total,
        "accepted_records": accepted_count,
        "abstained_records": total - accepted_count,
        "coverage": accepted_count / max(total, 1),
        "abstention_rate": (total - accepted_count) / max(total, 1),
        "accepted_positive_precision": true_positive / max(accepted_count, 1),
        "positive_recall": true_positive / max(positive_total, 1),
        "true_positive": true_positive,
        "false_positive": false_positive,
        "positive_records": positive_total,
    }


def percentile(values: list[float], fraction: float) -> float | None:
    finite = sorted(value for value in values if value is not None)
    if not finite:
        return None
    position = (len(finite) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(finite) - 1)
    weight = position - lower
    return finite[lower] * (1.0 - weight) + finite[upper] * weight


def interval(values: list[float | None], iterations: int) -> dict[str, float | int | None]:
    return {
        "lower_95": percentile(values, 0.025),
        "upper_95": percentile(values, 0.975),
        "bootstrap_iterations": iterations,
    }


def bootstrap_all(
    methods: dict[str, list[bool]],
    targets: list[int],
    rng: Random,
    iterations: int,
) -> tuple[dict[str, dict[str, dict[str, float | int | None]]], dict[str, dict[str, dict[str, float | int | None]]]]:
    metric_names = ("coverage", "abstention_rate", "accepted_positive_precision", "positive_recall")
    values = {name: {metric: [] for metric in metric_names} for name in methods}
    paired_values = {
        f"frozen_hybrid_minus_{name}": {metric: [] for metric in metric_names}
        for name in methods
        if name != "frozen_hybrid"
    }
    population = list(range(len(targets)))
    method_names = list(methods)
    method_bits = {name: 1 << index for index, name in enumerate(method_names)}
    masks = [
        sum(method_bits[name] for name in method_names if methods[name][index])
        for index in range(len(targets))
    ]
    for _ in range(iterations):
        buckets = [[0, 0] for _ in range(1 << len(method_names))]
        for index in rng.choices(population, k=len(targets)):
            buckets[masks[index]][targets[index]] += 1
        positive_total = sum(bucket[1] for bucket in buckets)
        counts = {}
        for name in method_names:
            bit = method_bits[name]
            accepted_count = sum(
                bucket[0] + bucket[1]
                for mask, bucket in enumerate(buckets)
                if mask & bit
            )
            true_positive = sum(
                bucket[1]
                for mask, bucket in enumerate(buckets)
                if mask & bit
            )
            counts[name] = [accepted_count, true_positive]
        metrics: dict[str, dict[str, float | None]] = {}
        for name, (accepted_count, true_positive) in counts.items():
            precision = true_positive / accepted_count if accepted_count else None
            recall = true_positive / positive_total if positive_total else None
            metrics[name] = {
                "coverage": accepted_count / len(targets),
                "abstention_rate": 1.0 - accepted_count / len(targets),
                "accepted_positive_precision": precision,
                "positive_recall": recall,
            }
            for metric in metric_names:
                values[name][metric].append(metrics[name][metric])
        for comparator in paired_values:
            comparator_name = comparator.removeprefix("frozen_hybrid_minus_")
            for metric in metric_names:
                left = metrics["frozen_hybrid"][metric]
                right = metrics[comparator_name][metric]
                paired_values[comparator][metric].append(
                    left - right if left is not None and right is not None else None
                )
    intervals = {
        name: {metric: interval(samples, iterations) for metric, samples in metrics.items()}
        for name, metrics in values.items()
    }
    paired_intervals = {
        name: {metric: interval(samples, iterations) for metric, samples in metrics.items()}
        for name, metrics in paired_values.items()
    }
    return intervals, paired_intervals


def load_inputs(
    qwen_path: Path, static_path: Path, policy_path: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    qwen_rows = [json.loads(line) for line in qwen_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    static = json.loads(static_path.read_text(encoding="utf-8"))
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    static_rows = {int(row["record_number"]): row for row in static["rows"]}
    policy_rows = {int(row["record_number"]): row for row in policy["rows"]}
    qwen_numbers = {int(row["record_number"]) for row in qwen_rows}
    if qwen_numbers != set(static_rows) or qwen_numbers != set(policy_rows):
        raise SystemExit("Qwen, Semgrep, and frozen-policy records are not aligned")
    qwen_rows.sort(key=lambda row: int(row["record_number"]))
    return qwen_rows, [static_rows[int(row["record_number"])] for row in qwen_rows], [policy_rows[int(row["record_number"])] for row in qwen_rows]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qwen-results", type=Path, required=True)
    parser.add_argument("--static-results", type=Path, required=True)
    parser.add_argument("--policy-results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20261027)
    args = parser.parse_args()
    if args.iterations <= 0:
        parser.error("iterations must be positive")

    qwen_rows, static_rows, policy_rows = load_inputs(
        args.qwen_results, args.static_results, args.policy_results
    )
    targets = [int(row["record"].get("target")) for row in qwen_rows]
    raw = [row.get("prediction") == "YES" for row in qwen_rows]
    conformal = [row.get("prediction_set") == [1] for row in policy_rows]
    static = [row.get("static_label") == "YES" for row in static_rows]
    frozen = [row.get("decision") == "YES" for row in policy_rows]
    methods = {"raw_qwen": raw, "temperature_conformal_only": conformal, "semgrep_only": static, "frozen_hybrid": frozen}
    rng = Random(args.seed)
    point_estimates = {name: metric_summary(values, targets) for name, values in methods.items()}
    intervals, paired_intervals = bootstrap_all(methods, targets, rng, args.iterations)
    paired: dict[str, Any] = {}
    for comparator in ("raw_qwen", "temperature_conformal_only", "semgrep_only"):
        left = point_estimates["frozen_hybrid"]
        right = point_estimates[comparator]
        paired[f"frozen_hybrid_minus_{comparator}"] = {
            "point_difference": {
                metric: left[metric] - right[metric]
                for metric in ("coverage", "abstention_rate", "accepted_positive_precision", "positive_recall")
            },
            "paired_bootstrap_95_percent_interval": paired_intervals[
                f"frozen_hybrid_minus_{comparator}"
            ],
        }
    output = {
        "status": "complete",
        "method": {
            "unit": "record-level paired bootstrap resampling with replacement",
            "bootstrap_iterations": args.iterations,
            "seed": args.seed,
            "positive_alert_definition": "accepted YES only; all other outcomes are abstentions",
            "test_labels_used_for_fitting_or_selection": False,
            "policy_parameters_changed": False,
        },
        "counts": {
            "records": len(targets),
            "positive_records": sum(targets),
            "negative_records": sum(target == 0 for target in targets),
        },
        "point_estimates": point_estimates,
        "bootstrap_intervals": intervals,
        "paired_comparisons": paired,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": output["status"], "output": str(args.output), "counts": output["counts"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

