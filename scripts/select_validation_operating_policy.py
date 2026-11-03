#!/usr/bin/env python3
"""Sweep validation-only operating policies under explicit review costs.

This is a policy-analysis tool, not a test-set threshold selector. It compares
singleton conformal decisions with the corroborated-positive and dual-signal
hybrid gates across a grid of false-negative and manual-review costs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def metrics(rows: list[dict[str, Any]], decisions: list[int | None]) -> dict[str, Any]:
    accepted = [(row, decision) for row, decision in zip(rows, decisions) if decision is not None]
    fp = sum(row["target"] == 0 and decision == 1 for row, decision in accepted)
    fn = sum(row["target"] == 1 and decision == 0 for row, decision in accepted)
    tp = sum(row["target"] == 1 and decision == 1 for row, decision in accepted)
    tn = sum(row["target"] == 0 and decision == 0 for row, decision in accepted)
    positive_total = sum(row["target"] == 1 for row in rows)
    return {
        "records": len(rows),
        "accepted": len(accepted),
        "abstained": len(rows) - len(accepted),
        "coverage": len(accepted) / max(len(rows), 1),
        "abstention_rate": (len(rows) - len(accepted)) / max(len(rows), 1),
        "true_positive": tp,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "accepted_precision": (tp + tn) / max(len(accepted), 1),
        "positive_precision": tp / max(sum(decision == 1 for _, decision in accepted), 1),
        "positive_recall": tp / max(positive_total, 1),
    }


def cost(summary: dict[str, Any], false_negative_cost: float, false_positive_cost: float, review_cost: float) -> float:
    return (
        false_negative_cost * summary["false_negative"]
        + false_positive_cost * summary["false_positive"]
        + review_cost * summary["abstained"]
    ) / max(summary["records"], 1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sweep validation operating policies")
    parser.add_argument("--conformal", type=Path, required=True)
    parser.add_argument("--static", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--false-negative-costs", type=float, nargs="+", default=[5, 10, 20, 50, 100])
    parser.add_argument("--false-positive-cost", type=float, default=1.0)
    parser.add_argument("--review-costs", type=float, nargs="+", default=[0.1, 0.25, 0.5, 1.0, 2.0])
    parser.add_argument("--default-false-negative-cost", type=float, default=10.0)
    parser.add_argument("--default-review-cost", type=float, default=0.5)
    parser.add_argument("--positive-recall-floors", type=float, nargs="+", default=[0.05, 0.10, 0.20])
    args = parser.parse_args()

    conformal = json.loads(args.conformal.read_text(encoding="utf-8"))
    static = json.loads(args.static.read_text(encoding="utf-8"))
    static_rows = {int(row["record_number"]): row for row in static["rows"]}
    candidates: list[dict[str, Any]] = []
    for method in ("temperature", "platt"):
        evaluation = conformal["methods"][method]["evaluation_records"]
        rows = [{"target": int(row["target"]), "record_number": int(row["record_number"])} for row in evaluation]
        for significance in (0.01, 0.05, 0.10, 0.20, 0.30, 0.50):
            key = str(significance)
            sets = [row["prediction_sets"].get(key, []) for row in evaluation]
            findings = [static_rows[row["record_number"]]["static_label"] == "YES" for row in rows]
            policies = {
                "conformal_singleton": [labels[0] if len(labels) == 1 else None for labels in sets],
                "corroborated_positive": [1 if labels == [1] and finding else None for labels, finding in zip(sets, findings)],
                "dual_signal_exploratory": [
                    1 if labels == [1] and finding else 0 if labels == [0] and not finding else None
                    for labels, finding in zip(sets, findings)
                ],
            }
            for policy, decisions in policies.items():
                summary = metrics(rows, decisions)
                candidates.append(
                    {
                        "candidate": f"{method}_{policy}",
                        "method": method,
                        "policy": policy,
                        "significance": significance,
                        "summary": summary,
                    }
                )

    scenarios = []
    for fn_cost in args.false_negative_costs:
        for review_cost in args.review_costs:
            scored = []
            for candidate in candidates:
                value = cost(candidate["summary"], fn_cost, args.false_positive_cost, review_cost)
                scored.append({"candidate": candidate["candidate"], "significance": candidate["significance"], "normalized_cost": value})
            scored.sort(key=lambda item: (item["normalized_cost"], item["candidate"], item["significance"]))
            constrained = {}
            for floor in args.positive_recall_floors:
                eligible = [
                    item for item in scored
                    if next(
                        candidate["summary"]["positive_recall"]
                        for candidate in candidates
                        if candidate["candidate"] == item["candidate"] and candidate["significance"] == item["significance"]
                    ) >= floor
                ]
                constrained[str(floor)] = eligible[:5]
            scenarios.append(
                {
                    "false_negative_cost": fn_cost,
                    "false_positive_cost": args.false_positive_cost,
                    "review_cost": review_cost,
                    "best": scored[:5],
                    "best_by_positive_recall_floor": constrained,
                }
            )

    default_scored = []
    for candidate in candidates:
        default_scored.append(
            {
                "candidate": candidate["candidate"],
                "method": candidate["method"],
                "policy": candidate["policy"],
                "significance": candidate["significance"],
                "normalized_cost": cost(candidate["summary"], args.default_false_negative_cost, args.false_positive_cost, args.default_review_cost),
                "summary": candidate["summary"],
            }
        )
    default_scored.sort(key=lambda item: (item["normalized_cost"], item["candidate"], item["significance"]))
    output = {
        "status": "complete",
        "method": {
            "validation_only": True,
            "false_positive_cost": args.false_positive_cost,
            "false_negative_costs": args.false_negative_costs,
            "review_costs": args.review_costs,
            "positive_recall_floors": args.positive_recall_floors,
            "default_scenario": {
                "false_negative_cost": args.default_false_negative_cost,
                "false_positive_cost": args.false_positive_cost,
                "review_cost": args.default_review_cost,
            },
            "abstention_cost_interpretation": "each abstained record is escalated to manual review and incurs review_cost",
            "policy_frozen": False,
            "final_test_used": False,
        },
        "counts": {"candidate_policies": len(candidates), "scenarios": len(scenarios)},
        "default_ranking": default_scored,
        "scenario_rankings": scenarios,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "complete", "output": str(args.output), "counts": output["counts"], "default_best": default_scored[:5]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

