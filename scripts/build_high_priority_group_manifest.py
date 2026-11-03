#!/usr/bin/env python3
"""Build a non-destructive connected-component manifest for flagged pairs."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


class UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def add(self, item: str) -> None:
        self.parent.setdefault(item, item)

    def find(self, item: str) -> str:
        parent = self.parent[item]
        if parent != item:
            self.parent[item] = self.find(parent)
        return self.parent[item]

    def union(self, left: str, right: str) -> None:
        self.add(left)
        self.add(right)
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def node(partition: str, record_number: int) -> str:
    return f"{partition}:{record_number}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.input.read_text(encoding="utf-8"))
    pairs = [pair for pair in report["pairs"] if pair["review_priority"] == "high"]
    uf = UnionFind()
    pair_by_root: dict[str, list[str]] = defaultdict(list)
    for pair in pairs:
        left = node(pair["left_partition"], pair["left_record_number"])
        right = node(pair["right_partition"], pair["right_record_number"])
        uf.union(left, right)

    members: dict[str, list[str]] = defaultdict(list)
    for item in uf.parent:
        members[uf.find(item)].append(item)
    for pair in pairs:
        left = node(pair["left_partition"], pair["left_record_number"])
        pair_by_root[uf.find(left)].append(pair["pair_key"])

    components: list[dict[str, Any]] = []
    for root, items in members.items():
        partitions = Counter(item.split(":", 1)[0] for item in items)
        components.append(
            {
                "component_id": root,
                "record_count": len(items),
                "records_by_partition": dict(sorted(partitions.items())),
                "records": sorted(items),
                "pair_count": len(pair_by_root.get(root, [])),
                "pair_keys": sorted(pair_by_root.get(root, [])),
            }
        )
    components.sort(key=lambda item: (-item["record_count"], item["component_id"]))

    affected = Counter(item.split(":", 1)[0] for item in uf.parent)
    result = {
        "status": "complete",
        "source_report": str(args.input),
        "method": {
            "scope": "verified candidates with review_priority=high",
            "component_rule": "union records connected by a high-priority pair",
            "interpretation": "manifest is for review/grouped-split construction; it does not authorize deletion or relabeling",
        },
        "counts": {
            "high_priority_pairs": len(pairs),
            "affected_records_by_partition": dict(sorted(affected.items())),
            "connected_components": len(components),
            "largest_component_records": components[0]["record_count"] if components else 0,
        },
        "components": components,
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

