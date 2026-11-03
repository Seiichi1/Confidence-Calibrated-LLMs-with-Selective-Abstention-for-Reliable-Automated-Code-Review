#!/usr/bin/env python3
"""Summarize high-priority PrimeVul near-duplicate pairs for protocol review."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any


def same_path(pair: dict[str, Any]) -> bool:
    left = pair["left_provenance"]
    right = pair["right_provenance"]
    return bool(left.get("project_file_path")) and (
        left.get("project") == right.get("project")
        and left.get("project_file_path") == right.get("project_file_path")
    )


def same_commit(pair: dict[str, Any]) -> bool:
    left = pair["left_provenance"]
    right = pair["right_provenance"]
    return bool(left.get("commit_id")) and left.get("commit_id") == right.get("commit_id")


def same_file_hash(pair: dict[str, Any]) -> bool:
    left = pair["left_provenance"]
    right = pair["right_provenance"]
    return bool(left.get("file_hash")) and left.get("file_hash") == right.get("file_hash")


def compact_pair(pair: dict[str, Any]) -> dict[str, Any]:
    left = pair["left_provenance"]
    right = pair["right_provenance"]
    return {
        "pair_key": pair["pair_key"],
        "left_partition": pair["left_partition"],
        "right_partition": pair["right_partition"],
        "classification": pair["classification"],
        "token_shingle_jaccard": pair["token_shingle_jaccard"],
        "line_similarity": pair["line_similarity"],
        "target_pair": [left.get("target"), right.get("target")],
        "left": {
            "idx": left.get("idx"),
            "project": left.get("project"),
            "commit_id": left.get("commit_id"),
            "func_hash": left.get("func_hash"),
            "file_name": left.get("file_name"),
            "project_file_path": left.get("project_file_path"),
            "cve": left.get("cve"),
        },
        "right": {
            "idx": right.get("idx"),
            "project": right.get("project"),
            "commit_id": right.get("commit_id"),
            "func_hash": right.get("func_hash"),
            "file_name": right.get("file_name"),
            "project_file_path": right.get("project_file_path"),
            "cve": right.get("cve"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--top", type=int, default=25)
    args = parser.parse_args()

    report = json.loads(args.input.read_text(encoding="utf-8"))
    pairs = [pair for pair in report["pairs"] if pair["review_priority"] == "high"]
    target_pairs = Counter(
        f"{pair['left_provenance'].get('target')}->{pair['right_provenance'].get('target')}"
        for pair in pairs
    )
    partition_pairs = Counter(
        f"{pair['left_partition']}/{pair['right_partition']}" for pair in pairs
    )
    similarity = [pair["token_shingle_jaccard"] for pair in pairs]
    line_similarity = [pair["line_similarity"] for pair in pairs]
    mismatch = [
        pair
        for pair in pairs
        if pair["left_provenance"].get("target")
        != pair["right_provenance"].get("target")
    ]
    path_pairs = [pair for pair in pairs if same_path(pair)]
    commit_pairs = [pair for pair in pairs if same_commit(pair)]
    file_hash_pairs = [pair for pair in pairs if same_file_hash(pair)]
    affected_records: dict[str, set[int]] = {}
    for pair in pairs:
        affected_records.setdefault(pair["left_partition"], set()).add(
            pair["left_record_number"]
        )
        affected_records.setdefault(pair["right_partition"], set()).add(
            pair["right_record_number"]
        )

    result = {
        "status": "complete",
        "source_report": str(args.input),
        "method": {
            "scope": "verified candidates with review_priority=high",
            "interpretation": "triage categories and recommendations do not prove semantic leakage",
        },
        "counts": {
            "high_priority_pairs": len(pairs),
            "same_file_or_path_class": sum(
                pair["classification"] == "same_file_or_path" for pair in pairs
            ),
            "shared_commit_class": sum(
                pair["classification"] == "shared_commit" for pair in pairs
            ),
            "same_project_file_path": len(path_pairs),
            "same_project_file_path_cross_commit": sum(
                same_path(pair) and not same_commit(pair) for pair in pairs
            ),
            "same_commit": len(commit_pairs),
            "same_file_hash": len(file_hash_pairs),
            "target_mismatch": len(mismatch),
            "both_vulnerable": target_pairs.get("1->1", 0),
            "both_non_vulnerable": target_pairs.get("0->0", 0),
        },
        "affected_record_counts": {
            partition: len(record_numbers)
            for partition, record_numbers in sorted(affected_records.items())
        },
        "partition_pair_counts": dict(sorted(partition_pairs.items())),
        "target_pair_counts": dict(sorted(target_pairs.items())),
        "similarity_summary": {
            "jaccard_min": min(similarity),
            "jaccard_mean": statistics.fmean(similarity),
            "jaccard_median": statistics.median(similarity),
            "jaccard_max": max(similarity),
            "line_similarity_min": min(line_similarity),
            "line_similarity_mean": statistics.fmean(line_similarity),
            "line_similarity_median": statistics.median(line_similarity),
            "line_similarity_max": max(line_similarity),
        },
        "protocol_recommendation": {
            "same_project_file_path_cross_commit": "treat as a high-priority grouped-split or exclusion review set before baseline claims",
            "same_commit": "treat as a high-priority snapshot-overlap review set",
            "target_mismatch": "inspect representative diffs because near-identical vulnerable/non-vulnerable labels can indicate version/label leakage or distinct annotations",
            "dataset_action": "no automatic deletion or relabeling; preserve raw partitions until the leakage policy is explicitly frozen",
        },
        "top_target_mismatch_pairs": [
            compact_pair(pair)
            for pair in sorted(
                mismatch,
                key=lambda pair: (
                    pair["token_shingle_jaccard"],
                    pair["line_similarity"],
                ),
                reverse=True,
            )[: args.top]
        ],
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

