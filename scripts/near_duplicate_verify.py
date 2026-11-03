#!/usr/bin/env python3
"""Second-stage token-shingle verification for PrimeVul candidates.

This scan is intentionally separate from ``near_duplicate_scan.py``. It uses
the same bounded SimHash candidate generator, then calculates exact Jaccard
similarity over deterministic token 5-gram hash sets for each candidate that
passes the SimHash Hamming threshold. The SQLite database stores shingle blobs
outside the project directory so the Python process remains memory-bounded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import struct
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from tempfile import gettempdir
from typing import Any

from near_duplicate_scan import (
    FIELD_ALIASES,
    TOKEN_RE,
    SimHasher,
    as_text,
    first_value,
    hamming_distance,
    pair_name,
)


SHINGLE_SIZE = 5
UINT64_MASK = (1 << 64) - 1
FNV_OFFSET = 1469598103934665603
FNV_PRIME = 1099511628211


def token_hash(token: str, cache: dict[str, int]) -> int:
    value = cache.get(token)
    if value is None:
        value = int.from_bytes(
            hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest(),
            "big",
        )
        cache[token] = value
    return value


def sampled_tokens(tokens: list[str], max_tokens: int | None) -> list[str]:
    if max_tokens is None or len(tokens) <= max_tokens:
        return tokens
    stride = len(tokens) / max_tokens
    return [tokens[int(index * stride)] for index in range(max_tokens)]


def shingle_hashes(
    code: str,
    cache: dict[str, int],
    max_tokens: int | None,
) -> tuple[bytes, int]:
    tokens = sampled_tokens(TOKEN_RE.findall(code), max_tokens)
    if len(tokens) < SHINGLE_SIZE:
        return b"", len(tokens)
    token_values = [token_hash(token, cache) for token in tokens]
    shingles: set[int] = set()
    # Rolling polynomial hash: one update per token rather than recomputing
    # all five token contributions for every overlapping shingle.
    power = pow(FNV_PRIME, SHINGLE_SIZE - 1, 1 << 64)
    value = 0
    for index, token_value in enumerate(token_values):
        if index < SHINGLE_SIZE:
            value = (value * FNV_PRIME + token_value) & UINT64_MASK
            if index == SHINGLE_SIZE - 1:
                shingles.add(value)
            continue
        outgoing = token_values[index - SHINGLE_SIZE]
        value = (value - (outgoing * power)) & UINT64_MASK
        value = (value * FNV_PRIME + token_value) & UINT64_MASK
        shingles.add(value)
    ordered = sorted(shingles)
    return struct.pack(f"<{len(ordered)}Q", *ordered), len(tokens)


def unpack_shingles(blob: bytes) -> tuple[int, ...]:
    if not blob:
        return ()
    return struct.unpack(f"<{len(blob) // 8}Q", blob)


def jaccard(left: tuple[int, ...], right: tuple[int, ...]) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    left_index = right_index = intersection = 0
    while left_index < len(left) and right_index < len(right):
        if left[left_index] == right[right_index]:
            intersection += 1
            left_index += 1
            right_index += 1
        elif left[left_index] < right[right_index]:
            left_index += 1
        else:
            right_index += 1
    union = len(left) + len(right) - intersection
    return intersection / union if union else 1.0


def histogram_bin(value: float) -> str:
    if value >= 1.0:
        return "1.0"
    lower = int(value * 10) / 10
    return f"{lower:.1f}-{lower + 0.1:.1f}"


def initialize_database(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA journal_mode = OFF")
    connection.execute("PRAGMA synchronous = OFF")
    connection.execute("PRAGMA temp_store = MEMORY")
    connection.execute("PRAGMA cache_size = -65536")
    connection.execute(
        """
        CREATE TABLE records (
            record_key INTEGER PRIMARY KEY,
            partition_name TEXT NOT NULL,
            record_number INTEGER NOT NULL,
            dataset_idx TEXT,
            project TEXT,
            function_hash TEXT,
            signature_hex TEXT NOT NULL,
            shingle_blob BLOB NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE band_index (
            band INTEGER NOT NULL,
            bucket INTEGER NOT NULL,
            record_key INTEGER NOT NULL
        )
        """
    )
    connection.execute(
        "CREATE INDEX band_index_lookup ON band_index (band, bucket)"
    )


def scan(
    partitions: list[tuple[str, Path]],
    database_path: Path,
    sample_limit: int,
    bucket_cap: int,
    min_tokens: int,
    max_simhash_tokens: int,
    max_verify_tokens: int | None,
    max_hamming_distance: int,
    jaccard_threshold: float,
) -> dict[str, Any]:
    if database_path.exists():
        database_path.unlink()
    database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(database_path))
    initialize_database(connection)
    simhasher = SimHasher()
    token_cache: dict[str, int] = {}
    bucket_counts: Counter[tuple[int, int]] = Counter()
    records_seen: Counter[str] = Counter()
    eligible_records: Counter[str] = Counter()
    skipped_records: Counter[str] = Counter()
    invalid_records: Counter[str] = Counter()
    candidate_pairs_checked: Counter[str] = Counter()
    simhash_hits: Counter[str] = Counter()
    verified_pairs: Counter[str] = Counter()
    histograms: dict[str, Counter[str]] = defaultdict(Counter)
    size_bound_rejects: Counter[str] = Counter()
    samples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    started = time.time()
    next_record_key = 1

    try:
        for partition_index, (partition_name, partition_path) in enumerate(partitions):
            print(f"Verifying {partition_name}: {partition_path}", file=sys.stderr, flush=True)
            with partition_path.open(
                "r", encoding="utf-8", errors="replace"
            ) as handle:
                for record_number, line in enumerate(handle, start=1):
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        invalid_records[partition_name] += 1
                        continue
                    if not isinstance(record, dict):
                        invalid_records[partition_name] += 1
                        continue

                    records_seen[partition_name] += 1
                    code = as_text(first_value(record, FIELD_ALIASES["code"]))
                    if not code:
                        skipped_records[partition_name] += 1
                        continue
                    signature, token_count, _ = simhasher.signature(
                        code, max_simhash_tokens
                    )
                    if token_count < min_tokens:
                        skipped_records[partition_name] += 1
                        continue
                    eligible_records[partition_name] += 1
                    shingle_blob, verified_token_count = shingle_hashes(
                        code, token_cache, max_verify_tokens
                    )
                    current_signature_hex = f"{signature:016x}"
                    band_buckets = [
                        (band, (signature >> (band * 16)) & 0xFFFF)
                        for band in range(4)
                    ]
                    candidate_rows: dict[int, tuple[Any, ...]] = {}
                    if partition_index > 0:
                        conditions = " OR ".join(
                            "(b.band = ? AND b.bucket = ?)" for _ in band_buckets
                        )
                        query_params = [partition_name]
                        query_params.extend(
                            value for pair in band_buckets for value in pair
                        )
                        rows = connection.execute(
                            f"""
                            SELECT r.record_key, r.partition_name, r.record_number,
                                   r.dataset_idx, r.project, r.function_hash,
                                   r.signature_hex, r.shingle_blob
                            FROM band_index b
                            JOIN records r ON r.record_key = b.record_key
                            WHERE r.partition_name <> ? AND ({conditions})
                            """,
                            query_params,
                        )
                        for row in rows:
                            candidate_rows[row[0]] = row[1:]

                    project = as_text(
                        first_value(record, FIELD_ALIASES["project"])
                    )
                    function_hash = as_text(
                        first_value(record, FIELD_ALIASES["function_hash"])
                    )
                    dataset_idx = as_text(record.get("idx"))
                    current_shingles = unpack_shingles(shingle_blob)
                    current_shingle_count = len(current_shingles)

                    for row in candidate_rows.values():
                        (
                            old_partition,
                            old_number,
                            old_idx,
                            old_project,
                            old_function_hash,
                            old_signature_hex,
                            old_shingle_blob,
                        ) = row
                        if old_partition == partition_name:
                            continue
                        pair = pair_name(old_partition, partition_name)
                        candidate_pairs_checked[pair] += 1
                        distance = hamming_distance(
                            signature, int(old_signature_hex, 16)
                        )
                        if distance > max_hamming_distance:
                            continue
                        simhash_hits[pair] += 1
                        old_shingle_count = len(old_shingle_blob) // 8
                        if (
                            not current_shingle_count
                            or not old_shingle_count
                            or min(current_shingle_count, old_shingle_count)
                            / max(current_shingle_count, old_shingle_count)
                            < jaccard_threshold
                        ):
                            size_bound_rejects[pair] += 1
                            continue
                        similarity = jaccard(
                            current_shingles,
                            unpack_shingles(old_shingle_blob),
                        )
                        histograms[pair][histogram_bin(similarity)] += 1
                        if similarity < jaccard_threshold:
                            continue
                        verified_pairs[pair] += 1
                        if len(samples[pair]) < sample_limit:
                            samples[pair].append(
                                {
                                    "left_partition": old_partition,
                                    "left_record_number": old_number,
                                    "left_idx": old_idx,
                                    "left_project": old_project,
                                    "left_func_hash": old_function_hash,
                                    "right_partition": partition_name,
                                    "right_record_number": record_number,
                                    "right_idx": dataset_idx,
                                    "right_project": project,
                                    "right_func_hash": function_hash,
                                    "hamming_distance": distance,
                                    "token_shingle_jaccard": round(similarity, 6),
                                    "verified_token_count": verified_token_count,
                                }
                            )

                    record_key = next_record_key
                    next_record_key += 1
                    connection.execute(
                        """
                        INSERT INTO records (
                            record_key, partition_name, record_number,
                            dataset_idx, project, function_hash,
                            signature_hex, shingle_blob
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            record_key,
                            partition_name,
                            record_number,
                            dataset_idx,
                            project,
                            function_hash,
                            current_signature_hex,
                            shingle_blob,
                        ),
                    )
                    for band, bucket in band_buckets:
                        bucket_key = (band, bucket)
                        if bucket_counts[bucket_key] >= bucket_cap:
                            continue
                        connection.execute(
                            "INSERT INTO band_index (band, bucket, record_key) VALUES (?, ?, ?)",
                            (band, bucket, record_key),
                        )
                        bucket_counts[bucket_key] += 1

                    if records_seen[partition_name] % 5000 == 0:
                        connection.commit()
                        print(
                            f"{partition_name}: {records_seen[partition_name]} records",
                            file=sys.stderr,
                            flush=True,
                        )
            connection.commit()
    finally:
        connection.close()

    return {
        "status": "complete",
        "method": {
            "candidate_generator": "64-bit token SimHash with four 16-bit bands",
            "minimum_tokens": min_tokens,
            "maximum_simhash_tokens": max_simhash_tokens,
            "verification": "token 5-gram Jaccard similarity over deterministic sampled tokens",
            "maximum_verification_tokens": max_verify_tokens,
            "maximum_hamming_distance": max_hamming_distance,
            "jaccard_threshold": jaccard_threshold,
            "jaccard_size_bound": "pairs below the threshold's shingle-cardinality upper bound are rejected before blob unpacking",
            "bucket_cap": bucket_cap,
            "scope": "cross-partition candidates only",
            "interpretation": "verified candidates are stronger triage signals, not proof of semantic equivalence",
        },
        "partitions": {
            name: {
                "path": str(path),
                "records_seen": records_seen[name],
                "eligible_records": eligible_records[name],
                "skipped_short_or_missing_code": skipped_records[name],
                "invalid_records": invalid_records[name],
            }
            for name, path in partitions
        },
        "total_records_seen": sum(records_seen.values()),
        "candidate_pairs_checked": dict(candidate_pairs_checked),
        "simhash_hits": dict(simhash_hits),
        "verified_pairs": dict(verified_pairs),
        "size_bound_rejects": dict(size_bound_rejects),
        "jaccard_histograms": {pair: dict(counts) for pair, counts in histograms.items()},
        "sample_pairs": dict(samples),
        "elapsed_seconds": round(time.time() - started, 3),
        "temporary_database": str(database_path),
    }


