#!/usr/bin/env python3
"""Memory-bounded approximate near-duplicate scan for PrimeVul JSONL files.

The scan is deliberately separate from the full partition audit. It stores the
SimHash band index in SQLite so the Python process does not retain a large
object-heavy candidate index alongside all audit statistics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from tempfile import gettempdir
from typing import Any


TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)
BYTE_CONTRIBUTIONS = tuple(
    tuple(1 if (value >> bit) & 1 else -1 for bit in range(8))
    for value in range(256)
)
FIELD_ALIASES = {
    "code": ("func", "function", "code", "source_code"),
    "project": ("project", "repo", "repository"),
    "function_hash": ("func_hash", "function_hash"),
}


def first_value(record: dict[str, Any], aliases: tuple[str, ...]) -> Any:
    for name in aliases:
        if name in record:
            return record[name]
    return None


def as_text(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    return str(value)


class SimHasher:
    def __init__(self) -> None:
        self._token_hashes: dict[str, int] = {}

    def signature(self, code: str, max_tokens: int) -> tuple[int, int, int]:
        tokens = TOKEN_RE.findall(code)
        original_token_count = len(tokens)
        if len(tokens) > max_tokens:
            stride = len(tokens) / max_tokens
            tokens = [tokens[int(index * stride)] for index in range(max_tokens)]
        accumulators = [0] * 64
        for token in tokens:
            token_hash = self._token_hashes.get(token)
            if token_hash is None:
                token_hash = int.from_bytes(
                    hashlib.blake2b(
                        token.encode("utf-8"), digest_size=8
                    ).digest(),
                    "big",
                )
                self._token_hashes[token] = token_hash
            # Updating eight bytes instead of iterating over 64 individual
            # bits keeps the scan practical for the full PrimeVul corpus.
            for byte_index in range(8):
                byte_contributions = BYTE_CONTRIBUTIONS[
                    (token_hash >> (byte_index * 8)) & 0xFF
                ]
                offset = byte_index * 8
                for bit, contribution in enumerate(byte_contributions):
                    accumulators[offset + bit] += contribution
        signature = 0
        for bit, value in enumerate(accumulators):
            if value >= 0:
                signature |= 1 << bit
        return signature, original_token_count, len(tokens)


def hamming_distance(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def pair_name(left: str, right: str) -> str:
    return "__".join(sorted((left, right)))


@dataclass(frozen=True)
class Partition:
    name: str
    path: Path


def initialize_database(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA journal_mode = OFF")
    connection.execute("PRAGMA synchronous = OFF")
    connection.execute("PRAGMA temp_store = MEMORY")
    connection.execute("PRAGMA cache_size = -65536")
    connection.execute(
        """
        CREATE TABLE band_index (
            band INTEGER NOT NULL,
            bucket INTEGER NOT NULL,
            partition_name TEXT NOT NULL,
            record_number INTEGER NOT NULL,
            dataset_idx TEXT,
            signature_hex TEXT NOT NULL,
            project TEXT,
            function_hash TEXT
        )
        """
    )
    connection.execute(
        "CREATE INDEX band_index_lookup ON band_index (band, bucket)"
    )


def scan(
    partitions: list[Partition],
    database_path: Path,
    sample_limit: int,
    bucket_cap: int,
    min_tokens: int,
    max_tokens: int,
    max_hamming_distance: int,
) -> dict[str, Any]:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    if database_path.exists():
        database_path.unlink()

    hasher = SimHasher()
    bucket_counts: Counter[tuple[int, int]] = Counter()
    records_seen: Counter[str] = Counter()
    eligible_records: Counter[str] = Counter()
    skipped_short: Counter[str] = Counter()
    invalid_records: Counter[str] = Counter()
    candidate_pairs_checked: Counter[str] = Counter()
    near_duplicate_candidates: Counter[str] = Counter()
    samples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    started = time.time()

    connection = sqlite3.connect(str(database_path))
    try:
        initialize_database(connection)

        for partition in partitions:
            print(f"Scanning {partition.name}: {partition.path}", file=sys.stderr)
            insert_rows: list[tuple[Any, ...]] = []
            with partition.path.open(
                "r", encoding="utf-8", errors="replace"
            ) as handle:
                for record_number, line in enumerate(handle, start=1):
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        invalid_records[partition.name] += 1
                        continue
                    if not isinstance(record, dict):
                        invalid_records[partition.name] += 1
                        continue

                    records_seen[partition.name] += 1
                    code = as_text(first_value(record, FIELD_ALIASES["code"]))
                    if not code:
                        skipped_short[partition.name] += 1
                        continue
                    signature, token_count, _hashed_token_count = hasher.signature(
                        code, max_tokens
                    )
                    if token_count < min_tokens:
                        skipped_short[partition.name] += 1
                        continue
                    eligible_records[partition.name] += 1

                    candidate_rows: dict[int, tuple[Any, ...]] = {}
                    band_buckets = [
                        (band, (signature >> (band * 16)) & 0xFFFF)
                        for band in range(4)
                    ]
                    conditions = " OR ".join(
                        "(band = ? AND bucket = ?)" for _ in band_buckets
                    )
                    query_params = [value for pair in band_buckets for value in pair]
                    rows = connection.execute(
                        f"""
                        SELECT rowid, partition_name, record_number,
                               dataset_idx, signature_hex, project,
                               function_hash
                        FROM band_index
                        WHERE {conditions}
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
                    current_signature_hex = f"{signature:016x}"

                    for row in candidate_rows.values():
                        if row[0] == partition.name:
                            continue
                        old_partition, old_number, old_idx, old_signature_hex, old_project, old_function_hash = row
                        pair = pair_name(old_partition, partition.name)
                        candidate_pairs_checked[pair] += 1
                        distance = hamming_distance(
                            int(current_signature_hex, 16),
                            int(old_signature_hex, 16),
                        )
                        if distance > max_hamming_distance:
                            continue
                        near_duplicate_candidates[pair] += 1
                        if len(samples[pair]) < sample_limit:
                            samples[pair].append(
                                {
                                    "left_partition": old_partition,
                                    "left_record_number": old_number,
                                    "left_idx": old_idx,
                                    "left_project": old_project,
                                    "left_func_hash": old_function_hash,
                                    "right_partition": partition.name,
                                    "right_record_number": record_number,
                                    "right_idx": dataset_idx,
                                    "right_project": project,
                                    "right_func_hash": function_hash,
                                    "hamming_distance": distance,
                                }
                            )

                    for band in range(4):
                        bucket = (signature >> (band * 16)) & 0xFFFF
                        bucket_key = (band, bucket)
                        if bucket_counts[bucket_key] >= bucket_cap:
                            continue
                        insert_rows.append(
                            (
                                band,
                                bucket,
                                partition.name,
                                record_number,
                                dataset_idx,
                                current_signature_hex,
                                project,
                                function_hash,
                            )
                        )
                        bucket_counts[bucket_key] += 1

                    if len(insert_rows) >= 5000:
                        connection.executemany(
                            """
                            INSERT INTO band_index (
                                band, bucket, partition_name, record_number,
                                dataset_idx, signature_hex, project,
                                function_hash
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            insert_rows,
                        )
                        connection.commit()
                        insert_rows.clear()

            if insert_rows:
                connection.executemany(
                    """
                    INSERT INTO band_index (
                        band, bucket, partition_name, record_number,
                        dataset_idx, signature_hex, project, function_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    insert_rows,
                )
                connection.commit()

    finally:
        connection.close()

    total_records = sum(records_seen.values())
    report = {
        "status": "complete",
        "method": {
            "algorithm": "64-bit token SimHash",
            "bands": 4,
            "bits_per_band": 16,
            "minimum_tokens": min_tokens,
            "maximum_tokens_hashed_per_function": max_tokens,
            "maximum_hamming_distance": max_hamming_distance,
            "bucket_cap": bucket_cap,
            "scope": "cross-partition candidates only",
            "interpretation": "approximate triage; candidates are not confirmed semantic duplicates",
        },
        "partitions": {
            name: {
                "path": str(partition.path),
                "records_seen": records_seen[name],
                "eligible_records": eligible_records[name],
                "skipped_short_or_missing_code": skipped_short[name],
                "invalid_records": invalid_records[name],
            }
            for name, partition in ((p.name, p) for p in partitions)
        },
        "total_records_seen": total_records,
        "candidate_pairs_checked": dict(candidate_pairs_checked),
        "near_duplicate_candidates": dict(near_duplicate_candidates),
        "sample_pairs": dict(samples),
        "elapsed_seconds": round(time.time() - started, 3),
        "temporary_database": str(database_path),
    }
    return report


def parse_partition(value: str) -> Partition:
    if "=" not in value:
        raise argparse.ArgumentTypeError("partition must use NAME=PATH")
    name, raw_path = value.split("=", 1)
    path = Path(raw_path).expanduser()
    if not name or not path.is_file():
        raise argparse.ArgumentTypeError(f"invalid partition: {value}")
    return Partition(name, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--partition",
        action="append",
        required=True,
        type=parse_partition,
        metavar="NAME=PATH",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(gettempdir()) / "primevul_near_duplicate_scan.sqlite3",
    )
    parser.add_argument("--sample-limit", type=int, default=100)
    parser.add_argument("--bucket-cap", type=int, default=256)
    parser.add_argument("--min-tokens", type=int, default=20)
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=256,
        help="deterministic evenly spaced token cap used for SimHash features",
    )
    parser.add_argument("--max-hamming-distance", type=int, default=8)
    args = parser.parse_args()

    if len(args.partition) != 3:
        parser.error("exactly three partitions are required")
    if (
        args.sample_limit < 0
        or args.bucket_cap < 1
        or args.min_tokens < 1
        or args.max_tokens < args.min_tokens
    ):
        parser.error(
            "sample-limit must be nonnegative; bucket/min/max token limits must be positive and max-tokens must be >= min-tokens"
        )
    if not 0 <= args.max_hamming_distance <= 64:
        parser.error("max-hamming-distance must be between 0 and 64")
    names = [partition.name for partition in args.partition]
    if len(set(names)) != len(names):
        parser.error("partition names must be unique")

    report = scan(
        args.partition,
        args.database,
        args.sample_limit,
        args.bucket_cap,
        args.min_tokens,
        args.max_tokens,
        args.max_hamming_distance,
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

