from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9+#./-]*", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    return [token.lower().strip("./-") for token in TOKEN_PATTERN.findall(text) if token.strip("./-")]


@dataclass(slots=True)
class Document:
    evidence_id: str
    source: str
    title: str
    text: str
    document_type: str
    source_url: str = ""
    source_version: str = "sample"
    license: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Document":
        return cls(**value)

    def to_result(self, score: float) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source": self.source,
            "title": self.title,
            "text": self.text,
            "score": round(score, 8),
            "source_url": self.source_url,
            "source_version": self.source_version,
            "license": self.license,
            "document_type": self.document_type,
            "metadata": self.metadata,
        }


def load_documents(path: str | Path) -> list[Document]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Document.from_dict(item) for item in raw]


class HashedVectorizer:
    """Small deterministic vectorizer used when no neural model is installed."""

    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions

    def encode(self, text: str) -> list[float]:
        tokens = tokenize(text)
        features = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
        vector = [0.0] * self.dimensions
        for feature in features:
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest, "big") % self.dimensions
            vector[index] += 1.0
        magnitude = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / magnitude for value in vector]


def cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


class HybridIndex:
    """In-memory BM25 + hashed-vector index with reciprocal-rank fusion."""

    def __init__(self, documents: Iterable[Document]) -> None:
        self.documents = list(documents)
        self.vectorizer = HashedVectorizer()
        self.token_counts = [Counter(tokenize(f"{doc.title} {doc.text}")) for doc in self.documents]
        self.lengths = [sum(counts.values()) for counts in self.token_counts]
        self.average_length = sum(self.lengths) / max(len(self.lengths), 1)
        document_frequency: Counter[str] = Counter()
        for counts in self.token_counts:
            document_frequency.update(counts.keys())
        count = max(len(self.documents), 1)
        self.idf = {
            token: math.log(1 + (count - frequency + 0.5) / (frequency + 0.5))
            for token, frequency in document_frequency.items()
        }
        self.vectors = [self.vectorizer.encode(f"{doc.title} {doc.text}") for doc in self.documents]

    @staticmethod
    def _matches(doc: Document, document_types: list[str], filters: dict[str, Any]) -> bool:
        if document_types and doc.document_type not in document_types:
            return False
        for key, expected in filters.items():
            actual = doc.metadata.get(key)
            if isinstance(expected, list):
                if isinstance(actual, list):
                    if not set(expected).intersection(actual):
                        return False
                elif actual not in expected:
                    return False
            elif isinstance(actual, list):
                if expected not in actual:
                    return False
            elif actual != expected:
                return False
        return True

    def _bm25(self, query_tokens: list[str], index: int) -> float:
        counts = self.token_counts[index]
        length = self.lengths[index]
        k1, b = 1.5, 0.75
        score = 0.0
        for token in query_tokens:
            frequency = counts.get(token, 0)
            if not frequency:
                continue
            denominator = frequency + k1 * (1 - b + b * length / max(self.average_length, 1))
            score += self.idf.get(token, 0.0) * frequency * (k1 + 1) / denominator
        return score

    def search(
        self,
        query: str,
        top_k: int = 8,
        document_types: list[str] | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        document_types = document_types or []
        filters = filters or {}
        candidates = [
            index
            for index, document in enumerate(self.documents)
            if self._matches(document, document_types, filters)
        ]
        if not candidates:
            return []
        if not query.strip():
            return [self.documents[index].to_result(1.0) for index in candidates[:top_k]]

        query_tokens = tokenize(query)
        query_vector = self.vectorizer.encode(query)
        lexical = sorted(candidates, key=lambda i: self._bm25(query_tokens, i), reverse=True)
        dense = sorted(candidates, key=lambda i: cosine(query_vector, self.vectors[i]), reverse=True)

        fused: dict[int, float] = {index: 0.0 for index in candidates}
        for rank, index in enumerate(lexical, start=1):
            fused[index] += 1.0 / (60 + rank)
        for rank, index in enumerate(dense, start=1):
            fused[index] += 1.0 / (60 + rank)

        ordered = sorted(candidates, key=lambda i: fused[i], reverse=True)[:top_k]
        return [self.documents[index].to_result(fused[index]) for index in ordered]
