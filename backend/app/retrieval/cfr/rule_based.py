"""Rule-based multi-label Contextual Functional Representation baseline."""

from __future__ import annotations

import time
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from app.retrieval.providers.base import OfflineProvider, ProviderMetadata

Vocabulary = Mapping[str, Mapping[str, tuple[str, ...]]]

DEFAULT_VOCABULARY: Vocabulary = MappingProxyType(
    {
        "power_source": {
            "human_power": ("人力", "手摇", "脚踏", "踏板", "hand powered"),
            "water_power": ("流水", "水力", "水轮", "水车", "水动力", "hydraulic power"),
            "animal_power": ("畜力", "牛力", "马力", "animal power"),
            "wind_power": ("风力", "风车", "wind power"),
        },
        "motion": {
            "rotary": ("旋转", "回转", "转动", "轮转", "rotary"),
            "reciprocating": ("往复", "来回", "升降", "reciprocating"),
            "linear": ("直线", "平移", "linear motion"),
            "cyclic": ("循环", "连续运动", "cyclic motion"),
        },
        "transmission": {
            "gear": ("齿轮", "轮齿", "gear"),
            "belt": ("带传动", "带轮传动", "皮带", "belt drive"),
            "chain": ("链传动", "链条", "链板传动", "chain drive"),
            "shaft": ("轮轴", "转轴", "轴传动", "轮轴传动", "轮轴承载", "shaft"),
            "cam": ("凸轮", "凸轮传动", "cam"),
            "linkage": ("杆件联动", "杠杆传动", "杆件", "杠杆", "linkage"),
            "wheel_support": ("轮周承载", "轮周承托", "wheel support"),
        },
        "action": {
            "lifting": ("提水", "汲水", "提升", "提灌", "lifting"),
            "grinding": ("磨粉", "碾磨", "舂米", "grinding"),
            "weaving": ("纺织", "织布", "纺纱", "织造", "weaving"),
            "irrigation": ("灌溉", "引水", "irrigation"),
            "cutting": ("切割", "锯", "cutting"),
            "shooting": ("发射", "远射", "shooting"),
            "mobility": ("机动", "调节方向", "mobility"),
        },
        "object": {
            "water": ("水流", "流水", "河水", "渠水", "灌渠", "农田水面", "提水", "灌溉", "water"),
            "grain": ("谷物", "稻谷", "麦", "碾磨", "舂捣", "grain"),
            "fiber": ("丝", "棉", "麻", "纤维", "纤维束", "fiber"),
            "textile_yarn": ("经纬纱线", "经线", "纱线", "纬线", "textile yarn"),
            "arrow": ("箭矢", "箭", "arrow"),
            "cannon": ("炮身", "火炮", "cannon"),
            "wood": ("木料", "木材", "wood"),
            "soil": ("土壤", "泥土", "soil"),
        },
        "purpose": {
            "water_lifting_irrigation": ("提水灌溉", "提灌", "water lifting irrigation"),
            "textile_production": ("纺纱", "织造布帛", "织造纹样", "textile production"),
            "grain_processing": ("谷物加工", "grain processing"),
            "long_range_shooting": ("远程发射", "远射", "long-range shooting"),
            "firearm_mobility": ("火器机动", "firearm mobility"),
        },
    }
)


@dataclass(frozen=True, slots=True)
class CFRConcept:
    slot: str
    concept: str
    confidence: float
    matched_terms: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CFRResult:
    slots: Mapping[str, tuple[CFRConcept, ...]]
    metadata: ProviderMetadata

    @property
    def is_unknown(self) -> bool:
        return all(
            not concepts or all(concept.concept == "unknown" for concept in concepts)
            for concepts in self.slots.values()
        )


class RuleBasedCFRProvider(OfflineProvider):
    provider_name = "rule_based_cfr"
    model_name = "controlled-functional-vocabulary"
    version = "1.0.0"
    preprocessing_contract = "nfkc-casefold+substring-controlled-vocabulary-v1"

    def __init__(self, vocabulary: Vocabulary = DEFAULT_VOCABULARY) -> None:
        self._vocabulary = vocabulary
        self.dimension = sum(len(concepts) for concepts in vocabulary.values())

    def extract(self, text: str) -> CFRResult:
        started = time.perf_counter_ns()
        normalized = unicodedata.normalize("NFKC", text).casefold()
        slots: dict[str, tuple[CFRConcept, ...]] = {}
        for slot, concepts in self._vocabulary.items():
            matches: list[CFRConcept] = []
            for concept, terms in concepts.items():
                matched_terms = tuple(term for term in terms if term.casefold() in normalized)
                if matched_terms:
                    confidence = min(0.95, 0.6 + 0.1 * len(matched_terms))
                    matches.append(
                        CFRConcept(
                            slot=slot,
                            concept=concept,
                            confidence=confidence,
                            matched_terms=matched_terms,
                        )
                    )
            if not matches:
                matches.append(
                    CFRConcept(
                        slot=slot,
                        concept="unknown",
                        confidence=0.0,
                        matched_terms=(),
                    )
                )
            slots[slot] = tuple(matches)

        elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
        return CFRResult(slots=slots, metadata=self.metadata(elapsed_ms))
