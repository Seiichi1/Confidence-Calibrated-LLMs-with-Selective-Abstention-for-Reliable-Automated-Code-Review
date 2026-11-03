#!/usr/bin/env python3
"""Run a conservative Semgrep corroboration scan over retained PrimeVul rows.

The input LLM JSONL identifies the exact retained records to scan. The raw
PrimeVul JSONL supplies the corresponding function bodies by ``idx``. Each
function is written to a temporary C file outside the project directory, then
one Semgrep process scans the temporary batch. Raw dataset files are never
modified.

This is a corroboration baseline, not a semantic oracle. A Semgrep finding is
positive evidence for review; no finding is treated as neutral rather than as
proof that the function is safe. The default relation labels are deliberately
conservative:

* AGREE: parsed LLM ``YES`` and at least one static finding;
* DISAGREE: parsed LLM ``NO`` and at least one static finding;
* NEUTRAL: no static finding, unparseable LLM output, or unavailable scan.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


def load_llm_rows(path: Path, limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if not isinstance(row.get("record"), dict):
                continue
            rows.append(row)
            if limit > 0 and len(rows) >= limit:
                break
    return rows


def load_functions(path: Path, wanted_indices: set[Any]) -> dict[Any, str]:
    functions: dict[Any, str] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            idx = record.get("idx")
            if idx in wanted_indices:
                functions[idx] = str(record.get("func") or "")
                if len(functions) == len(wanted_indices):
                    break
    return functions


def run_semgrep(
    semgrep: str,
    rules: Path,
    source_dir: Path,
) -> tuple[dict[str, list[dict[str, Any]]], str]:
    command = [
        semgrep,
        "scan",
        "--config",
        str(rules),
        "--json",
        "--no-git-ignore",
        str(source_dir),
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode not in (0, 1):
        raise RuntimeError(
            "Semgrep failed with exit code "
            f"{completed.returncode}: {completed.stderr[-4000:]}"
        )
    payload = json.loads(completed.stdout or "{}")
    findings: dict[str, list[dict[str, Any]]] = {}
    for result in payload.get("results", []):
        path = str(Path(result.get("path", "")).name)
        findings.setdefault(path, []).append(
            {
                "check_id": result.get("check_id"),
                "start_line": result.get("start", {}).get("line"),
                "end_line": result.get("end", {}).get("line"),
                "message": result.get("extra", {}).get("message"),
                "severity": result.get("extra", {}).get("severity"),
            }
        )
    version = "unknown"
    try:
        version_run = subprocess.run(
            [semgrep, "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
        version = version_run.stdout.strip() or version_run.stderr.strip()
    except (OSError, subprocess.CalledProcessError):
        pass
    return findings, version


def relation(prediction: Any, has_finding: bool) -> str:
    if has_finding and prediction == "YES":
        return "AGREE"
    if has_finding and prediction == "NO":
        return "DISAGREE"
    return "NEUTRAL"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Semgrep corroboration on PrimeVul LLM rows")
    parser.add_argument("--data", type=Path, required=True, help="raw PrimeVul JSONL partition")
    parser.add_argument("--llm-results", type=Path, required=True, help="Qwen JSONL output")
    parser.add_argument("--rules", type=Path, default=Path(__file__).with_name("semgrep_primevul_rules.yml"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--semgrep", default="semgrep")
    parser.add_argument("--limit", type=int, default=0, help="0 means all rows in the LLM output")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=512,
        help="temporary source files per Semgrep invocation; smaller batches avoid Windows hangs",
    )
    args = parser.parse_args()
    if args.batch_size <= 0:
        parser.error("--batch-size must be positive")

    semgrep_path = shutil.which(args.semgrep) or args.semgrep
    if not Path(semgrep_path).exists() and shutil.which(args.semgrep) is None:
        raise SystemExit(
            "Semgrep executable not found. Install Semgrep Community Edition, "
            "then rerun this command; no scan or output was produced."
        )
    if not args.rules.exists():
        raise SystemExit(f"Rules file not found: {args.rules}")

    llm_rows = load_llm_rows(args.llm_results, args.limit)
    wanted_indices = {row["record"].get("idx") for row in llm_rows}
    functions = load_functions(args.data, wanted_indices)
    missing_functions = sorted(wanted_indices - set(functions), key=str)
    if missing_functions:
        raise SystemExit(
            f"Could not find {len(missing_functions)} LLM record indices in the raw partition. "
            "Check that --data matches the LLM partition."
        )

    with tempfile.TemporaryDirectory(prefix="thesis_semgrep_primevul_") as temp_name:
        source_dir = Path(temp_name)
        file_by_record: dict[int, str] = {}
        files_by_name: dict[str, str] = {}
        for row in llm_rows:
            record_number = int(row["record_number"])
            filename = f"record_{record_number:08d}.c"
            files_by_name[filename] = functions[row["record"].get("idx")]
            file_by_record[record_number] = filename
        all_findings: dict[str, list[dict[str, Any]]] = {}
        semgrep_version = "unknown"
        filenames = sorted(files_by_name)
        batch_count = (len(filenames) + args.batch_size - 1) // args.batch_size
        for batch_index in range(batch_count):
            batch_dir = source_dir / f"batch_{batch_index:05d}"
            batch_dir.mkdir()
            batch_names = filenames[batch_index * args.batch_size : (batch_index + 1) * args.batch_size]
            for filename in batch_names:
                (batch_dir / filename).write_text(files_by_name[filename], encoding="utf-8")
            print(
                f"[semgrep] batch {batch_index + 1}/{batch_count} "
                f"({len(batch_names)} records)",
                flush=True,
            )
            batch_findings, semgrep_version = run_semgrep(semgrep_path, args.rules, batch_dir)
            all_findings.update(batch_findings)

    output_rows: list[dict[str, Any]] = []
    relation_counts: Counter[str] = Counter()
    static_counts: Counter[str] = Counter()
    for row in llm_rows:
        record_number = int(row["record_number"])
        file_name = file_by_record[record_number]
        batch_file_name = file_name
        # Findings are keyed by basename, so the batch directory is irrelevant
        # after each batch has been merged.
        file_findings = all_findings.get(batch_file_name, [])
        has_finding = bool(file_findings)
        prediction = row.get("prediction")
        status = relation(prediction, has_finding)
        relation_counts[status] += 1
        static_counts["YES" if has_finding else "NO_FINDING"] += 1
        output_rows.append(
            {
                "record_number": record_number,
                "idx": row["record"].get("idx"),
                "target": row["record"].get("target"),
                "llm_prediction": prediction,
                "static_label": "YES" if has_finding else "NO_FINDING",
                "corroboration_status": status,
                "findings": file_findings,
            }
        )

    target_counts = Counter(str(row["target"]) for row in output_rows)
    static_true_positive = sum(row["target"] == 1 and row["static_label"] == "YES" for row in output_rows)
    static_predicted_positive = sum(row["static_label"] == "YES" for row in output_rows)
    output = {
        "status": "complete",
        "method": {
            "analyzer": "Semgrep Community Edition/local rules",
            "semgrep_version": semgrep_version,
            "language_mode": "C/C++ syntax scan over isolated PrimeVul function snippets",
            "rules": str(args.rules),
            "batch_size": args.batch_size,
            "absence_of_finding": "neutral; not evidence of safety",
            "final_test_used": False,
            "temporary_source_directory": "outside project directory; removed after scan",
        },
        "counts": {
            "llm_rows_scanned": len(output_rows),
            "target_counts": dict(sorted(target_counts.items())),
            "static_label_counts": dict(sorted(static_counts.items())),
            "corroboration_status_counts": dict(sorted(relation_counts.items())),
            "static_findings": static_counts["YES"],
            "static_true_positives": static_true_positive,
            "static_positive_precision": static_true_positive / max(static_predicted_positive, 1),
            "static_positive_recall": static_true_positive / max(sum(row["target"] == 1 for row in output_rows), 1),
        },
        "rows": output_rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "complete", "output": str(args.output), "counts": output["counts"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

