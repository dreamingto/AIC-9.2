import hashlib
import json
from pathlib import Path

import pytest

from app.retrieval.experiments.contracts import EvidencePlan, QueryProtocol


def test_full_coverage_remains_ai_only_and_keeps_frozen_queries() -> None:
    data = Path(__file__).parents[1] / "data/experiments"
    plan = EvidencePlan.model_validate_json(
        (data / "domestic-functions-v2.json").read_text(encoding="utf-8")
    )
    old = QueryProtocol.model_validate_json(
        (data / "domestic-queries-v1.json").read_text(encoding="utf-8")
    )
    new = QueryProtocol.model_validate_json(
        (data / "domestic-queries-v2.json").read_text(encoding="utf-8")
    )
    assert len(plan.figures) == 12
    assert all(len(f.functions) == 6 for f in plan.figures)
    assert all(
        c.confidence is None and c.state == "Inferred" for f in plan.figures for c in f.functions
    )
    assert all(not r.eligible_for_graph_rerank for f in plan.figures for r in f.relations)
    assert [q.model_dump() for q in old.queries] == [q.model_dump() for q in new.queries]
    assert not plan.independent_ground_truth
    lock_path = data.parents[2] / "release/domestic-data.lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    assert lock["figures"] == 12 and not lock["models_included"]


@pytest.mark.parametrize("relative", [
    "backend/data/real_pilot/sources.json",
    "backend/data/real_pilot/domestic_ai_selection.json",
])
def test_checkout_registry_bytes_match_frozen_restore_inputs(relative: str) -> None:
    root = Path(__file__).parents[2]
    lock = json.loads((root / "release/domestic-data.lock.json").read_text(encoding="utf-8"))
    expected = next(entry["sha256"] for entry in lock["files"] if entry["path"] == relative)
    assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected
