"""Run the versioned, dependency-free baseline RAG evaluation."""

import argparse
import json
import re
import time
from hashlib import blake2b
from math import sqrt
from pathlib import Path

WORD_RE = re.compile(r"[\w']+", re.UNICODE)
VECTOR_SIZE = 256


def embed(text: str) -> list[float]:
    vector = [0.0] * VECTOR_SIZE
    for word in WORD_RE.findall(text.casefold()):
        digest = blake2b(word.encode("utf-8"), digest_size=4).digest()
        vector[int.from_bytes(digest, "big") % VECTOR_SIZE] += 1.0
    norm = sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", nargs="?", default="evals/rag-baseline-v1.json")
    parser.add_argument("--k", type=int, default=3)
    args = parser.parse_args()
    dataset = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    documents = dataset["documents"]
    hits = reciprocal_rank = citations = total_latency = 0.0
    for query in dataset["queries"]:
        started = time.perf_counter()
        ranked = sorted(
            ((cosine(embed(query["text"]), embed(doc["text"])), doc["id"]) for doc in documents),
            reverse=True,
        )[: args.k]
        total_latency += time.perf_counter() - started
        relevant = set(query["relevant_documents"])
        if any(doc_id in relevant for _, doc_id in ranked):
            hits += 1
            reciprocal_rank += 1 / next(index for index, item in enumerate(ranked, 1) if item[1] in relevant)
            citations += 1
        elif not relevant:
            citations += 1
    count = len(dataset["queries"])
    relevant_count = sum(bool(q["relevant_documents"]) for q in dataset["queries"])
    print(json.dumps({
        "dataset": dataset["version"], "k": args.k, "queries": count,
        "hit_rate": round(hits / count, 4),
        "recall": round(hits / relevant_count, 4) if relevant_count else 0,
        "mrr": round(reciprocal_rank / count, 4),
        "citation_coverage": round(citations / count, 4),
        "avg_latency_ms": round(total_latency / count * 1000, 4)
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
