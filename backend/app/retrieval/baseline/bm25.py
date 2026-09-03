"""A dependency-free BM25 baseline with Chinese-aware tokenization."""

from __future__ import annotations

import math
import re
import time
import unicodedata
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from app.retrieval.providers.base import OfflineProvider, ProviderMetadata

_LATIN_OR_NUMBER = re.compile(r"[a-z0-9]+(?:[_-][a-z0-9]+)*")


def _is_cjk(character: str) -> bool:
    codepoint = ord(character)
    return (
        0x3400 <= codepoint <= 0x4DBF
        or 0x4E00 <= codepoint <= 0x9FFF
        or 0xF900 <= codepoint <= 0xFAFF
        or 0x20000 <= codepoint <= 0x2FA1F
    )


def tokenize_zh(text: str) -> list[str]:
    """Return CJK unigrams/bigrams plus normalized Latin and numeric words."""

    normalized = unicodedata.normalize("NFKC", text).lower()
    tokens: list[str] = []
    cjk_run: list[str] = []

    def flush_cjk() -> None:
        if not cjk_run:
            return
        tokens.extend(cjk_run)
        tokens.extend(cjk_run[index] + cjk_run[index + 1] for index in range(len(cjk_run) - 1))
        cjk_run.clear()

    for character in normalized:
        if _is_cjk(character):
            cjk_run.append(character)
        else:
            flush_cjk()
    flush_cjk()
    tokens.extend(_LATIN_OR_NUMBER.findall(normalized))
    return tokens


@dataclass(frozen=True, slots=True)
class BM25Hit:
    document_id: str
    score: float


@dataclass(frozen=True, slots=True)
class BM25SearchResult:
    hits: tuple[BM25Hit, ...]
    metadata: ProviderMetadata


class BM25TextProvider(OfflineProvider):
    provider_name = "bm25_text"
    model_name = "bm25-zh-char-bigram"
    version = "1.0.0"
    preprocessing_contract = "nfkc-lower+cjk-unigram-bigram+latin-word-v1"

    def __init__(
        self,
        documents: Mapping[str, str] | Iterable[tuple[str, str]] | None = None,
        *,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        if k1 <= 0:
            raise ValueError("k1 must be greater than zero")
        if not 0 <= b <= 1:
            raise ValueError("b must be between zero and one")
        self.k1 = float(k1)
        self.b = float(b)
        self._term_frequencies: dict[str, Counter[str]] = {}
        self._document_lengths: dict[str, int] = {}
        self._document_frequencies: Counter[str] = Counter()
        self._average_document_length = 0.0
        if documents is not None:
            self.fit(documents)

    @property
    def dimension(self) -> int:  # type: ignore[override]
        return len(self._document_frequencies)

    def fit(self, documents: Mapping[str, str] | Iterable[tuple[str, str]]) -> BM25TextProvider:
        items = documents.items() if isinstance(documents, Mapping) else documents
        frequencies: dict[str, Counter[str]] = {}
        lengths: dict[str, int] = {}
        document_frequencies: Counter[str] = Counter()

        for raw_document_id, text in items:
            document_id = str(raw_document_id)
            if document_id in frequencies:
                raise ValueError(f"duplicate document id: {document_id}")
            terms = tokenize_zh(text)
            term_frequency = Counter(terms)
            frequencies[document_id] = term_frequency
            lengths[document_id] = len(terms)
            document_frequencies.update(term_frequency.keys())

        self._term_frequencies = frequencies
        self._document_lengths = lengths
        self._document_frequencies = document_frequencies
        count = len(lengths)
        self._average_document_length = sum(lengths.values()) / count if count else 0.0
        return self

    def search(self, query: str, *, top_k: int = 10) -> BM25SearchResult:
        if top_k < 1:
            raise ValueError("top_k must be at least one")
        started = time.perf_counter_ns()
        query_frequency = Counter(tokenize_zh(query))
        document_count = len(self._term_frequencies)
        scored: list[BM25Hit] = []

        if query_frequency and document_count:
            average_length = self._average_document_length or 1.0
            for document_id, terms in self._term_frequencies.items():
                score = 0.0
                document_length = self._document_lengths[document_id]
                normalization = self.k1 * (1.0 - self.b + self.b * document_length / average_length)
                for term, query_count in query_frequency.items():
                    frequency = terms.get(term, 0)
                    if frequency == 0:
                        continue
                    containing = self._document_frequencies[term]
                    inverse_document_frequency = math.log(
                        1.0 + (document_count - containing + 0.5) / (containing + 0.5)
                    )
                    query_weight = 1.0 + math.log(query_count)
                    score += (
                        inverse_document_frequency
                        * frequency
                        * (self.k1 + 1.0)
                        / (frequency + normalization)
                        * query_weight
                    )
                if score > 0.0:
                    scored.append(BM25Hit(document_id=document_id, score=score))

        scored.sort(key=lambda hit: (-hit.score, hit.document_id))
        elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
        return BM25SearchResult(
            hits=tuple(scored[:top_k]),
            metadata=self.metadata(elapsed_ms),
        )
