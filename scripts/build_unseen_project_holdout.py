#!/usr/bin/env python3
"""Build a non-destructive, project-held-out PrimeVul evaluation manifest.

The candidate is drawn from the raw training partition, but only from projects
that do not occur in either the official validation or official test
partition.  Records are selected at whole-project granularity; the raw JSONL
files are never modified.  The resulting manifest is compatible with the
Qwen Colab runner, which reads ``kept_record_numbers`` as 1-based JSONL line
numbers.

This is an evaluation-candidate construction step, not model training and
not policy fitting.  The candidate must remain independent of the locked test
partition when reporting the final thesis result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def load_projects(path: Path) -> set[str]:
    projects: set[str] = set()
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            projects.add(str(record.get("project")))
    return projects


def load_high_priority_record_numbers(
    review_report: Path,
) -> dict[str, set[int]]:
    """Return high-priority record numbers by source partition."""

    report = json.loads(review_report.read_text(encoding="utf-8"))
    flagged: dict[str, set[int]] = defaultdict(set)
    for pair in report.get("pairs", []):
        if pair.get("review_priority") != "high":
            continue
        flagged[str(pair["left_partition"])].add(int(pair["left_record_number"]))
        flagged[str(pair["right_partition"])].add(int(pair["right_record_number"]))
    return {name: set(values) for name, values in flagged.items()}


def scan_train_candidate(
    path: Path,
    excluded_projects: set[str],
    flagged_train_records: set[int],
) -> dict[str, Any]:
    kept_record_numbers: list[int] = []
    excluded_record_numbers: list[int] = []
    excluded_project_record_numbers: list[int] = []
    excluded_flagged_record_numbers: list[int] = []
    kept_targets: Counter[str] = Counter()
    excluded_targets: Counter[str] = Counter()
    kept_projects: set[str] = set()
    all_projects: set[str] = set()

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for record_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            project = str(record.get("project"))
            target = str(record.get("target"))
            all_projects.add(project)

            reasons: list[str] = []
            if project in excluded_projects:
                reasons.append("project_occurs_in_official_validation_or_test")
            if record_number in flagged_train_records:
                reasons.append("high_priority_verified_cross_partition_overlap")

            if reasons:
                excluded_record_numbers.append(record_number)
                excluded_targets[target] += 1
                if project in excluded_projects:
                    excluded_project_record_numbers.append(record_number)
                if record_number in flagged_train_records:
                    excluded_flagged_record_numbers.append(record_number)
                continue

            kept_record_numbers.append(record_number)
            kept_targets[target] += 1
            kept_projects.add(project)

    excluded_reason_counts = {
        "project_occurs_in_official_validation_or_test": len(
            excluded_project_record_numbers
        ),
        "high_priority_verified_cross_partition_overlap": len(
            excluded_flagged_record_numbers
        ),
    }
    return {
        "source": str(path),
        "source_sha256": sha256_file(path),
        "source_partition": "train",
        "records_total": len(kept_record_numbers) + len(excluded_record_numbers),
        "records_kept": len(kept_record_numbers),
        "records_excluded": len(excluded_record_numbers),
        "records_kept_target_counts": dict(sorted(kept_targets.items())),
        "records_excluded_target_counts": dict(sorted(excluded_targets.items())),
        "projects_total": len(all_projects),
        "projects_kept": len(kept_projects),
        "projects_excluded_by_official_eval_overlap": len(
            all_projects & excluded_projects
        ),
        "excluded_reason_counts": excluded_reason_counts,
        "excluded_record_numbers": excluded_record_numbers,
        "kept_record_numbers": kept_record_numbers,
    }


def counts_from_records(path: Path) -> dict[str, Any]:
    targets: Counter[str] = Counter()
    projects: set[str] = set()
    records = 0
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            records += 1
            targets[str(record.get("target"))] += 1
            projects.add(str(record.get("project")))
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "records": records,
        "projects": len(projects),
        "target_counts": dict(sorted(targets.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--valid", type=Path, required=True)
    parser.add_argument("--test", type=Path, required=True)
    parser.add_argument("--review-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    valid_projects = load_projects(args.valid)
    test_projects = load_projects(args.test)
    official_eval_projects = valid_projects | test_projects
    flagged = load_high_priority_record_numbers(args.review_report)

    train_candidate = scan_train_candidate(
        args.train,
        excluded_projects=official_eval_projects,
        flagged_train_records=flagged.get("train", set()),
    )

    result = {
        "status": "complete",
        "manifest_type": "unseen_project_evaluation_candidate",
        "method": {
            "selection_unit": "whole project",
            "source_partition": "raw train",
            "project_exclusion_rule": (
                "exclude every train project occurring in official validation or test"
            ),
            "verified_overlap_rule": (
                "exclude high-priority verified cross-partition train records"
            ),
            "policy_or_model_selection_used": False,
            "raw_files_modified": False,
            "interpretation": (
                "new project-held-out candidate for independent evaluation; "
                "not a replacement for the locked official test result"
            ),
        },
        "source_partitions": {
            "train": counts_from_records(args.train),
            "valid": counts_from_records(args.valid),
            "test": counts_from_records(args.test),
        },
        "official_evaluation_project_counts": {
            "valid_projects": len(valid_projects),
            "test_projects": len(test_projects),
            "union_projects": len(official_eval_projects),
        },
        "high_priority_verified_record_counts": {
            partition: len(numbers) for partition, numbers in sorted(flagged.items())
        },
        "partitions": {
            "unseen_project_holdout": train_candidate,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "candidate_records": train_candidate["records_kept"],
        "candidate_projects": train_candidate["projects_kept"],
        "candidate_targets": train_candidate["records_kept_target_counts"],
        "output": str(args.output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