def parse_partition(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("partition must use NAME=PATH")
    name, raw_path = value.split("=", 1)
    path = Path(raw_path).expanduser()
    if not name or not path.is_file():
        raise argparse.ArgumentTypeError(f"invalid partition: {value}")
    return name, path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--partition", action="append", required=True, metavar="NAME=PATH", type=parse_partition)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(gettempdir()) / "primevul_near_duplicate_verify.sqlite3",
    )
    parser.add_argument("--sample-limit", type=int, default=100)
    parser.add_argument("--bucket-cap", type=int, default=256)
    parser.add_argument("--min-tokens", type=int, default=20)
    parser.add_argument("--max-simhash-tokens", type=int, default=256)
    parser.add_argument(
        "--max-verify-tokens",
        type=int,
        default=4096,
        help="deterministic verification-token cap; use 0 for all tokens",
    )
    parser.add_argument("--max-hamming-distance", type=int, default=8)
    parser.add_argument("--jaccard-threshold", type=float, default=0.8)
    args = parser.parse_args()

    if len(args.partition) != 3:
        parser.error("exactly three partitions are required")
    if args.sample_limit < 0 or args.bucket_cap < 1:
        parser.error("sample-limit must be nonnegative and bucket-cap must be positive")
    if args.min_tokens < 1 or args.max_simhash_tokens < args.min_tokens:
        parser.error("token limits must be positive and max-simhash-tokens >= min-tokens")
    if args.max_verify_tokens < 0:
        parser.error("max-verify-tokens must be nonnegative")
    if not 0 <= args.max_hamming_distance <= 64:
        parser.error("max-hamming-distance must be between 0 and 64")
    if not 0.0 <= args.jaccard_threshold <= 1.0:
        parser.error("jaccard-threshold must be between 0 and 1")
    names = [name for name, _ in args.partition]
    if len(set(names)) != len(names):
        parser.error("partition names must be unique")

    max_verify_tokens = args.max_verify_tokens or None
    report = scan(
        args.partition,
        args.database,
        args.sample_limit,
        args.bucket_cap,
        args.min_tokens,
        args.max_simhash_tokens,
        max_verify_tokens,
        args.max_hamming_distance,
        args.jaccard_threshold,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

