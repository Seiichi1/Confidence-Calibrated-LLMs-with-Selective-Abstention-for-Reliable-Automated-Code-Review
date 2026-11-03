#!/usr/bin/env python3
"""Bootstrap a direct comparison of the frozen and higher-recall policies.

This evaluator is for the project-held-out candidate. It does not fit a model,
calibrator, conformal threshold, or operating policy. It compares the already
selected alpha=0.10 and alpha=0.50 decisions using record-level and
whole-project clustered bootstrap resampling.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from random import Random
from typing import Any


METRICS = ("coverage", "abstention_rate", "accepted_positive_precision", "positive_recall")


def percentile(values: list[float | None], fraction: float) -> float | None:
    finite = sorted(value for value in values if value is not None)
    if not finite:
        return None
    position = (len(finite) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(finite) - 1)
    weight = position - lower
    return finite[lower] * (1.0 - weight) + finite[upper] * weight


def interval(values: list[float | None], iterations: int) -> dict[str, Any]:
    return {
        "lower_95": percentile(values, 0.025),
        "upper_95": percentile(values, 0.975),
        "bootstrap_iterations": iterations,
    }


def metrics(accepted: int, true_positive: int, total: int, positives: int) -> dict[str, float | None]:
    coverage = accepted / max(total, 1)
    return {
        "coverage": coverage,
        "abstention_rate": 1.0 - coverage,
        "accepted_positive_precision": true_positive / accepted if accepted else None,
        "positive_recall": true_positive / positives if positives else None,
    }


def counts_for_indices(
    indices: list[int], targets: list[int], accepted: dict[str, list[bool]]
) -> dict[str, dict[str, int]]:
    output: dict[str, dict[str, int]] = {}
    for name, flags in accepted.items():
        accepted_count = sum(flags[index] for index in indices)
        true_positive = sum(flags[index] and targets[index] == 1 for index in indices)
        output[name] = {
            "accepted": accepted_count,
            "true_positive": true_positive,
            "false_positive": accepted_count - true_positive,
        }
    return output


def bootstrap_record_level(
    accepted: dict[str, list[bool]],
    targets: list[int],
    rng: Random,
    iterations: int,
) -> tuple[dict[str, dict[str, dict[str, Any]]], dict[str, dict[str, dict[str, Any]]]]:
    names = list(accepted)
    bits = {name: 1 << index for index, name in enumerate(names)}
    masks = [sum(bits[name] for name in names if accepted[name][i]) for i in range(len(targets))]
    buckets = {mask: [[0, 0] for _ in range(2)] for mask in range(1 << len(names))}
    values = {name: {metric: [] for metric in METRICS} for name in names}
    comparisons = {
        "candidate_alpha_0_50_minus_frozen_alpha_0_10": {metric: [] for metric in METRICS},
        "frozen_alpha_0_10_minus_raw_qwen": {metric: [] for metric in METRICS},
        "candidate_alpha_0_50_minus_raw_qwen": {metric: [] for metric in METRICS},
    }
    population = list(range(len(targets)))
    for _ in range(iterations):
        current = {mask: [[0, 0] for _ in range(2)] for mask in buckets}
        for index in rng.choices(population, k=len(targets)):
            current[masks[index]][targets[index]][0] += 1
        positive_total = sum(bucket[1][0] for bucket in current.values())
        estimates: dict[str, dict[str, float | None]] = {}
        for name in names:
            bit = bits[name]
            accepted_count = sum(
                current[mask][0][0] + current[mask][1][0]
                for mask in current
                if mask & bit
            )
            true_positive = sum(
                current[mask][1][0] for mask in current if mask & bit
            )
            estimates[name] = metrics(accepted_count, true_positive, len(targets), positive_total)
            for metric in METRICS:
                values[name][metric].append(estimates[name][metric])
        for comparison, left_name, right_name in (
            ("candidate_alpha_0_50_minus_frozen_alpha_0_10", "candidate_alpha_0_50", "frozen_alpha_0_10"),
            ("frozen_alpha_0_10_minus_raw_qwen", "frozen_alpha_0_10", "raw_qwen"),
            ("candidate_alpha_0_50_minus_raw_qwen", "candidate_alpha_0_50", "raw_qwen"),
        ):
            for metric in METRICS:
                left = estimates[left_name][metric]
                right = estimates[right_name][metric]
                comparisons[comparison][metric].append(
                    left - right if left is not None and right is not None else None
                )
    return (
        {name: {metric: interval(samples, iterations) for metric, samples in metric_map.items()} for name, metric_map in values.items()},
        {name: {metric: interval(samples, iterations) for metric, samples in metric_map.items()} for name, metric_map in comparisons.items()},
    )


def bootstrap_project_level(
    project_stats: dict[str, dict[str, Any]],
    rng: Random,
    iterations: int,
) -> tuple[dict[str, dict[str, dict[str, Any]]], dict[str, dict[str, dict[str, Any]]]]:
    names = ("raw_qwen", "frozen_alpha_0_10", "candidate_alpha_0_50")
    projects = list(project_stats)
    values = {name: {metric: [] for metric in METRICS} for name in names}
    comparisons = {
        "candidate_alpha_0_50_minus_frozen_alpha_0_10": {metric: [] for metric in METRICS},
        "frozen_alpha_0_10_minus_raw_qwen": {metric: [] for metric in METRICS},
        "candidate_alpha_0_50_minus_raw_qwen": {metric: [] for metric in METRICS},
    }
    for _ in range(iterations):
        totals = {name: {"accepted": 0, "true_positive": 0} for name in names}
        total = positives = 0
        for project in rng.choices(projects, k=len(projects)):
            stats = project_stats[project]
            total += stats["records"]
            positives += stats["positive_records"]
            for name in names:
                totals[name]["accepted"] += stats[name]["accepted"]
                totals[name]["true_positive"] += stats[name]["true_positive"]
        estimates = {
            name: metrics(totals[name]["accepted"], totals[name]["true_positive"], total, positives)
            for name in names
        }
        for name in names:
            for metric in METRICS:
                values[name][metric].append(estimates[name][metric])
        for comparison, left_name, right_name in (
            ("candidate_alpha_0_50_minus_frozen_alpha_0_10", "candidate_alpha_0_50", "frozen_alpha_0_10"),
            ("frozen_alpha_0_10_minus_raw_qwen", "frozen_alpha_0_10", "raw_qwen"),
            ("candidate_alpha_0_50_minus_raw_qwen", "candidate_alpha_0_50", "raw_qwen"),
        ):
            for metric in METRICS:
                left = estimates[left_name][metric]
                right = estimates[right_name][metric]
                comparisons[comparison][metric].append(
                    left - right if left is not None and right is not None else None
                )
    return (
        {name: {metric: interval(samples, iterations) for metric, samples in metric_map.items()} for name, metric_map in values.items()},
        {name: {metric: interval(samples, iterations) for metric, samples in metric_map.items()} for name, metric_map in comparisons.items()},
    )


def load_rows(path: Path) -> dict[int, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8")) if path.suffix == ".json" else None
    if data is not None:
        return {int(row["record_number"]): row for row in data["rows"]}
    with path.open("r", encoding="utf-8") as handle:
        return {int((row := json.loads(line))["record_number"]): row for line in handle}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qwen-results", type=Path, required=True)
    parser.add_argument("--frozen-policy-results", type=Path, required=True)
    parser.add_argument("--candidate-policy-results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20261029)
    args = parser.parse_args()
    if args.iterations <= 0:
        parser.error("iterations must be positive")

    qwen = load_rows(args.qwen_results)
    frozen = load_rows(args.frozen_policy_results)
    candidate = load_rows(args.candidate_policy_results)
    record_numbers = sorted(qwen)
    if set(frozen) != set(qwen) or set(candidate) != set(qwen):
        raise SystemExit("Qwen and policy record-number sets do not match")

    targets: list[int] = []
    projects: list[str] = []
    accepted: dict[str, list[bool]] = {
        "raw_qwen": [],
        "frozen_alpha_0_10": [],
        "candidate_alpha_0_50": [],
    }
    for number in record_numbers:
        source = qwen[number]
        targets.append(int(source["record"].get("target")))
        projects.append(str(source["record"].get("project") or "__MISSING_PROJECT__"))
        accepted["raw_qwen"].append(source.get("prediction") == "YES")
        accepted["frozen_alpha_0_10"].append(frozen[number].get("decision") == "YES")
        accepted["candidate_alpha_0_50"].append(candidate[number].get("decision") == "YES")

    total = len(targets)
    positives = sum(targets)
    point = {
        name: {
            **metrics(sum(flags), sum(flag and target == 1 for flag, target in zip(flags, targets)), total, positives),
            "records": total,
            "accepted_records": sum(flags),
            "abstained_records": total - sum(flags),
            "true_positive": sum(flag and target == 1 for flag, target in zip(flags, targets)),
            "false_positive": sum(flag and target == 0 for flag, target in zip(flags, targets)),
            "positive_records": positives,
        }
        for name, flags in accepted.items()
    }

    project_stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "records": 0,
            "positive_records": 0,
            **{name: {"accepted": 0, "true_positive": 0} for name in accepted},
        }
    )
    for index, project in enumerate(projects):
        stats = project_stats[project]
        stats["records"] += 1
        stats["positive_records"] += targets[index]
        for name, flags in accepted.items():
            stats[name]["accepted"] += int(flags[index])
            stats[name]["true_positive"] += int(flags[index] and targets[index] == 1)

    record_intervals, record_comparisons = bootstrap_record_level(
        accepted, targets, Random(args.seed), args.iterations
    )
    project_intervals, project_comparisons = bootstrap_project_level(
        project_stats, Random(args.seed), args.iterations
    )
    output = {
        "status": "complete",
        "method": {
            "unit_record": "record-level paired bootstrap resampling with replacement",
            "unit_project": "whole-project clustered bootstrap resampling with replacement",
            "iterations": args.iterations,
            "seed_record": args.seed,
            "seed_project": args.seed,
            "test_labels_used_for_fitting_or_selection": False,
            "policy_parameters_changed": False,
            "comparison": "candidate alpha 0.50 versus frozen alpha 0.10",
        },
        "counts": {"records": total, "positive_records": positives, "projects": len(project_stats)},
        "point_estimates": point,
        "record_bootstrap_95_percent_intervals": record_intervals,
        "project_clustered_bootstrap_95_percent_intervals": project_intervals,
        "record_paired_comparisons": record_comparisons,
        "project_paired_comparisons": project_comparisons,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "complete", "output": str(args.output), "counts": output["counts"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

