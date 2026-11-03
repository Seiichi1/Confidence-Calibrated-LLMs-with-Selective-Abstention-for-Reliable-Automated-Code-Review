#!/usr/bin/env python3
"""Run a small deterministic smoke test with the pinned local Qwen coder."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from pathlib import Path
from typing import Any


MODEL_ID = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
MODEL_REVISION = "2e1fd39"
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
    data = manifest.get("partitions", {}).get(partition)
    if not data:
        raise ValueError(f"Partition {partition!r} not found in manifest")
    return set(data["kept_record_numbers"])


def load_sample_records(
    data_path: Path, retained: set[int], sample_count: int, seed: int
) -> list[tuple[int, dict[str, Any]]]:
    available: list[int] = []
    with data_path.open("r", encoding="utf-8", errors="replace") as handle:
        for record_number, line in enumerate(handle, start=1):
            if record_number in retained and line.strip():
                available.append(record_number)
    if not available:
        raise ValueError("No retained records were found in the data file")
    count = min(sample_count, len(available))
    selected = set(random.Random(seed).sample(available, count))
    records: list[tuple[int, dict[str, Any]]] = []
    with data_path.open("r", encoding="utf-8", errors="replace") as handle:
        for record_number, line in enumerate(handle, start=1):
            if record_number in selected and line.strip():
                records.append((record_number, json.loads(line)))
    return records


def load_model(dtype_name: str):
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as error:
        raise RuntimeError(
            "Install transformers and torch before running this script."
        ) from error

    dtype = None
    if dtype_name != "auto":
        dtype = getattr(torch, dtype_name)
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID, revision=MODEL_REVISION, trust_remote_code=False
    )
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
        torch_dtype=dtype,
        low_cpu_mem_usage=True,
        trust_remote_code=False,
    )
    model.eval()
    return torch, tokenizer, model


def run_one(torch, tokenizer, model, record: dict[str, Any], max_new_tokens: int) -> dict[str, Any]:
    messages = prompt_messages(record["func"])
    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_tensors="pt",
        return_dict=True,
    )
    device = next(model.parameters()).device
    inputs = inputs.to(device)
    with torch.inference_mode():
        generated = model.generate(
            **inputs,
            do_sample=False,
            max_new_tokens=max_new_tokens,
            return_dict_in_generate=True,
            output_scores=True,
        )
    input_length = inputs["input_ids"].shape[-1]
    output_ids = generated.sequences[0][input_length:]
    response = tokenizer.decode(output_ids, skip_special_tokens=True).strip()
    first_scores = generated.scores[0][0]
    probabilities = torch.softmax(first_scores.float(), dim=-1)
    values, indices = torch.topk(probabilities, k=min(5, probabilities.shape[-1]))
    top_tokens = [
        {
            "token_id": int(token_id),
            "token": tokenizer.decode([int(token_id)]),
            "probability": float(probability),
        }
        for probability, token_id in zip(values.tolist(), indices.tolist())
    ]
    return {
        "record": {
            "idx": record.get("idx"),
            "target": record.get("target"),
            "project": record.get("project"),
            "func_hash": record.get("func_hash"),
        },
        "response": response,
        "prediction": parse_prediction(response),
        "first_token_top5": top_tokens,
        "prompt_sha256": prompt_hash(record["func"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--partition", choices=("valid", "test"), default="valid")
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--max-new-tokens", type=int, default=16)
    parser.add_argument(
        "--dtype", choices=("auto", "float32", "float16", "bfloat16"), default="auto"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    retained = load_retained_numbers(args.manifest, args.partition)
    records = load_sample_records(args.data, retained, args.samples, args.seed)
    torch, tokenizer, model = load_model(args.dtype)
    results = []
    for number, record in records:
        print(f"Running record {number} (idx={record.get('idx')})", flush=True)
        result = run_one(torch, tokenizer, model, record, args.max_new_tokens)
        result["record_number"] = number
        results.append(result)

    output = {
        "status": "complete",
        "model": {
            "id": MODEL_ID,
            "revision": MODEL_REVISION,
            "dtype": args.dtype,
        },
        "run": {
            "partition": args.partition,
            "sample_count": len(results),
            "seed": args.seed,
            "max_new_tokens": args.max_new_tokens,
            "prompt_contract": "code-only YES/NO classification",
        },
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(results)} results to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

