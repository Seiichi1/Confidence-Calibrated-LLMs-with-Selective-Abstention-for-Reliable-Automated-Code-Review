#!/usr/bin/env python3
"""Project-clustered sensitivity intervals for the locked-test ablations.

Whole projects, rather than individual records, are resampled with
replacement. This is an uncertainty sensitivity analysis only: it does not
create a new split, refit calibration, or change the frozen policy.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from random import Random
from typing import Any


METRICS = ("coverage", "abstention_rate", "accepted_positive_precision", "positive_recall")
METHODS = ("raw_qwen", "temperature_conformal_only", "semgrep_only", "frozen_hybrid")


def percentile(values: list[float | None], fraction: float) -> float | None:
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


def metrics_from_totals(totals: dict[str, int], total: int, positives: int) -> dict[str, float | None]:
    accepted = totals["accepted"]
    true_positive = totals["true_positive"]
    return {
        "coverage": accepted / max(total, 1),
        "abstention_rate": 1.0 - accepted / max(total, 1),
        "accepted_positive_precision": true_positive / accepted if accepted else None,
        "positive_recall": true_positive / positives if positives else None,
    }


def point_summary(cluster_stats: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    totals = {
        method: {"accepted": 0, "true_positive": 0, "false_positive": 0}
        for method in METHODS
    }
    total = positives = 0
    for stats in cluster_stats.values():
        total += stats["records"]
        positives += stats["positive_records"]
        for method in METHODS:
            for key in totals[method]:
                totals[method][key] += stats[method][key]
    output: dict[str, dict[str, Any]] = {}
    for method in METHODS:
        values = metrics_from_totals(totals[method], total, positives)
        output[method] = {
            "records": total,
            "accepted_records": totals[method]["accepted"],
            "abstained_records": total - totals[method]["accepted"],
            "true_positive": totals[method]["true_positive"],
            "false_positive": totals[method]["false_positive"],
            "positive_records": positives,
            **values,
        }
    return output


def clustered_bootstrap(
    cluster_stats: dict[str, dict[str, Any]],
    rng: Random,
    iterations: int,
) -> tuple[dict[str, dict[str, dict[str, float | int | None]]], dict[str, dict[str, dict[str, float | int | None]]]]:
    project_names = list(cluster_stats)
    values = {method: {metric: [] for metric in METRICS} for method in METHODS}
    paired_values = {
        f"frozen_hybrid_minus_{method}": {metric: [] for metric in METRICS}
        for method in METHODS
        if method != "frozen_hybrid"
    }
    for _ in range(iterations):
        totals = {
            method: {"accepted": 0, "true_positive": 0, "false_positive": 0}
            for method in METHODS
        }
        total = positives = 0
        for project in rng.choices(project_names, k=len(project_names)):
            stats = cluster_stats[project]
            total += stats["records"]
            positives += stats["positive_records"]
            for method in METHODS:
                for key in totals[method]:
                    totals[method][key] += stats[method][key]
        current = {
            method: metrics_from_totals(totals[method], total, positives)
            for method in METHODS
        }
        for method in METHODS:
            for metric in METRICS:
                values[method][metric].append(current[method][metric])
        for comparator in paired_values:
            comparator_method = comparator.removeprefix("frozen_hybrid_minus_")
            for metric in METRICS:
                left = current["frozen_hybrid"][metric]
                right = current[comparator_method][metric]
                paired_values[comparator][metric].append(
                    left - right if left is not None and right is not None else None
                )
    intervals = {
        method: {metric: interval(samples, iterations) for metric, samples in metric_map.items()}
        for method, metric_map in values.items()
    }
    paired_intervals = {
        comparison: {metric: interval(samples, iterations) for metric, samples in metric_map.items()}
        for comparison, metric_map in paired_values.items()
    }
    return intervals, paired_intervals


def load_cluster_stats(qwen_path: Path, static_path: Path, policy_path: Path) -> dict[str, dict[str, Any]]:
    qwen_rows = [json.loads(line) for line in qwen_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    static = json.loads(static_path.read_text(encoding="utf-8"))
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    static_rows = {int(row["record_number"]): row for row in static["rows"]}
    policy_rows = {int(row["record_number"]): row for row in policy["rows"]}
    numbers = {int(row["record_number"]) for row in qwen_rows}
    if numbers != set(static_rows) or numbers != set(policy_rows):
        raise SystemExit("Qwen, Semgrep, and frozen-policy records are not aligned")
    clusters: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "records": 0,
            "positive_records": 0,
            **{method: {"accepted": 0, "true_positive": 0, "false_positive": 0} for method in METHODS},
        }
    )
    for source in qwen_rows:
        number = int(source["record_number"])
        target = int(source["record"].get("target"))
        project = str(source["record"].get("project") or "__MISSING_PROJECT__")
        static_row = static_rows[number]
        policy_row = policy_rows[number]
        accepted = {
            "raw_qwen": source.get("prediction") == "YES",
            "temperature_conformal_only": policy_row.get("prediction_set") == [1],
            "semgrep_only": static_row.get("static_label") == "YES",
            "frozen_hybrid": policy_row.get("decision") == "YES",
        }
        stats = clusters[project]
        stats["records"] += 1
        stats["positive_records"] += target == 1
        for method, flag in accepted.items():
            stats[method]["accepted"] += flag
            stats[method]["true_positive"] += flag and target == 1
            stats[method]["false_positive"] += flag and target == 0
    return dict(clusters)


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

    clusters = load_cluster_stats(args.qwen_results, args.static_results, args.policy_results)
    intervals, paired_intervals = clustered_bootstrap(clusters, Random(args.seed), args.iterations)
    point = point_summary(clusters)
    paired: dict[str, Any] = {}
    for comparator in ("raw_qwen", "temperature_conformal_only", "semgrep_only"):
        left = point["frozen_hybrid"]
        right = point[comparator]
        paired[f"frozen_hybrid_minus_{comparator}"] = {
            "point_difference": {
                metric: left[metric] - right[metric]
                for metric in METRICS
                if left[metric] is not None and right[metric] is not None
            },
            "project_clustered_bootstrap_95_percent_interval": paired_intervals[
                f"frozen_hybrid_minus_{comparator}"
            ],
        }
    sizes = sorted(stats["records"] for stats in clusters.values())
    output = {
        "status": "complete",
        "method": {
            "unit": "project-clustered bootstrap resampling with replacement",
            "bootstrap_iterations": args.iterations,
            "seed": args.seed,
            "clusters": len(clusters),
            "test_labels_used_for_fitting_or_selection": False,
            "policy_parameters_changed": False,
        },
        "cluster_size_summary": {
            "minimum_records": min(sizes),
            "median_records": sizes[len(sizes) // 2],
            "maximum_records": max(sizes),
            "single_record_projects": sum(size == 1 for size in sizes),
        },
        "point_estimates": point,
        "bootstrap_intervals": intervals,
        "paired_comparisons": paired,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": output["status"], "output": str(args.output), "clusters": len(clusters)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

