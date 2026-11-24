"""Evaluate shared support retrieval and operator draft flow on synthetic tickets."""

import argparse
import asyncio
import hashlib
import json
import math
import tempfile
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.resolution.index import DEFAULT_K, Method, SupportIndex
from app.resolution.service import OperationStore, ResolutionService, configured_provider

DATA = Path(__file__).resolve().parents[1] / "support" / "evaluation"
KS = (1, DEFAULT_K)


class Example(BaseModel):
    id: str
    language: str
    ticket: str
    gold_sources: list[str]
    expected: str | None


def latency(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    return {
        "n": len(ordered), "p50_ms": round(ordered[math.ceil(len(ordered) * 0.50) - 1], 3),
        "p95_ms": round(ordered[math.ceil(len(ordered) * 0.95) - 1], 3),
    }


async def evaluate(path: Path, method: Method, examples: list[Example], mode: str,
                   db_path: Path) -> dict[str, Any]:
    index = SupportIndex(path, method)
    service = ResolutionService(index, OperationStore(db_path), configured_provider(mode))
    counts = {k: 0.0 for k in KS}
    failures: dict[int, list[dict[str, Any]]] = {k: [] for k in KS}
    retrieval_ms = []
    total_ms = []
    cases = []
    input_tokens = output_tokens = usage_count = answerable = unanswerable_review = 0
    for example in examples:
        ranked = [passage.id for passage in index.rank(example.ticket, max(KS))]
        gold = set(example.gold_sources)
        if gold:
            answerable += 1
            for k in KS:
                hits = gold.intersection(ranked[:k])
                counts[k] += len(hits) / len(gold)
                if hits != gold:
                    failures[k].append({"id": example.id, "expected": sorted(gold), "ranked": ranked[:k]})
        start = time.perf_counter()
        result = await service.suggest(example.ticket, "evaluation", example.id)
        total_ms.append((time.perf_counter() - start) * 1000)
        retrieval_ms.append(result.retrieval_ms)
        if not gold and result.status == "needs_review" and result.draft is None:
            unanswerable_review += 1
        if result.usage is not None:
            usage_count += 1
            input_tokens += result.usage.input_tokens
            output_tokens += result.usage.output_tokens
        cases.append({
            **example.model_dump(), "status": result.status, "reason": result.review_reason,
            "draft": result.draft, "cited_sources": [
                {"id": source.id, "text": next(p.text for p in index.passages if p.id == source.id)}
                for source in result.sources
            ],
            "human_judgment": None,
        })
    unanswerable = len(examples) - answerable
    return {
        "configuration": service.configuration,
        "n": len(examples), "answerable_n": answerable,
        "recall_at_k": {k: counts[k] / answerable if answerable else None for k in KS},
        "retrieval_failures": failures,
        "unanswerable": {"n": unanswerable, "reviewed": unanswerable_review,
                         "review_rate": unanswerable_review / unanswerable if unanswerable else None},
        "retrieval_latency": latency(retrieval_ms), "total_latency": latency(total_ms),
        "reported_usage": {"n": usage_count, "input_tokens": input_tokens,
                           "output_tokens": output_tokens} if usage_count else None,
        "cases_for_human_review": cases,
    }


async def run(args: argparse.Namespace) -> dict[str, Any]:
    dataset = (DATA / f"{args.split}.json").read_bytes()
    examples = [Example.model_validate(item) for item in json.loads(dataset)]
    if not examples or len(examples) != len({example.id for example in examples}):
        raise ValueError("Evaluation examples must have unique IDs and be nonempty.")
    runs = {}
    with tempfile.TemporaryDirectory() as directory:
        for method in dict.fromkeys(args.retrievers):
            result = await evaluate(args.index, method, examples, args.provider,
                                    Path(directory) / f"{method}.sqlite3")
            usage = result["reported_usage"]
            if usage and args.prices is not None:
                input_price, output_price = args.prices
                result["estimated_usd"] = {
                    "amount": (usage["input_tokens"] * input_price
                               + usage["output_tokens"] * output_price) / 1_000_000,
                    "price_per_million": args.prices, "pricing_source": args.pricing_source,
                }
            runs[method] = result
    return {
        "evaluation": "offline flow verification" if args.provider == "fake" else "provider evaluation",
        "split": args.split, "dataset_sha256": hashlib.sha256(dataset).hexdigest(),
        "runs": runs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--split", choices=["dev", "final"], default="dev")
    parser.add_argument("--retrievers", nargs="+", choices=["lexical", "dense"], default=["lexical"])
    parser.add_argument("--provider", choices=["fake", "openai"], default="fake")
    parser.add_argument("--prices", nargs=2, type=float, metavar=("INPUT_USD", "OUTPUT_USD"))
    parser.add_argument("--pricing-source")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.prices is not None and (
        not args.pricing_source or any(not math.isfinite(price) or price < 0 for price in args.prices)
    ):
        parser.error("--prices requires finite non-negative prices and --pricing-source.")
    report = json.dumps(asyncio.run(run(args)), ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(report + "\n", encoding="utf-8")
    else:
        print(report)


if __name__ == "__main__":
    main()
