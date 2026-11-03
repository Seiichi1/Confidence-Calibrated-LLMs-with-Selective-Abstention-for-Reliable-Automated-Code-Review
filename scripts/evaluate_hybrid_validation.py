#!/usr/bin/env python3
"""Compare validation-only conformal decisions with Semgrep corroboration.

This script does not fit parameters and does not read the test partition. It
joins the conformal evaluation rows with the matching static-analysis rows and
reports two candidate gates:

1. corroborated-positive: accept only conformal singleton YES decisions that
   also have a Semgrep finding; all other records abstain;
2. dual-signal exploratory: accept YES only with a finding and accept NO only
   when there is no finding; all other records abstain.

The second policy is explicitly exploratory because absence of a static finding
is not proof of safety.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def metric_summary(rows: list[dict[str, Any]], labels: list[int | None]) -> dict[str, Any]:
    accepted = [(row, label) for row, label in zip(rows, labels) if label is not None]
    correct = sum(row["target"] == label for row, label in accepted)
    true_positive = sum(row["target"] == 1 and label == 1 for row, label in accepted)
    positive_total = sum(row["target"] == 1 for row in rows)
    accepted_yes = sum(label == 1 for _, label in accepted)
    return {
        "evaluation_records": len(rows),
        "accepted_records": len(accepted),
        "coverage": len(accepted) / max(len(rows), 1),
        "abstention_rate": 1.0 - len(accepted) / max(len(rows), 1),
        "accepted_precision": correct / max(len(accepted), 1),
        "accepted_correct": correct,
        "accepted_yes_records": accepted_yes,
        "accepted_positive_precision": true_positive / max(accepted_yes, 1),
        "accepted_positive_recall": true_positive / max(positive_total, 1),
        "accepted_positive_correct": true_positive,
        "evaluation_positive_records": positive_total,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate conformal plus Semgrep validation gates")
    parser.add_argument("--conformal", type=Path, required=True)
    parser.add_argument("--static", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--significance-levels", type=float, nargs="+", default=[0.01, 0.05, 0.10, 0.20, 0.30, 0.50])
    args = parser.parse_args()

    conformal = json.loads(args.conformal.read_text(encoding="utf-8"))
    static = json.loads(args.static.read_text(encoding="utf-8"))
    static_rows = {int(row["record_number"]): row for row in static["rows"]}
    methods: dict[str, Any] = {}
    common_counts: dict[str, int] = {}
    for method in ("temperature", "platt"):
        evaluation_rows = conformal["methods"][method]["evaluation_records"]
        common = [row for row in evaluation_rows if int(row["record_number"]) in static_rows]
        if len(common) != len(evaluation_rows):
            raise SystemExit(f"Static artifact is missing {len(evaluation_rows) - len(common)} {method} evaluation rows")
        common_counts[method] = len(common)
        summaries: list[dict[str, Any]] = []
        for significance in args.significance_levels:
            key = str(significance)
            rows: list[dict[str, Any]] = []
            corroborated_labels: list[int | None] = []
            dual_labels: list[int | None] = []
            for row in common:
                static_row = static_rows[int(row["record_number"])]
                has_finding = static_row["static_label"] == "YES"
                prediction_set = row["prediction_sets"].get(key)
                rows.append({"target": int(row["target"])})
                if prediction_set == [1] and has_finding:
                    corroborated_labels.append(1)
                else:
                    corroborated_labels.append(None)
                if prediction_set == [1] and has_finding:
                    dual_labels.append(1)
                elif prediction_set == [0] and not has_finding:
                    dual_labels.append(0)
                else:
                    dual_labels.append(None)
            summaries.append(
                {
                    "significance": significance,
                    "corroborated_positive_gate": metric_summary(rows, corroborated_labels),
                    "dual_signal_exploratory_gate": metric_summary(rows, dual_labels),
                    "review_escalation_count": sum(
                        row["prediction_sets"].get(key) != [0, 1]
                        and static_rows[int(row["record_number"])] ["static_label"] == "YES"
                        for row in common
                    ),
                }
            )
        methods[method] = {"evaluation_records": len(common), "operating_points": summaries}

    output = {
        "status": "complete",
        "method": {
            "conformal_artifact": str(args.conformal),
            "static_artifact": str(args.static),
            "final_test_used": False,
            "positive_gate_definition": "accept YES only for conformal singleton [1] plus a static finding; otherwise abstain",
            "dual_gate_definition": "accept YES only for singleton [1] plus finding; accept NO only for singleton [0] plus no finding; otherwise abstain",
            "dual_gate_caveat": "no static finding is not evidence of safety; this is exploratory only",
        },
        "counts": {"common_evaluation_records": common_counts},
        "methods": methods,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "complete", "output": str(args.output), "counts": output["counts"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

