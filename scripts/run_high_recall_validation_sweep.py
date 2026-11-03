#!/usr/bin/env python3
"""Search higher-recall conformal policies using validation data only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


EPS = 1e-12


def p_value(scores: list[float], candidate: float) -> float:
    return (1.0 + sum(score >= candidate - EPS for score in scores)) / (len(scores) + 1.0)


def prediction_set(probability: float, scores: list[float], alpha: float) -> list[int]:
    labels: list[int] = []
    if p_value(scores, probability) > alpha:
        labels.append(0)
    if p_value(scores, 1.0 - probability) > alpha:
        labels.append(1)
    return labels


def summary(rows: list[dict[str, Any]], decisions: list[int | None]) -> dict[str, Any]:
    accepted = [(row, decision) for row, decision in zip(rows, decisions) if decision is not None]
    tp = sum(row["target"] == 1 and decision == 1 for row, decision in accepted)
    fp = sum(row["target"] == 0 and decision == 1 for row, decision in accepted)
    positive_total = sum(row["target"] == 1 for row in rows)
    accepted_count = len(accepted)
    coverage = accepted_count / max(len(rows), 1)
    fn = sum(row["target"] == 1 and decision == 0 for row, decision in accepted)
    tn = sum(row["target"] == 0 and decision == 0 for row, decision in accepted)
    return {
        "records": len(rows),
        "accepted": accepted_count,
        "abstained": len(rows) - accepted_count,
        "coverage": coverage,
        "abstention_rate": 1.0 - coverage,
        "true_positive": tp,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "accepted_positive_precision": tp / accepted_count if accepted_count else None,
        "positive_recall": tp / positive_total if positive_total else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--conformal", type=Path, required=True)
    parser.add_argument("--static", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--alphas",
        type=float,
        nargs="+",
        default=[0.01, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90],
    )
    args = parser.parse_args()
    if any(not 0.0 < alpha < 1.0 for alpha in args.alphas):
        parser.error("all alphas must be between 0 and 1")

    conformal = json.loads(args.conformal.read_text(encoding="utf-8"))
    method = conformal["methods"]["temperature"]
    scores = [float(value) for value in method["conformal_scores"]]
    rows = [
        {"record_number": int(row["record_number"]), "target": int(row["target"]), "probability": float(row["probability"])}
        for row in method["evaluation_records"]
    ]
    static = json.loads(args.static.read_text(encoding="utf-8"))
    static_rows = {int(row["record_number"]): row for row in static["rows"]}

    candidates: list[dict[str, Any]] = []
    for alpha in args.alphas:
        sets = {
            row["record_number"]: prediction_set(row["probability"], scores, alpha)
            for row in rows
        }
        for policy in ("conformal_singleton", "corroborated_positive"):
            decisions: list[int | None] = []
            for row in rows:
                labels = sets[row["record_number"]]
                finding = static_rows[row["record_number"]].get("static_label") == "YES"
                if policy == "conformal_singleton":
                    decision = labels[0] if len(labels) == 1 else None
                else:
                    decision = 1 if labels == [1] and finding else None
                decisions.append(decision)
            candidates.append({"alpha": alpha, "policy": policy, "summary": summary(rows, decisions)})

    for candidate in candidates:
        s = candidate["summary"]
        s["normalized_cost_fn20_fp1_review05"] = (
            20 * s["false_negative"]
            + s["false_positive"]
            + 0.5 * s["abstained"]
        ) / s["records"]

    selected: dict[str, Any] = {}
    for floor in (0.20, 0.30, 0.40, 0.50):
        eligible = [
            candidate for candidate in candidates
            if candidate["summary"]["positive_recall"] is not None
            and candidate["summary"]["positive_recall"] >= floor
        ]
        selected[str(floor)] = sorted(
            eligible,
            key=lambda candidate: (
                candidate["summary"]["normalized_cost_fn20_fp1_review05"],
                -(candidate["summary"]["accepted_positive_precision"] or -1.0),
            ),
        )[:5]

    output = {
        "status": "complete",
        "method": {
            "validation_only": True,
            "calibrator": "temperature scaling",
            "static_gate": "Semgrep corroborated-positive for the corroborated candidate",
            "false_negative_cost": 20,
            "false_positive_cost": 1,
            "review_cost": 0.5,
            "positive_recall_floors": [0.20, 0.30, 0.40, 0.50],
            "test_labels_used": False,
        },
        "candidates": candidates,
        "selected_by_recall_floor": selected,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "complete", "output": str(args.output), "candidates": len(candidates)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

