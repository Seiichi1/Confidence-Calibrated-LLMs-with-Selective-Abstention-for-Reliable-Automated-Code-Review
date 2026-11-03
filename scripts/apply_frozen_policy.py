#!/usr/bin/env python3
"""Apply the frozen validation-derived policy without fitting on test labels."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from fit_qwen_calibration import EPS, extract_pair_probability, sigmoid


def p_value(scores: list[float], candidate: float) -> float:
    count = sum(score >= candidate - EPS for score in scores)
    return (1.0 + count) / (len(scores) + 1.0)


def prediction_set(probability: float, scores: list[float], alpha: float) -> list[int]:
    labels: list[int] = []
    if p_value(scores, probability) > alpha:
        labels.append(0)
    if p_value(scores, 1.0 - probability) > alpha:
        labels.append(1)
    return labels


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply frozen temperature/conformal/Semgrep policy")
    parser.add_argument("--qwen-results", type=Path, required=True)
    parser.add_argument("--calibration-artifact", type=Path, required=True)
    parser.add_argument("--static-results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--alpha", type=float, default=0.10)
    args = parser.parse_args()
    if args.alpha != 0.10:
        parser.error("the frozen policy requires --alpha 0.10")

    calibration = json.loads(args.calibration_artifact.read_text(encoding="utf-8"))
    temperature = float(calibration["calibration_parameters"]["temperature"])
    conformal_scores = [float(score) for score in calibration["methods"]["temperature"]["conformal_scores"]]
    static = json.loads(args.static_results.read_text(encoding="utf-8"))
    static_rows = {int(row["record_number"]): row for row in static["rows"]}

    rows: list[dict[str, Any]] = []
    with args.qwen_results.open("r", encoding="utf-8") as handle:
        for line in handle:
            source = json.loads(line)
            record_number = int(source["record_number"])
            record = source.get("record", {})
            probability = extract_pair_probability(source)
            static_row = static_rows.get(record_number)
            has_finding = static_row is not None and static_row.get("static_label") == "YES"
            if probability is None:
                labels: list[int] = []
                decision = "ABSTAIN"
                reason = "missing_pairwise_score"
            elif static_row is None:
                labels = []
                decision = "ABSTAIN"
                reason = "missing_static_result"
            else:
                raw_logit = math.log(probability / (1.0 - probability))
                calibrated_probability = sigmoid(raw_logit / temperature)
                labels = prediction_set(calibrated_probability, conformal_scores, args.alpha)
                if labels == [1] and has_finding:
                    decision = "YES"
                    reason = "singleton_positive_with_static_finding"
                else:
                    decision = "ABSTAIN"
                    reason = "frozen_gate_not_satisfied"
            rows.append(
                {
                    "record_number": record_number,
                    "idx": record.get("idx"),
                    "target": record.get("target"),
                    "decision": decision,
                    "reason": reason,
                    "prediction_set": labels,
                    "static_label": "YES" if has_finding else "NO_FINDING",
                }
            )

    decision_counts: dict[str, int] = {}
    reason_counts: dict[str, int] = {}
    for row in rows:
        decision_counts[row["decision"]] = decision_counts.get(row["decision"], 0) + 1
        reason_counts[row["reason"]] = reason_counts.get(row["reason"], 0) + 1
    output = {
        "status": "complete",
        "method": {
            "policy": "temperature scaling + split conformal alpha 0.10 + Semgrep corroborated-positive gate",
            "temperature": temperature,
            "conformal_score_records": len(conformal_scores),
            "alpha": args.alpha,
            "test_labels_used_for_fitting_or_selection": False,
            "final_test_policy_frozen": True,
        },
        "counts": {
            "qwen_records": len(rows),
            "decision_counts": decision_counts,
            "reason_counts": reason_counts,
        },
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "complete", "output": str(args.output), "counts": output["counts"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

