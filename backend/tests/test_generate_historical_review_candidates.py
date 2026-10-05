from __future__ import annotations

from scripts.convert_ppocrlabel_annotations import LabelBox, PageRecord
from scripts.generate_historical_review_candidates import (
    SECTION_BODY_STARTS,
    SECTION_HEADING_OVERRIDES,
    _align_reference_candidates,
    _classification,
    _consensus_candidate,
    _crop_for_recognition,
    _reading_order_indices,
    _run_server_recognition,
)


def _box(text: str, x: float, y: float = 20, height: float = 600) -> LabelBox:
    return LabelBox(
        transcription=text,
        points=((x, y), (x + 30, y), (x + 30, y + height), (x, y + height)),
        difficult=False,
    )


def _page(number: int) -> PageRecord:
    return PageRecord(
        page_id=f"commons-najda-tiangong-kaiwu-2-p{number:04d}",
        source_id="commons-najda-tiangong-kaiwu-2",
        image_path="unused.png",
        image_key=f"commons-najda-tiangong-kaiwu-2/page-{number:04d}.png",
        width=1000,
        height=1000,
        sha256="0" * 64,
        provenance={},
    )


def test_reading_order_is_right_leaf_then_right_to_left_columns() -> None:
    boxes = [
        _box("左一", 100),
        _box("右二下", 700, y=400, height=100),
        _box("右一", 850),
        _box("右二上", 705, y=100, height=100),
        _box("左二", 300),
    ]

    order = _reading_order_indices(boxes, page_width=1000)

    assert order == [2, 3, 1, 4, 0]


def test_classification_separates_figure_title_body_and_annotation() -> None:
    figure_page = _page(12)
    text_page = _page(3)

    assert _classification(
        _box("圖絲治", 650, height=80), page=figure_page, box_index=2
    )[:2] == ("caption", "figure_title")
    assert _classification(
        _box("宋子曰人為萬物之靈五官百體", 700),
        page=text_page,
        box_index=1,
    )[:2] == ("text", "body")
    assert _classification(
        _box("天工開物", 50, height=150), page=text_page, box_index=2
    )[:2] == ("annotation", "running_title")


def test_reference_alignment_preserves_order_and_reports_confidence() -> None:
    matches = _align_reference_candidates(
        ["宋子曰人為萬物", "五官百體賅而存焉"],
        "宋子曰人為萬物之靈五官百體賅而存焉",
    )

    assert matches[0][0].startswith("宋子曰")
    assert matches[1][0].endswith("存焉")
    assert matches[0][2] == 0
    assert matches[1][2] >= matches[0][3]
    assert matches[1][1] > 0.8


def test_vertical_crop_rotates_to_horizontal() -> None:
    from PIL import Image

    image = Image.new("RGB", (200, 400), "white")
    crop = _crop_for_recognition(image, _box("縱列", 50, y=20, height=300))

    assert crop.width > crop.height


def test_explicit_heading_overrides_repair_known_ocr_errors() -> None:
    assert SECTION_HEADING_OVERRIDES[(3, 16)] == "蠶種"
    assert SECTION_HEADING_OVERRIDES[(7, 18)] == "病癥"
    assert SECTION_HEADING_OVERRIDES[(19, 2)] == "熟練"
    assert SECTION_HEADING_OVERRIDES[(24, 17)] == "枲著"

    assert _classification(
        _box("燈種", 650, height=80), page=_page(3), box_index=16
    ) == ("text", "section_heading", 0.99, "蠶種")


def test_late_section_body_anchors_prevent_cross_section_drift() -> None:
    assert SECTION_BODY_STARTS[(20, 12)] == "龍袍"
    assert SECTION_BODY_STARTS[(20, 6)] == "倭緞"
    assert SECTION_BODY_STARTS[(24, 15)] == "枲著"
    assert SECTION_BODY_STARTS[(24, 9)] == "夏服"
    assert SECTION_BODY_STARTS[(25, 15)] == "裘"
    assert SECTION_BODY_STARTS[(26, 3)] == "褐 氊"


def test_first_alignment_can_start_midway_through_each_section() -> None:
    first = _align_reference_candidates(
        ["丙丁"],
        "甲乙丙丁戊己",
    )
    second = _align_reference_candidates(
        ["子丑"],
        "庚辛壬癸子丑寅卯",
    )

    assert first[0][0] == "丙丁"
    assert first[0][2] == 2
    assert second[0][0] == "子丑"
    assert second[0][2] == 4
    assert first[0][1] == second[0][1] == 1.0


def test_secondary_ocr_cache_reuses_matching_crop(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    import sys
    from types import SimpleNamespace

    from PIL import Image

    monkeypatch.setitem(sys.modules, "numpy", SimpleNamespace(asarray=lambda image: image))

    class FakeEngine:
        def __init__(self) -> None:
            self.calls = 0

        def predict(self, input, batch_size=None):  # noqa: ANN001, ANN201
            self.calls += 1
            return [{"rec_text": "蠶種", "rec_score": 0.95} for _ in input]

    image_path = tmp_path / "unused.png"
    Image.new("RGB", (200, 400), "white").save(image_path)
    page = _page(3)
    work = [(page, 16, _box("燈種", 50, y=20, height=300))]
    cache_path = tmp_path / "server-cache.json"
    first_engine = FakeEngine()
    second_engine = FakeEngine()

    first = _run_server_recognition(
        work,
        project_root=tmp_path,
        device="cpu",
        batch_size=1,
        engine=first_engine,
        cache_path=cache_path,
    )
    second = _run_server_recognition(
        work,
        project_root=tmp_path,
        device="cpu",
        batch_size=1,
        engine=second_engine,
        cache_path=cache_path,
    )

    assert first_engine.calls == 1
    assert second_engine.calls == 0
    assert first[(page.page_id, 16)]["cache_hit"] is False
    assert second[(page.page_id, 16)]["cache_hit"] is True
    assert second[(page.page_id, 16)]["text"] == "蠶種"


def test_consensus_candidate_is_conservative_and_remains_inferred() -> None:
    assert _consensus_candidate(
        raw_text="凡蠶用浴法",
        server_text="凡蠶用浴法",
        reference_text="凡蠶用浴法",
        normalized_candidate=None,
        role="body",
    ) == ("凡蠶用浴法", "exact_pair:raw+reference+server")
    assert _consensus_candidate(
        raw_text="燈種",
        server_text="蠶種",
        reference_text=None,
        normalized_candidate="蠶種",
        role="section_heading",
    ) == ("蠶種", "controlled_title_candidate")
    assert _consensus_candidate(
        raw_text="甲乙",
        server_text="丙丁",
        reference_text="戊己",
        normalized_candidate=None,
        role="body",
    ) == (None, "no_consensus")
