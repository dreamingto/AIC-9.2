from __future__ import annotations

from dataclasses import dataclass

from app.retrieval.baseline.bm25 import BM25TextProvider
from app.retrieval.cfr.rule_based import RuleBasedCFRProvider
from app.retrieval.graph.weighted import FixtureRelationProvider
from app.retrieval.providers.base import OfflineProvider, ProviderHealth
from app.retrieval.providers.image_embedding import DeterministicImageEmbeddingProvider
from app.retrieval.providers.text_embedding import DeterministicTextEmbeddingProvider


@dataclass(slots=True)
class ProviderRegistry:
    text_embedding: DeterministicTextEmbeddingProvider
    image_embedding: DeterministicImageEmbeddingProvider
    cfr: RuleBasedCFRProvider
    graph: FixtureRelationProvider
    bm25: BM25TextProvider

    @classmethod
    def create(cls) -> ProviderRegistry:
        return cls(
            text_embedding=DeterministicTextEmbeddingProvider(),
            image_embedding=DeterministicImageEmbeddingProvider(),
            cfr=RuleBasedCFRProvider(),
            graph=FixtureRelationProvider(),
            bm25=BM25TextProvider(),
        )

    def health(self) -> list[ProviderHealth]:
        return [
            self.text_embedding.health(),
            self.image_embedding.health(),
            self.cfr.health(),
            self.graph.health(),
            self.bm25.health(),
        ]

    def all_offline(self) -> list[OfflineProvider]:
        return [self.text_embedding, self.image_embedding, self.cfr, self.graph, self.bm25]
