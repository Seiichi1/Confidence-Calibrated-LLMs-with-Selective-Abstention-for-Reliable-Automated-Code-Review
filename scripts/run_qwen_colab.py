#!/usr/bin/env python3
"""Run the PrimeVul Qwen baseline from Google Colab.

The script is portable: ``--model`` may be a local Hugging Face model
directory in Colab or a Hugging Face repository ID.  It reads only retained
records from the leakage-controlled manifest and never edits the dataset.

For a smoke test, leave ``--limit`` at its default of 3.  For a complete
retained validation/test run, use ``--limit 0``.  Full runs stream JSONL
results to avoid retaining every model response in RAM.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import time
from pathlib import Path
from typing import Any, Iterator


DEFAULT_MODEL_ID = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
DEFAULT_REVISION = "2e1fd39"
SYSTEM_PROMPT = "You are a security expert that is good at static program analysis."
USER_TEMPLATE = """Please analyze the following code:
```
{func}
```
Please indicate your analysis result with one of the options:
(1) YES: A security vulnerability detected.
(2) NO: No security vulnerability.

Only reply with one of the options above. Do not include any further information.
"""
LABEL_RE = re.compile(r"\b(YES|NO)\b", re.IGNORECASE)


def prompt_messages(code: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_TEMPLATE.format(func=code)},
    ]


def prompt_hash(code: str) -> str:
    serialized = json.dumps(prompt_messages(code), sort_keys=True).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def parse_prediction(text: str) -> str | None:
    match = LABEL_RE.search(text or "")
    return match.group(1).upper() if match else None


def load_retained_numbers(manifest_path: Path, partition: str) -> set[int]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "complete":
        raise ValueError(f"Manifest is not complete: {manifest_path}")
    partition_data = manifest.get("partitions", {}).get(partition)
    if not partition_data:
        raise ValueError(f"Partition {partition!r} not found in manifest")
    return set(partition_data["kept_record_numbers"])


def iter_records(data_path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
    with data_path.open("r", encoding="utf-8", errors="replace") as handle:
        for record_number, line in enumerate(handle, start=1):
            if line.strip():
                yield record_number, json.loads(line)


def select_record_numbers(
    data_path: Path,
    retained: set[int],
    limit: int,
    seed: int,
) -> set[int] | None:
    """Return selected line numbers, or None to stream every retained record."""
    if limit == 0:
        return None
    available = [number for number, _ in iter_records(data_path) if number in retained]
    if not available:
        raise ValueError("No retained records were found in the data file")
    count = min(limit, len(available))
    return set(random.Random(seed).sample(available, count))


def resolve_dtype(torch: Any, dtype_name: str) -> Any:
    if dtype_name == "auto":
        return torch.float16 if torch.cuda.is_available() else torch.float32
    return getattr(torch, dtype_name)


def load_model(
    model_source: str,
    revision: str,
    dtype_name: str,
    local_files_only: bool,
    device_map_name: str,
):
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as error:
        raise RuntimeError(
            "Install dependencies first: pip install -U torch transformers "
            "accelerate safetensors"
        ) from error

    local_model = Path(model_source).expanduser().exists()
    load_kwargs: dict[str, Any] = {
        "trust_remote_code": False,
        "local_files_only": local_files_only or local_model,
    }
    if not local_model:
        load_kwargs["revision"] = revision

    tokenizer = AutoTokenizer.from_pretrained(model_source, **load_kwargs)
    if tokenizer.pad_token_id is None and tokenizer.eos_token_id is not None:
        tokenizer.pad_token = tokenizer.eos_token

    dtype = resolve_dtype(torch, dtype_name)
    model_kwargs = dict(load_kwargs)
    model_kwargs.update({"torch_dtype": dtype, "low_cpu_mem_usage": True})
    if device_map_name == "auto":
        model_kwargs["device_map"] = "auto"
    model = AutoModelForCausalLM.from_pretrained(model_source, **model_kwargs)
    if device_map_name == "cpu":
        model.to("cpu")
    model.eval()
    return torch, tokenizer, model, dtype


def model_input_device(model: Any, torch: Any):
    if hasattr(model, "get_input_embeddings"):
        embedding = model.get_input_embeddings()
        if embedding is not None:
            return embedding.weight.device
    return next(model.parameters()).device


def top_token_probabilities(torch: Any, tokenizer: Any, scores: Any) -> list[dict[str, Any]]:
    probabilities = torch.softmax(scores.float(), dim=-1)
    values, indices = torch.topk(probabilities, k=min(5, probabilities.shape[-1]))
    return [
        {
            "token_id": int(token_id),
            "token": tokenizer.decode([int(token_id)]),
            "probability": float(probability),
        }
        for probability, token_id in zip(values.tolist(), indices.tolist())
    ]


def run_one(
    torch: Any,
    tokenizer: Any,
    model: Any,
    record: dict[str, Any],
    max_new_tokens: int,
) -> dict[str, Any]:
    code = str(record.get("func", ""))
    messages = prompt_messages(code)
    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_tensors="pt",
        return_dict=True,
    )
    if hasattr(inputs, "to"):
        inputs = inputs.to(model_input_device(model, torch))

    with torch.inference_mode():
        generated = model.generate(
            **inputs,
            do_sample=False,
            max_new_tokens=max_new_tokens,
            return_dict_in_generate=True,
            output_scores=True,
            pad_token_id=tokenizer.pad_token_id,
        )

    input_length = inputs["input_ids"].shape[-1]
    output_ids = generated.sequences[0][input_length:]
    response = tokenizer.decode(output_ids, skip_special_tokens=True).strip()
    top5 = top_token_probabilities(torch, tokenizer, generated.scores[0][0])
    return {
        "record": {
            "idx": record.get("idx"),
            "target": record.get("target"),
            "project": record.get("project"),
            "func_hash": record.get("func_hash"),
        },
        "response": response,
        "prediction": parse_prediction(response),
        "first_token_top5": top5,
        "prompt_sha256": prompt_hash(code),
    }


def build_result_record(
    record_number: int,
    record: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    result["record_number"] = record_number
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the pinned Qwen PrimeVul baseline in Google Colab."
    )
    parser.add_argument("--data", type=Path, required=True, help="Raw partition JSONL")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--partition", choices=("valid", "test"), default="valid")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL_ID,
        help="Local model directory or Hugging Face model ID",
    )
    parser.add_argument("--revision", default=DEFAULT_REVISION)
    parser.add_argument(
        "--local-files-only",
        action="store_true",
        help="Do not contact Hugging Face; use local/cache files only",
    )
    parser.add_argument("--limit", type=int, default=3, help="3 for smoke test; 0 for all")
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--max-new-tokens", type=int, default=16)
    parser.add_argument(
        "--dtype", choices=("auto", "float32", "float16", "bfloat16"), default="auto"
    )
    parser.add_argument("--device-map", choices=("auto", "cpu"), default="auto")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--progress-every",
        type=int,
        default=10,
        help="Print progress every N records during a full run",
    )
    args = parser.parse_args()

    if args.limit < 0:
        parser.error("--limit must be non-negative; use 0 for all retained records")
    if args.progress_every < 1:
        parser.error("--progress-every must be positive")

    retained = load_retained_numbers(args.manifest, args.partition)
    selected = select_record_numbers(args.data, retained, args.limit, args.seed)
    torch, tokenizer, model, dtype = load_model(
        args.model,
        args.revision,
        args.dtype,
        args.local_files_only,
        args.device_map,
    )

    records = (
        (number, record)
        for number, record in iter_records(args.data)
        if number in retained and (selected is None or number in selected)
    )
    results: list[dict[str, Any]] = []
    processed = 0
    started = time.time()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    jsonl_mode = args.limit == 0

    if jsonl_mode:
        output_handle = args.output.open("w", encoding="utf-8")
    else:
        output_handle = None

    try:
        for record_number, record in records:
            processed += 1
            print(
                f"[{processed}] record {record_number} (idx={record.get('idx')})",
                flush=True,
            )
            result = build_result_record(
                record_number, record, run_one(torch, tokenizer, model, record, args.max_new_tokens)
            )
            if output_handle is not None:
                output_handle.write(json.dumps(result, ensure_ascii=False) + "\n")
                output_handle.flush()
            else:
                results.append(result)
            if args.limit == 0 and processed % args.progress_every == 0:
                elapsed = max(time.time() - started, 1e-9)
                print(f"  {processed} records; {processed / elapsed:.2f} records/s", flush=True)
    finally:
        if output_handle is not None:
            output_handle.close()

    expected = len(selected) if selected is not None else len(retained)
    if processed != expected:
        raise RuntimeError(f"Processed {processed} records, expected {expected}")

    run_info = {
        "partition": args.partition,
        "records_processed": processed,
        "retained_manifest_records": len(retained),
        "limit": args.limit,
        "seed": args.seed,
        "max_new_tokens": args.max_new_tokens,
        "prompt_contract": "code-only YES/NO classification",
        "manifest": str(args.manifest),
        "data": str(args.data),
        "output_format": "jsonl" if jsonl_mode else "json",
    }
    metadata = {
        "status": "complete",
        "model": {
            "source": args.model,
            "huggingface_id": DEFAULT_MODEL_ID if args.model == DEFAULT_MODEL_ID else None,
            "revision": None if Path(args.model).expanduser().exists() else args.revision,
            "dtype_requested": args.dtype,
            "dtype_loaded": str(dtype),
            "device_map": args.device_map,
        },
        "run": run_info,
    }

    if not jsonl_mode:
        payload = {**metadata, "results": results}
        args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    metadata_path = Path(str(args.output) + ".meta.json")
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Completed {processed} records")
    print(f"Results: {args.output}")
    print(f"Metadata: {metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

