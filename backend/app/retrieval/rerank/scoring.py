"""Pure deterministic EAFR scoring primitives with no database or web dependency."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field
from typing import Any


def clip(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    if lower > upper:
        raise ValueError("lower must not exceed upper")
    if not math.isfinite(value):
        return lower
    return max(lower, min(upper, float(value)))


def normalize_score(value: float, minimum: float, maximum: float) -> float:
    if not math.isfinite(value) or not math.isfinite(minimum) or not math.isfinite(maximum):
        return 0.0
    if maximum == minimum:
        return 0.5
    return clip((value - minimum) / (maximum - minimum))


def cosine_similarity(left: Iterable[float], right: Iterable[float]) -> float:
    a = tuple(float(item) for item in left)
    b = tuple(float(item) for item in right)
    if not a or len(a) != len(b) or any(not math.isfinite(item) for item in a + b):
        return 0.0
    scale = max(max(abs(item) for item in a), max(abs(item) for item in b))
    if scale == 0.0 or not math.isfinite(scale):
        return 0.0
    aa = tuple(item / scale for item in a)
    bb = tuple(item / scale for item in b)
    numerator = sum(x * y for x, y in zip(aa, bb, strict=True))
    left_norm = math.sqrt(sum(x * x for x in aa))
    right_norm = math.sqrt(sum(y * y for y in bb))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return max(-1.0, min(1.0, numerator / (left_norm * right_norm)))


def cosine_to_unit(value: float) -> float:
    return clip((clip(value, -1.0, 1.0) + 1.0) / 2.0)


def normalized_entropy(values: Iterable[float]) -> float:
    numbers = []
    for item in values:
        number = float(item)
        numbers.append(max(0.0, number) if math.isfinite(number) else 0.0)
    if len(numbers) <= 1:
        return 0.0
    total = sum(numbers)
    if total == 0.0:
        return 1.0
    probabilities = [item / total for item in numbers if item > 0.0]
    entropy = -sum(item * math.log(item) for item in probabilities)
    return clip(entropy / math.log(len(numbers)))


def model_uncertainty(component_scores: Iterable[float]) -> float:
    values = [float(item) for item in component_scores if math.isfinite(float(item))]
    if len(values) <= 1:
        return 0.0
    maximum = max(values)
    exponentials = [math.exp(max(-60.0, min(60.0, item - maximum))) for item in values]
    return normalized_entropy(exponentials)


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    status: str = "Inferred"
    supports: tuple[str, ...] = ()
    claim_id: str | None = None
    text: str | None = None

    @classmethod
    def from_value(cls, value: object) -> EvidenceItem:
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            raw_supports = value.get("supports", ())
            supports = (
                tuple(str(item) for item in raw_supports)
                if isinstance(raw_supports, (list, tuple, set))
                else ()
            )
            return cls(
                status=str(value.get("status", "Inferred")),
                supports=supports,
                claim_id=str(value["claim_id"]) if value.get("claim_id") is not None else None,
                text=str(value["text"]) if value.get("text") is not None else None,
            )
        return cls(text=str(value))


_EVIDENCE_WEIGHTS = {"Verified": 1.0, "Documented": 0.9, "Observed": 0.8, "Inferred": 0.5}


def evidence_coverage(
    query_claims: Iterable[str],
    evidence: Iterable[EvidenceItem | Mapping[str, object] | object],
) -> float:
    claims = [str(claim).strip().casefold() for claim in query_claims if str(claim).strip()]
    if not claims:
        return 0.0
    items = [EvidenceItem.from_value(item) for item in evidence]
    best_scores: list[float] = []
    for claim in claims:
        best = 0.0
        for item in items:
            searchable = {claim_id.casefold() for claim_id in item.supports}
            if item.claim_id:
                searchable.add(item.claim_id.casefold())
            if item.text:
                searchable.add(item.text.casefold())
            if any(claim == value or claim in value or value in claim for value in searchable):
                best = max(best, _EVIDENCE_WEIGHTS.get(item.status, 0.5))
        best_scores.append(best)
    return sum(best_scores) / len(best_scores)


@dataclass(frozen=True, slots=True)
class EAFRWeights:
    beta_v: float = 0.2
    beta_t: float = 0.2
    beta_r: float = 0.15
    beta_f: float = 0.2
    beta_g: float = 0.1
    lambda_e: float = 0.1
    lambda_u: float = 0.05

    def __post_init__(self) -> None:
        if any(value < 0.0 or not math.isfinite(value) for value in asdict(self).values()):
            raise ValueError("EAFR weights must be finite and non-negative")

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ScoreComponents:
    sv: float
    st: float
    sr: float
    sf: float
    sg: float
    se: float
    u_model: float
    availability: dict[str, bool] = field(default_factory=dict)
    reliability: dict[str, float] = field(default_factory=dict)
    missing_modalities: tuple[str, ...] = ()
    weights: dict[str, float] = field(default_factory=dict)
    contributions: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sv": self.sv,
            "st": self.st,
            "sr": self.sr,
            "sf": self.sf,
            "sg": self.sg,
            "se": self.se,
            "u_model": self.u_model,
            "availability": dict(self.availability),
            "reliability": dict(self.reliability),
            "missing_modalities": list(self.missing_modalities),
            "weights": dict(self.weights),
            "contributions": dict(self.contributions),
        }


@dataclass(frozen=True, slots=True)
class EAFRResult:
    score: float
    components: ScoreComponents

    @property
    def score_components(self) -> dict[str, Any]:
        return self.components.to_dict()

    def to_dict(self) -> dict[str, Any]:
        return {"score": self.score, "score_components": self.score_components}


_ALIASES = {
    "visual": "sv",
    "image": "sv",
    "text": "st",
    "region": "sr",
    "function": "sf",
    "cfr": "sf",
    "graph": "sg",
    "structure": "sg",
}
_MODALITY_NAMES = {"sv": "visual", "st": "text", "sr": "region", "sf": "function", "sg": "graph"}


def score_candidate(
    scores: Mapping[str, float | None],
    *,
    evidence_score: float | None = 0.0,
    model_uncertainty_score: float | None = 0.0,
    weights: EAFRWeights | None = None,
    modality_reliability: Mapping[str, float] | None = None,
    availability: Mapping[str, bool] | None = None,
) -> EAFRResult:
    current = weights or EAFRWeights()
    raw: dict[str, float | None] = {name: None for name in _MODALITY_NAMES}
    for key, value in scores.items():
        canonical = _ALIASES.get(key, key)
        if canonical in raw:
            raw[canonical] = value
    values: dict[str, float] = {}
    available: dict[str, bool] = {}
    reliability: dict[str, float] = {}
    missing: list[str] = []
    for canonical, value in raw.items():
        name = _MODALITY_NAMES[canonical]
        is_available = bool((availability or {}).get(name, value is not None)) and value is not None
        available[name] = is_available
        if not is_available:
            missing.append(name)
        reliability[name] = (
            clip(float((modality_reliability or {}).get(name, 1.0 if is_available else 0.0)))
            if is_available
            else 0.0
        )
        values[canonical] = clip(float(value)) if is_available and value is not None else 0.0
    coefficients = {
        "sv": current.beta_v,
        "st": current.beta_t,
        "sr": current.beta_r,
        "sf": current.beta_f,
        "sg": current.beta_g,
    }
    contributions = {
        key: coefficients[key] * values[key] * reliability[_MODALITY_NAMES[key]]
        for key in coefficients
    }
    for name, value in (
        ("evidence", evidence_score),
        ("model_uncertainty", model_uncertainty_score),
    ):
        available[name] = value is not None
        reliability[name] = 1.0 if value is not None else 0.0
        if value is None:
            missing.append(name)
    se = clip(float(evidence_score)) if evidence_score is not None else 0.0
    u_model = clip(float(model_uncertainty_score)) if model_uncertainty_score is not None else 0.0
    contributions["se"] = current.lambda_e * se
    contributions["u_model"] = -current.lambda_u * u_model
    total = sum(contributions.values())
    return EAFRResult(
        score=float(total),
        components=ScoreComponents(
            sv=values["sv"],
            st=values["st"],
            sr=values["sr"],
            sf=values["sf"],
            sg=values["sg"],
            se=se,
            u_model=u_model,
            availability=available,
            reliability=reliability,
            missing_modalities=tuple(missing),
            weights=current.as_dict(),
            contributions=contributions,
        ),
    )


def compute_eafr_score(*args: Any, **kwargs: Any) -> EAFRResult:
    return score_candidate(*args, **kwargs)


def eafr_score(*args: Any, **kwargs: Any) -> float:
    return score_candidate(*args, **kwargs).score
