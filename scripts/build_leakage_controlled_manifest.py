#!/usr/bin/env python3
"""Build a conservative, non-destructive evaluation exclusion manifest."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def load_flagged_nodes(report_path: Path, priority: str) -> dict[str, set[int]]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    flagged: dict[str, set[int]] = {"train": set(), "valid": set(), "test": set()}
    for pair in report["pairs"]:
        if priority != "all_verified" and pair["review_priority"] != priority:
            continue
        flagged[pair["left_partition"]].add(pair["left_record_number"])
        flagged[pair["right_partition"]].add(pair["right_record_number"])
    return flagged


def scan_partition(path: Path, excluded: set[int]) -> dict[str, Any]:
    total = 0
    excluded_targets: Counter[str] = Counter()
    kept_targets: Counter[str] = Counter()
    excluded_records: list[int] = []
    kept_records: list[int] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for record_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            total += 1
            record = json.loads(line)
            target = str(record.get("target"))
            if record_number in excluded:
                excluded_records.append(record_number)
                excluded_targets[target] += 1
            else:
                kept_records.append(record_number)
                kept_targets[target] += 1
    return {
        "source": str(path),
        "records_total": total,
        "records_excluded": len(excluded_records),
        "records_kept": len(kept_records),
        "excluded_target_counts": dict(sorted(excluded_targets.items())),
        "kept_target_counts": dict(sorted(kept_targets.items())),
        "excluded_record_numbers": excluded_records,
        "kept_record_numbers": kept_records,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-report", type=Path, required=True)
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--valid", type=Path, required=True)
    parser.add_argument("--test", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--priority",
        choices=("high", "all_verified"),
        default="high",
        help="Use high-priority provenance pairs or all verified pairs.",
    )
    args = parser.parse_args()

    flagged = load_flagged_nodes(args.review_report, args.priority)
    # Train stays available for model fitting but is explicitly reported as flagged.
    partitions = {
        "train": scan_partition(args.train, set()),
        "valid": scan_partition(args.valid, flagged["valid"]),
        "test": scan_partition(args.test, flagged["test"]),
    }
    result = {
        "status": "complete",
        "method": {
            "policy": "keep train; exclude flagged validation and test records",
            "priority_scope": args.priority,
            "interpretation": "derived manifest only; source JSONL files are unchanged",
            "warning": "This conservative manifest removes evaluation records rather than proving semantic leakage.",
        },
        "source_review_report": str(args.review_report),
        "flagged_record_counts_before_exclusion": {
            partition: len(record_numbers)
            for partition, record_numbers in sorted(flagged.items())
        },
        "partitions": partitions,
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

