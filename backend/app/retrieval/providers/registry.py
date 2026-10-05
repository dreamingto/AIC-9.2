from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings
from app.retrieval.baseline.bm25 import BM25TextProvider
from app.retrieval.cfr.rule_based import RuleBasedCFRProvider
from app.retrieval.graph.weighted import FixtureRelationProvider
from app.retrieval.providers.base import OfflineProvider, ProviderHealth
from app.retrieval.providers.image_embedding import DeterministicImageEmbeddingProvider
from app.retrieval.providers.neural import NeuralImageEmbeddingProvider, NeuralTextEmbeddingProvider
from app.retrieval.providers.text_embedding import DeterministicTextEmbeddingProvider


@dataclass(slots=True)
class ProviderRegistry:
    text_embedding: DeterministicTextEmbeddingProvider | NeuralTextEmbeddingProvider
    image_embedding: DeterministicImageEmbeddingProvider | NeuralImageEmbeddingProvider
    cfr: RuleBasedCFRProvider
    graph: FixtureRelationProvider
    bm25: BM25TextProvider
    clip_text: NeuralTextEmbeddingProvider | None = None

    @classmethod
    def create(cls, settings: Settings | None = None) -> ProviderRegistry:
        if settings is not None and settings.retrieval_profile == "neural":
            return cls(
                text_embedding=NeuralTextEmbeddingProvider(
                    "text", settings.model_service_url, settings.model_timeout_seconds
                ),
                image_embedding=NeuralImageEmbeddingProvider(
                    "image", settings.model_service_url, settings.model_timeout_seconds
                ),
                cfr=RuleBasedCFRProvider(),
                graph=FixtureRelationProvider(),
                bm25=BM25TextProvider(),
                clip_text=NeuralTextEmbeddingProvider(
                    "clip_text", settings.model_service_url, settings.model_timeout_seconds
                ),
            )
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
        ] + ([self.clip_text.health()] if self.clip_text else [])

    def all_offline(self) -> list[OfflineProvider]:
        return [self.text_embedding, self.image_embedding, self.cfr, self.graph, self.bm25]
