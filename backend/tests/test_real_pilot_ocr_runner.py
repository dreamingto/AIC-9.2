from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

import scripts.run_real_pilot_ocr as runner
from app.retrieval.providers.base import OfflineProvider
from app.retrieval.providers.ocr import OCRLine, OCRResult


class FakeOCR(OfflineProvider):
    model_name = "test-ocr"

    def __init__(self, *, fail_at: int = 0, version: str = "1.0.0") -> None:
        self.calls = 0
        self.fail_at = fail_at
        self.version = version

    def recognize(self, image: str | Path | bytes) -> OCRResult:
        self.calls += 1
        if self.calls == self.fail_at:
            raise RuntimeError("interrupted inference")
        return OCRResult("織", (OCRLine("織", (1, 2, 3, 4), 0.8, 0),), self.metadata())


@pytest.fixture
def inputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    processed = tmp_path / "processed"
    processed.mkdir()
    monkeypatch.setattr(runner, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(runner, "PROCESSED_ROOT", processed)
    pages = []
    for index in range(2):
        path = processed / f"{index}.png"
        Image.new("RGB", (20, 30), "white").save(path)
        pages.append(
            {
                "page_id": f"page-{index}",
                "source_id": "source-a",
                "image_path": f"processed/{index}.png",
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    inventory = tmp_path / "inventory.json"
    inventory.write_text(
        json.dumps(
            {
                "dataset_kind": "real_pilot_page_inventory",
                "pages": pages,
            }
        ),
        encoding="utf-8",
    )
    return inventory, tmp_path / "raw.json"


def test_checkpoint_resumes_without_repeating_finished_pages(inputs: tuple[Path, Path]) -> None:
    inventory, output = inputs
    with pytest.raises(RuntimeError):
        runner.run_ocr(inventory_path=inventory, output_path=output, provider=FakeOCR(fail_at=2))
    partial = json.loads(output.read_text(encoding="utf-8"))
    assert partial["run_status"] == "failed" and len(partial["pages"]) == 1
    provider = FakeOCR()
    final = runner.run_ocr(
        inventory_path=inventory,
        output_path=output,
        provider=provider,
        resume=True,
    )
    assert final["run_status"] == "completed" and len(final["pages"]) == 2
    assert provider.calls == 1
    runner.run_ocr(inventory_path=inventory, output_path=output, provider=provider, resume=True)
    assert provider.calls == 1
    assert all(p["corrected_text"] is None and p["status"] == "inferred" for p in final["pages"])


@pytest.mark.parametrize("change", ["scope", "model", "review", "result"])
def test_resume_rejects_changed_or_reviewed_checkpoints(
    inputs: tuple[Path, Path],
    change: str,
) -> None:
    inventory, output = inputs
    runner.run_ocr(inventory_path=inventory, output_path=output, provider=FakeOCR())
    cache: dict[str, Any] = json.loads(output.read_text(encoding="utf-8"))
    if change == "review":
        cache["pages"][0]["corrected_text"] = "human correction"
    elif change == "result":
        cache["pages"][0]["raw_text"] = "modified"
    output.write_text(json.dumps(cache), encoding="utf-8")
    original = output.read_bytes()
    with pytest.raises(runner.RealPilotOCRError):
        runner.run_ocr(
            inventory_path=inventory,
            output_path=output,
            resume=True,
            provider=FakeOCR(version="2" if change == "model" else "1.0.0"),
            page_ids={"page-0"} if change == "scope" else None,
        )
    assert output.read_bytes() == original


def test_invalid_image_hash_and_unknown_ids_fail_before_inference(
    inputs: tuple[Path, Path],
) -> None:
    inventory, output = inputs
    provider = FakeOCR()
    with pytest.raises(runner.RealPilotOCRError, match="unknown page IDs"):
        runner.run_ocr(
            inventory_path=inventory,
            output_path=output,
            provider=provider,
            page_ids={"page-0", "typo"},
        )
    (inventory.parent / "processed/0.png").write_bytes(b"changed")
    with pytest.raises(runner.RealPilotOCRError, match="hash mismatch"):
        runner.run_ocr(inventory_path=inventory, output_path=output, provider=provider)
    assert provider.calls == 0 and not output.exists()


def test_supplement_cannot_overwrite_primary_or_inventory(inputs: tuple[Path, Path]) -> None:
    inventory, _ = inputs
    with pytest.raises(runner.RealPilotOCRError, match="separate"):
        runner.run_ocr(inventory_path=inventory, provider=FakeOCR())
    with pytest.raises(runner.RealPilotOCRError, match="overwrite inventory"):
        runner.run_ocr(inventory_path=inventory, output_path=inventory, provider=FakeOCR())
