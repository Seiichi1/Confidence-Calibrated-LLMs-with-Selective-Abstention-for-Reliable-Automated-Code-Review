#!/usr/bin/env python3
"""Review all verified PrimeVul near-duplicate pairs from the SQLite store."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sqlite3
import struct
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from near_duplicate_scan import hamming_distance, pair_name
from near_duplicate_verify import TOKEN_RE, jaccard, unpack_shingles


WHITESPACE_RE = re.compile(r"\s+")


def canonical_code(code: str) -> str:
    return WHITESPACE_RE.sub(" ", code).strip()


def code_hash(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8", errors="replace")).hexdigest()


def record_code_stats(code: str) -> dict[str, Any]:
    return {
        "characters": len(code),
        "lines": len(code.splitlines()),
        "tokens": len(TOKEN_RE.findall(code)),
        "raw_sha256": code_hash(code),
        "canonical_sha256": code_hash(canonical_code(code)),
    }


def provenance(record: dict[str, Any], file_info: dict[str, Any]) -> dict[str, Any]:
    func_hash = str(record.get("func_hash"))
    metadata = file_info.get(func_hash) or {}
    file_hash = metadata.get("file_hash")
    if file_hash in (None, ""):
        file_hash = record.get("file_hash") or None
    return {
        "idx": record.get("idx"),
        "project": record.get("project"),
        "commit_id": record.get("commit_id"),
        "func_hash": func_hash,
        "target": record.get("target"),
        "cwe": record.get("cwe"),
        "cve": record.get("cve"),
        "file_name": metadata.get("file_name") or record.get("file_name"),
        "file_hash": str(file_hash) if file_hash not in (None, "") else None,
        "project_file_path": metadata.get("project_file_path"),
        "local_file_path": metadata.get("local_file_path"),
        "start_line": metadata.get("start_line"),
        "end_line": metadata.get("end_line"),
    }


def pair_classification(left: dict[str, Any], right: dict[str, Any]) -> tuple[str, str]:
    same_project = left["project"] == right["project"]
    same_commit = bool(left.get("commit_id")) and left.get("commit_id") == right.get("commit_id")
    same_file_hash = bool(left.get("file_hash")) and left.get("file_hash") == right.get("file_hash")
    same_file_path = (
        bool(left.get("project_file_path"))
        and left.get("project_file_path") == right.get("project_file_path")
        and same_project
    )
    if same_file_hash or same_file_path:
        return "same_file_or_path", "high"
    if same_commit:
        return "shared_commit", "high"
    if same_project:
        return "same_project_only", "medium"
    if left.get("project") and right.get("project"):
        return "cross_project", "low"
    return "insufficient_provenance", "review"


def load_needed_records(
    partitions: list[tuple[str, Path]], needed: dict[str, set[int]]
) -> dict[tuple[str, int], dict[str, Any]]:
    records: dict[tuple[str, int], dict[str, Any]] = {}
    for name, path in partitions:
        wanted = needed.get(name, set())
        if not wanted:
            continue
        print(f"Loading provenance for {name}: {path}", file=sys.stderr, flush=True)
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line_number, line in enumerate(handle, start=1):
                if line_number not in wanted or not line.strip():
                    continue
                records[(name, line_number)] = json.loads(line)
    return records


def extract_verified_pairs(
    database_path: Path,
    partition_names: tuple[str, str, str],
    max_hamming_distance: int,
    jaccard_threshold: float,
) -> list[dict[str, Any]]:
    uri = f"file:{database_path.as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    pairs: list[dict[str, Any]] = []
    try:
        ordered = (
            (partition_names[1], (partition_names[0],)),
            (partition_names[2], (partition_names[0], partition_names[1])),
        )
        for current_partition, allowed_old_partitions in ordered:
            print(f"Extracting verified pairs for {current_partition}", file=sys.stderr, flush=True)
            allowed_placeholders = ",".join("?" for _ in allowed_old_partitions)
            current_rows = connection.execute(
                """
                SELECT record_key, record_number, dataset_idx, project,
                       function_hash, signature_hex, shingle_blob
                FROM records WHERE partition_name = ? ORDER BY record_number
                """,
                (current_partition,),
            )
            for processed, current in enumerate(current_rows, start=1):
                (
                    current_key,
                    current_number,
                    current_idx,
                    current_project,
                    current_func_hash,
                    current_signature_hex,
                    current_blob,
                ) = current
                current_signature = int(current_signature_hex, 16)
                current_shingles = unpack_shingles(current_blob)
                buckets = [
                    (band, (current_signature >> (band * 16)) & 0xFFFF)
                    for band in range(4)
                ]
                conditions = " OR ".join(
                    "(b.band = ? AND b.bucket = ?)" for _ in buckets
                )
                params: list[Any] = list(allowed_old_partitions)
                params.extend(value for pair in buckets for value in pair)
                rows = connection.execute(
                    f"""
                    SELECT r.record_key, r.partition_name, r.record_number,
                           r.dataset_idx, r.project, r.function_hash,
                           r.signature_hex, r.shingle_blob
                    FROM band_index b
                    JOIN records r ON r.record_key = b.record_key
                    WHERE r.partition_name IN ({allowed_placeholders})
                      AND ({conditions})
                    """,
                    params,
                )
                candidates: dict[int, tuple[Any, ...]] = {}
                for row in rows:
                    candidates[row[0]] = row
                for row in candidates.values():
                    (
                        old_key,
                        old_partition,
                        old_number,
                        old_idx,
                        old_project,
                        old_func_hash,
                        old_signature_hex,
                        old_blob,
                    ) = row
                    distance = hamming_distance(
                        current_signature, int(old_signature_hex, 16)
                    )
                    if distance > max_hamming_distance:
                        continue
                    old_shingles = unpack_shingles(old_blob)
                    if not current_shingles or not old_shingles:
                        continue
                    if (
                        min(len(current_shingles), len(old_shingles))
                        / max(len(current_shingles), len(old_shingles))
                        < jaccard_threshold
                    ):
                        continue
                    similarity = jaccard(current_shingles, old_shingles)
                    if similarity < jaccard_threshold:
                        continue
                    pairs.append(
                        {
                            "pair_key": f"{old_key}:{current_key}",
                            "left_partition": old_partition,
                            "left_record_number": old_number,
                            "left_idx": old_idx,
                            "left_project": old_project,
                            "left_func_hash": old_func_hash,
                            "right_partition": current_partition,
                            "right_record_number": current_number,
                            "right_idx": current_idx,
                            "right_project": current_project,
                            "right_func_hash": current_func_hash,
                            "hamming_distance": distance,
                            "token_shingle_jaccard": similarity,
                        }
                    )
                if processed % 5000 == 0:
                    print(
                        f"{current_partition}: {processed} records, {len(pairs)} verified pairs",
                        file=sys.stderr,
                        flush=True,
                    )
    finally:
        connection.close()
    return pairs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--file-info", type=Path, required=True)
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--valid", type=Path, required=True)
    parser.add_argument("--test", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--diff-output", type=Path, required=True)
    parser.add_argument("--sample-diffs", type=int, default=25)
    parser.add_argument("--max-hamming-distance", type=int, default=8)
    parser.add_argument("--jaccard-threshold", type=float, default=0.8)
    args = parser.parse_args()
    partitions = [("train", args.train), ("valid", args.valid), ("test", args.test)]
    if not args.database.is_file():
        parser.error(f"database does not exist: {args.database}")
    if args.sample_diffs < 0 or not 0 <= args.jaccard_threshold <= 1:
        parser.error("sample-diffs must be nonnegative and threshold must be between 0 and 1")

    pairs = extract_verified_pairs(
        args.database,
        ("train", "valid", "test"),
        args.max_hamming_distance,
        args.jaccard_threshold,
    )
    with args.file_info.open("r", encoding="utf-8") as handle:
        file_info = json.load(handle)
    needed = {name: set() for name, _ in partitions}
    for pair in pairs:
        needed[pair["left_partition"]].add(pair["left_record_number"])
        needed[pair["right_partition"]].add(pair["right_record_number"])
    records = load_needed_records(partitions, needed)

    reviewed: list[dict[str, Any]] = []
    classification_counts: Counter[str] = Counter()
    priority_counts: Counter[str] = Counter()
    for pair in pairs:
        left_record = records[(pair["left_partition"], pair["left_record_number"])]
        right_record = records[(pair["right_partition"], pair["right_record_number"])]
        left_provenance = provenance(left_record, file_info)
        right_provenance = provenance(right_record, file_info)
        classification, priority = pair_classification(left_provenance, right_provenance)
        left_code = str(left_record.get("func") or "")
        right_code = str(right_record.get("func") or "")
        left_stats = record_code_stats(left_code)
        right_stats = record_code_stats(right_code)
        line_similarity = difflib.SequenceMatcher(
            None,
            left_code.splitlines(),
            right_code.splitlines(),
        ).ratio()
        item = {
            **pair,
            "classification": classification,
            "review_priority": priority,
            "left_provenance": left_provenance,
            "right_provenance": right_provenance,
            "left_code": left_stats,
            "right_code": right_stats,
            "line_similarity": round(line_similarity, 6),
            "exact_raw_code_match": left_stats["raw_sha256"] == right_stats["raw_sha256"],
            "exact_canonical_code_match": left_stats["canonical_sha256"] == right_stats["canonical_sha256"],
        }
        reviewed.append(item)
        classification_counts[classification] += 1
        priority_counts[priority] += 1

    reviewed.sort(
        key=lambda item: (
            {"high": 0, "medium": 1, "low": 2, "review": 3}[item["review_priority"]],
            -item["token_shingle_jaccard"],
        )
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "complete",
        "method": {
            "source_database": str(args.database),
            "jaccard_threshold": args.jaccard_threshold,
            "max_hamming_distance": args.max_hamming_distance,
            "classification": "provenance review categories; no category alone proves leakage",
        },
        "pair_count": len(reviewed),
        "classification_counts": dict(classification_counts),
        "priority_counts": dict(priority_counts),
        "pairs": reviewed,
    }
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    diff_lines: list[str] = []
    for item in reviewed[: args.sample_diffs]:
        left_key = (item["left_partition"], item["left_record_number"])
        right_key = (item["right_partition"], item["right_record_number"])
        left_code = str(records[left_key].get("func") or "").splitlines()
        right_code = str(records[right_key].get("func") or "").splitlines()
        diff_lines.extend(
            [
                "=" * 80,
                json.dumps(
                    {
                        "pair_key": item["pair_key"],
                        "classification": item["classification"],
                        "jaccard": item["token_shingle_jaccard"],
                        "left": item["left_provenance"],
                        "right": item["right_provenance"],
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        diff_lines.extend(
            difflib.unified_diff(
                left_code,
                right_code,
                fromfile=f"{item['left_partition']}:{item['left_record_number']}",
                tofile=f"{item['right_partition']}:{item['right_record_number']}",
                lineterm="",
                n=3,
            )
        )
        diff_lines.append("")
    args.diff_output.parent.mkdir(parents=True, exist_ok=True)
    args.diff_output.write_text("\n".join(diff_lines), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "pair_count": report["pair_count"],
                "classification_counts": report["classification_counts"],
                "output": str(args.output),
                "diff_output": str(args.diff_output),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

