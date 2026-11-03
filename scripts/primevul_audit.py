#!/usr/bin/env python3
"""Audit supplied PrimeVul JSONL partitions without changing them.

The audit is intentionally dependency-free so it can run before the experiment
environment is frozen. It reports file hashes, record/schema statistics,
partition overlap, and exact-code duplicate diagnostics. An optional bounded
SimHash scan reports approximate cross-partition near-duplicate candidates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


DEFAULT_FIELDS = {
    "code": ("func", "function", "code", "source_code"),
    "label": ("target", "label", "y", "vulnerable", "is_vulnerable"),
    "project": ("project", "repo", "repository"),
    "commit": ("commit_id", "commit", "commit_hash"),
    "file": ("file_hash", "file_id", "filename", "file"),
    "function_hash": ("func_hash", "function_hash"),
    "cwe": ("cwe", "cwe_id", "weakness", "weakness_id"),
    "cve": ("cve", "cve_id"),
}

TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)
WHITESPACE_RE = re.compile(r"\s+")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def first_value(record: dict[str, Any], names: Iterable[str]) -> Any:
    for name in names:
        if name in record:
            return record[name]
    return None


def present(value: Any) -> bool:
    return value is not None and value != ""


def display_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    return str(value)


def canonical_code(code: str) -> str:
    # This is deliberately conservative: it removes formatting-only
    # whitespace but does not strip comments or literals that may be
    # semantically relevant.
    return WHITESPACE_RE.sub(" ", code).strip()


def code_metrics(code: str) -> tuple[int, int, str, str]:
    tokens = TOKEN_RE.findall(code)
    canonical = canonical_code(code)
    raw_hash = hashlib.sha256(code.encode("utf-8", errors="replace")).hexdigest()
    canonical_hash = hashlib.sha256(
        canonical.encode("utf-8", errors="replace")
    ).hexdigest()
    return len(code), len(tokens), raw_hash, canonical_hash


def simhash(code: str) -> int:
    """Return a 64-bit token SimHash for approximate duplicate triage."""
    tokens = TOKEN_RE.findall(code)
    if not tokens:
        return 0
    accumulators = [0] * 64
    for token in tokens:
        token_hash = int.from_bytes(
            hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest(),
            "big",
        )
        for bit in range(64):
            accumulators[bit] += 1 if (token_hash >> bit) & 1 else -1
    result = 0
    for bit, value in enumerate(accumulators):
        if value >= 0:
            result |= 1 << bit
    return result


def hamming_distance(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def percentile(values: list[int], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * p
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return float(ordered[lower])
    fraction = index - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def distribution(values: list[int]) -> dict[str, float | int | None]:
    return {
        "min": min(values) if values else None,
        "p25": percentile(values, 0.25),
        "median": percentile(values, 0.50),
        "p75": percentile(values, 0.75),
        "p95": percentile(values, 0.95),
        "max": max(values) if values else None,
        "mean": (sum(values) / len(values)) if values else None,
    }


def pairwise_intersections(values: dict[str, set[str]]) -> dict[str, dict[str, int]]:
    names = list(values)
    result: dict[str, dict[str, int]] = {}
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            result[f"{left}__{right}"] = {
                "intersection": len(values[left] & values[right]),
                "left_only": len(values[left] - values[right]),
                "right_only": len(values[right] - values[left]),
            }
    return result


@dataclass
class PartitionSummary:
    name: str
    path: str
    file_sha256: str
    records: int = 0
    invalid_json_lines: int = 0
    blank_lines: int = 0
    keys: set[str] = field(default_factory=set)
    missing: Counter[str] = field(default_factory=Counter)
    labels: Counter[str] = field(default_factory=Counter)
    projects: Counter[str] = field(default_factory=Counter)
    cwes: Counter[str] = field(default_factory=Counter)
    cves: Counter[str] = field(default_factory=Counter)
    code_lengths: list[int] = field(default_factory=list)
    token_lengths: list[int] = field(default_factory=list)
    identity_values: dict[str, set[str]] = field(
        default_factory=lambda: defaultdict(set)
    )
    raw_code_hashes: set[str] = field(default_factory=set)
    canonical_code_hashes: set[str] = field(default_factory=set)
    schema_counts: Counter[str] = field(default_factory=Counter)

    def to_json(self, top_n: int) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "file_sha256": self.file_sha256,
            "records": self.records,
            "invalid_json_lines": self.invalid_json_lines,
            "blank_lines": self.blank_lines,
            "field_presence": {
                field_name: {
                    "present": self.records - self.missing[field_name],
                    "missing": self.missing[field_name],
                    "missing_rate": self.missing[field_name] / self.records
                    if self.records
                    else None,
                }
                for field_name in DEFAULT_FIELDS
            },
            "schema": {
                "unique_keys": len(self.keys),
                "key_presence_counts": dict(self.schema_counts),
            },
            "labels": dict(self.labels),
            "top_projects": self.projects.most_common(top_n),
            "top_cwes": self.cwes.most_common(top_n),
            "top_cves": self.cves.most_common(top_n),
            "code_length_characters": distribution(self.code_lengths),
            "code_length_tokens_approx": distribution(self.token_lengths),
            "unique_raw_code_hashes": len(self.raw_code_hashes),
            "unique_canonical_code_hashes": len(self.canonical_code_hashes),
        }


def audit_partition(name: str, path: Path) -> PartitionSummary:
    summary = PartitionSummary(name, str(path), sha256_file(path))
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                summary.blank_lines += 1
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                summary.invalid_json_lines += 1
                continue
            if not isinstance(record, dict):
                summary.invalid_json_lines += 1
                continue

            summary.records += 1
            summary.keys.update(record.keys())
            for key in record:
                summary.schema_counts[key] += 1

            values = {
                field_name: first_value(record, aliases)
                for field_name, aliases in DEFAULT_FIELDS.items()
            }
            for field_name, value in values.items():
                if not present(value):
                    summary.missing[field_name] += 1

            if present(values["label"]):
                summary.labels[display_value(values["label"])] += 1
            if present(values["project"]):
                summary.projects[display_value(values["project"])] += 1
            if present(values["cwe"]):
                summary.cwes[display_value(values["cwe"])] += 1
            if present(values["cve"]):
                summary.cves[display_value(values["cve"])] += 1

            code = values["code"]
            if present(code):
                code_text = display_value(code)
                char_count, token_count, raw_hash, canonical_hash = code_metrics(
                    code_text
                )
                summary.code_lengths.append(char_count)
                summary.token_lengths.append(token_count)
                summary.raw_code_hashes.add(raw_hash)
                summary.canonical_code_hashes.add(canonical_hash)

            for identity_name in ("project", "commit", "file", "function_hash"):
                value = values[identity_name]
                if present(value):
                    summary.identity_values[identity_name].add(display_value(value))

    return summary


def build_report(
    summaries: list[PartitionSummary], top_n: int, near_duplicate_note: str | None
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "audit": {
            "tool": "work/primevul_audit.py",
            "purpose": "Pre-experiment PrimeVul partition and leakage audit",
            "near_duplicate_mode": near_duplicate_note or "not requested",
        },
        "partitions": [summary.to_json(top_n) for summary in summaries],
        "overlap": {},
        "warnings": [],
    }

    for identity_name in ("project", "commit", "file", "function_hash"):
        values = {
            summary.name: summary.identity_values[identity_name]
            for summary in summaries
        }
        report["overlap"][identity_name] = pairwise_intersections(values)

    for hash_name, attr in (
        ("raw_code_sha256", "raw_code_hashes"),
        ("canonical_code_sha256", "canonical_code_hashes"),
    ):
        values = {summary.name: getattr(summary, attr) for summary in summaries}
        report["overlap"][hash_name] = pairwise_intersections(values)

    for summary in summaries:
        if summary.invalid_json_lines:
            report["warnings"].append(
                f"{summary.name}: {summary.invalid_json_lines} invalid JSON record(s)"
            )
        if summary.blank_lines:
            report["warnings"].append(
                f"{summary.name}: {summary.blank_lines} blank line(s)"
            )
        if not summary.identity_values["function_hash"]:
            report["warnings"].append(
                f"{summary.name}: no function_hash values were detected"
            )
        if not summary.identity_values["file"]:
            report["warnings"].append(
                f"{summary.name}: no file identity values were detected"
            )

    return report


def approximate_near_duplicates(
    partitions: list[tuple[str, Path]],
    max_bucket_size: int = 256,
    max_samples: int = 100,
    max_hamming_distance: int = 8,
) -> dict[str, Any]:
    """Find bounded cross-partition near-duplicate candidates.

    SimHash is used only as a scalable candidate generator. A hit is a
    triage signal, not proof that two functions are semantically equivalent.
    Small functions are excluded because their signatures are too collision
    prone. The scan keeps at most ``max_bucket_size`` references per band.
    """
    buckets: dict[tuple[int, int], list[tuple[str, int, str, str]]] = defaultdict(list)
    checked = 0
    matches = 0
    samples: list[dict[str, Any]] = []

    for partition_name, path in partitions:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for record_number, line in enumerate(handle, start=1):
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict):
                    continue
                code_value = first_value(record, DEFAULT_FIELDS["code"])
                if not present(code_value):
                    continue
                code = display_value(code_value)
                token_count = len(TOKEN_RE.findall(code))
                if token_count < 20:
                    continue
                signature = simhash(code)
                candidates: set[tuple[str, int, str, str]] = set()
                for band in range(4):
                    key = (band, (signature >> (band * 16)) & 0xFFFF)
                    candidates.update(buckets.get(key, ()))

                for old_partition, old_number, old_hash, old_project in candidates:
                    if old_partition == partition_name:
                        continue
                    checked += 1
                    distance = hamming_distance(signature, int(old_hash, 16))
                    if distance > max_hamming_distance:
                        continue
                    matches += 1
                    if len(samples) < max_samples:
                        project = first_value(record, DEFAULT_FIELDS["project"])
                        samples.append(
                            {
                                "partition": old_partition,
                                "record_number": old_number,
                                "other_partition": partition_name,
                                "other_record_number": record_number,
                                "hamming_distance": distance,
                                "project": old_project,
                                "other_project": display_value(project)
                                if present(project)
                                else None,
                            }
                        )

                project_value = first_value(record, DEFAULT_FIELDS["project"])
                project = display_value(project_value) if present(project_value) else ""
                signature_hex = f"{signature:016x}"
                for band in range(4):
                    key = (band, (signature >> (band * 16)) & 0xFFFF)
                    bucket = buckets[key]
                    if len(bucket) < max_bucket_size:
                        bucket.append((partition_name, record_number, signature_hex, project))

    return {
        "method": "64-bit token SimHash with four 16-bit bands",
        "interpretation": "approximate cross-partition triage; candidates require manual or stronger similarity verification",
        "minimum_token_count": 20,
        "max_hamming_distance": max_hamming_distance,
        "candidate_pairs_checked": checked,
        "near_duplicate_candidates": matches,
        "sample_pairs": samples,
    }


def parse_partition(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("partition must use NAME=PATH")
    name, raw_path = value.split("=", 1)
    if not name or not raw_path:
        raise argparse.ArgumentTypeError("partition must use NAME=PATH")
    path = Path(raw_path).expanduser()
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"file does not exist: {path}")
    return name, path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--partition",
        action="append",
        type=parse_partition,
        metavar="NAME=PATH",
        help="partition to audit; may be repeated (default names are train/valid/test)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("primevul_audit.json"),
        help="JSON report path (default: primevul_audit.json)",
    )
    parser.add_argument("--top-n", type=int, default=25)
    parser.add_argument(
        "--near-duplicates",
        action="store_true",
        help="run a bounded approximate cross-partition SimHash candidate scan",
    )
    args = parser.parse_args()

    partitions = args.partition
    if not partitions:
        partitions = []
        for name in ("train", "valid", "test"):
            path = Path(f"primevul_{name}.jsonl")
            if path.is_file():
                partitions.append((name, path))
        if not partitions:
            parser.error(
                "no default primevul_train/valid/test JSONL files found; use --partition NAME=PATH"
            )

    if len({name for name, _ in partitions}) != len(partitions):
        parser.error("partition names must be unique")
    if args.top_n < 1:
        parser.error("--top-n must be positive")

    summaries: list[PartitionSummary] = []
    for name, path in partitions:
        print(f"Auditing {name}: {path}", file=sys.stderr)
        summaries.append(audit_partition(name, path))

    note = "bounded SimHash candidate scan" if args.near_duplicates else None
    report = build_report(summaries, args.top_n, note)
    if args.near_duplicates:
        report["near_duplicates"] = approximate_near_duplicates(partitions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

