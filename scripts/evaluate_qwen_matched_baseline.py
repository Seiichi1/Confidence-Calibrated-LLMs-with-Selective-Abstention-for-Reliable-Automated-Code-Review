#!/usr/bin/env python3
"""Evaluate a Qwen YES/NO JSONL run on the PrimeVul locked-test protocol.

This evaluator is deliberately separate from the selective hybrid evaluator.
It reports ordinary binary metrics for a matched open-source model baseline and
keeps unparseable outputs visible instead of silently converting them to NO.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable


LABEL_RE = re.compile(r"\b(YES|NO)\b", re.IGNORECASE)


def iter_rows(path: Path) -> Iterable[dict[str, Any]]:
    """Read either streamed JSONL or the small smoke-test JSON container."""
    text = path.read_text(encoding="utf-8")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict):
        yield from payload.get("results", [])
        return
    for line in text.splitlines():
        if line.strip():
            yield json.loads(line)


def value(row: dict[str, Any], key: str, default: Any = None) -> Any:
    if key in row:
        return row[key]
    record = row.get("record")
    if isinstance(record, dict):
        return record.get(key, default)
    return default


def parse_prediction(row: dict[str, Any]) -> str | None:
    direct = value(row, "prediction")
    if isinstance(direct, str) and direct.upper() in {"YES", "NO"}:
        return direct.upper()
    response = row.get("response", "")
    match = LABEL_RE.search(response or "")
    return match.group(1).upper() if match else None


def evaluate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    tp = fp = tn = fn = unparsed = 0
    for row in rows:
        target = int(value(row, "target"))
        prediction = parse_prediction(row)
        if prediction is None:
            unparsed += 1
            continue
        if target == 1 and prediction == "YES":
            tp += 1
        elif target == 0 and prediction == "YES":
            fp += 1
        elif target == 0 and prediction == "NO":
            tn += 1
        elif target == 1 and prediction == "NO":
            fn += 1

    parseable = tp + fp + tn + fn
    total = len(rows)
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else None
    )
    return {
        "records": total,
        "parseable_records": parseable,
        "unparseable_records": unparsed,
        "parseable_decision_coverage": parseable / total if total else None,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "accuracy_all_records_unparsed_incorrect": (tp + tn) / total if total else None,
        "accuracy_among_parseable_records": (tp + tn) / parseable if parseable else None,
        "yes_precision": precision,
        "yes_recall": recall,
        "yes_f1": f1,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--revision", default=None)
    parser.add_argument("--protocol", default="PrimeVul leakage-controlled natural locked test")
    args = parser.parse_args()

    rows = list(iter_rows(args.input))
    result = {
        "status": "complete",
        "method": {
            "description": "Ordinary YES/NO evaluation; no calibration or test-label policy selection",
            "positive_label": "YES",
            "unparseable_outputs": "reported separately; not converted to NO",
            "protocol": args.protocol,
        },
        "model": {"source": args.model, "revision": args.revision},
        "metrics": evaluate(rows),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

