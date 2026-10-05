"""Generate model-assisted OCR, reading-order, and layout-class candidates.

The output is deliberately a review queue.  It never rewrites ``Label.txt``,
fills ``corrected_text``, or marks model output as verified ground truth.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import time
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Protocol, cast

from PIL import Image, ImageOps

from scripts.convert_ppocrlabel_annotations import (
    DEFAULT_SOURCE_ID,
    INVENTORY_PATH,
    PROCESSED_ROOT,
    PROJECT_ROOT,
    ConversionError,
    LabelBox,
    PageRecord,
    _load_inventory,
    _parse_annotation_file,
    _resolve_source_dir,
    _write_json_atomic,
)
from scripts.download_naifu_reference import OUTPUT_PATH as REFERENCE_PATH
from scripts.download_naifu_reference import SECTIONS

OUTPUT_PATH = (
    PROJECT_ROOT
    / "backend"
    / "data"
    / "real_pilot"
    / "annotations.model-assisted-candidates.json"
)
SERVER_CACHE_PATH = (
    PROJECT_ROOT / "backend" / "data" / "real_pilot" / "server-ocr-review-cache.json"
)
PIPELINE_VERSION = "historical-review-candidates-v2"
SERVER_MODEL = "PP-OCRv5_server_rec"
SERVER_INPUT_SHAPE = (3, 48, 1024)
FIGURE_PAGE_NUMBERS = frozenset({12, 13, 14, 16, 17, 22, 23})
SECTION_NAMES = tuple(section for section in SECTIONS if section != "乃服第二")
JAPANESE_OR_LATIN = re.compile(r"[\u3040-\u30ffA-Za-z]")
CJK_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")

# These overrides are tied to the retained PPOCRLabel box indices.  They repair
# only section-title candidates that can be located unambiguously from the scan
# and chapter sequence; they do not rewrite the box transcription.
SECTION_HEADING_OVERRIDES: dict[tuple[int, int], str] = {
    (2, 11): "乃服第二",
    (3, 16): "蠶種",
    (3, 15): "蠶浴",
    (4, 19): "種類",
    (4, 18): "抱養",
    (5, 20): "葉料",
    (6, 20): "食忌",
    (7, 18): "病癥",
    (7, 19): "老足",
    (8, 16): "取繭",
    (9, 18): "物害",
    (9, 17): "擇繭",
    (9, 16): "造綿",
    (10, 21): "治絲",
    (10, 19): "調絲",
    (11, 19): "經具",
    (11, 17): "過糊",
    (15, 17): "經數",
    (15, 19): "花機式",
    (18, 21): "腰機式",
    (18, 20): "結花本",
    (19, 20): "穿經",
    (19, 19): "分名",
    (19, 2): "熟練",
    (20, 20): "龍袍",
    (20, 18): "倭緞",
    (24, 17): "枲著",
    (24, 16): "夏服",
    (25, 18): "裘",
    (26, 14): "褐 氊",
}

# Some headings were not retained as independent boxes.  Explicit body-start
# anchors keep alignment deterministic without pretending that a missing title
# box exists.  A section continues until the next anchor in scan reading order.
SECTION_BODY_STARTS: dict[tuple[int, int], str] = {
    (2, 10): "乃服第二",
    (3, 13): "蠶種",
    (3, 8): "蠶浴",
    (4, 16): "種忌",
    (4, 12): "種類",
    (5, 16): "抱養",
    (5, 9): "養忌",
    (6, 18): "葉料",
    (6, 2): "食忌",
    (7, 11): "病癥",
    (7, 2): "老足",
    (8, 10): "結繭",
    (8, 3): "取繭",
    (9, 11): "物害",
    (9, 12): "擇繭",
    (9, 21): "造綿",
    (10, 17): "治絲",
    (10, 5): "調絲",
    (11, 4): "緯絡",
    (11, 2): "經具",
    (11, 14): "過糊",
    (15, 10): "邊維",
    (15, 7): "經數",
    (15, 2): "花機式",
    (18, 13): "腰機式",
    (18, 8): "結花本",
    (19, 13): "穿經",
    (19, 9): "分名",
    (20, 17): "熟練",
    (20, 12): "龍袍",
    (20, 6): "倭緞",
    (21, 9): "布衣",
    (24, 15): "枲著",
    (24, 9): "夏服",
    (25, 15): "裘",
    (26, 3): "褐 氊",
}


@dataclass(frozen=True)
class FigureSeed:
    side: str
    bbox: tuple[float, float, float, float]
    candidate_title: str
    caption_box_index: int | None
    title_bbox: tuple[float, float, float, float] | None = None


LEFT_FIGURE = (0.055, 0.13, 0.405, 0.75)
RIGHT_FIGURE = (0.535, 0.13, 0.355, 0.75)
FIGURE_SEEDS: dict[int, tuple[FigureSeed, ...]] = {
    12: (
        FigureSeed("right", RIGHT_FIGURE, "山箔圖", 3),
        FigureSeed("left", LEFT_FIGURE, "治絲圖", 2),
    ),
    13: (
        FigureSeed("right", RIGHT_FIGURE, "調絲", 2),
        FigureSeed("left", LEFT_FIGURE, "紡緯", 4),
    ),
    14: (
        FigureSeed("right", RIGHT_FIGURE, "溜眼", 2),
        FigureSeed("left", LEFT_FIGURE, "經耙", 3),
    ),
    16: (
        FigureSeed("spread", (0.055, 0.13, 0.835, 0.75), "花機圖", 2),
    ),
    17: (
        FigureSeed("right", RIGHT_FIGURE, "腰機式圖", 2),
        FigureSeed("left", LEFT_FIGURE, "過糊", 3),
    ),
    22: (
        FigureSeed(
            "right",
            RIGHT_FIGURE,
            "趕綿",
            None,
            (0.69, 0.16, 0.075, 0.06),
        ),
        FigureSeed("left", LEFT_FIGURE, "彈綿", 2),
    ),
    23: (
        FigureSeed(
            "right",
            RIGHT_FIGURE,
            "擦條",
            None,
            (0.70, 0.16, 0.075, 0.06),
        ),
        FigureSeed(
            "left",
            LEFT_FIGURE,
            "紡綿",
            None,
            (0.265, 0.205, 0.075, 0.06),
        ),
    ),
}


class RecognitionEngine(Protocol):
    def predict(self, input: Any, batch_size: int | None = None) -> list[Any]: ...


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _page_number(page: PageRecord) -> int:
    match = re.search(r"-p(\d{4})$", page.page_id)
    if match is None:
        raise ConversionError(f"page id has no four-digit suffix: {page.page_id}")
    return int(match.group(1))


def _bounds(box: LabelBox) -> tuple[float, float, float, float]:
    xs = [point[0] for point in box.points]
    ys = [point[1] for point in box.points]
    return min(xs), min(ys), max(xs), max(ys)


def _reading_order_indices(boxes: list[LabelBox], page_width: int) -> list[int]:
    """Order a scanned opening: right leaf first, then columns right-to-left."""

    def key(index: int) -> tuple[int, int, float, float]:
        x_min, y_min, x_max, _ = _bounds(boxes[index])
        x_center = (x_min + x_max) / 2
        side = 0 if x_center >= page_width / 2 else 1
        column_bucket = -round(x_center / 40)
        return side, column_bucket, y_min, -x_center

    return sorted(range(len(boxes)), key=key)


def _normalized_edit_similarity(left: str, right: str) -> float:
    if not left and not right:
        return 1.0
    return SequenceMatcher(a=left, b=right, autojunk=False).ratio()


def _consensus_candidate(
    *,
    raw_text: str,
    server_text: str | None,
    reference_text: str | None,
    normalized_candidate: str | None,
    role: str,
) -> tuple[str | None, str]:
    """Return a conservative inferred suggestion, never a corrected value."""

    if role in {"section_heading", "figure_title"} and normalized_candidate:
        return normalized_candidate, "controlled_title_candidate"
    values = {
        "raw": raw_text,
        "server": server_text or "",
        "reference": reference_text or "",
    }
    nonempty = {name: value for name, value in values.items() if _cjk_text(value)}
    exact_groups: dict[str, list[str]] = {}
    for name, value in nonempty.items():
        exact_groups.setdefault(_cjk_text(value), []).append(name)
    exact = next(
        (
            (normalized, sources)
            for normalized, sources in exact_groups.items()
            if len(sources) >= 2
        ),
        None,
    )
    if exact is not None:
        _, sources = exact
        preferred = "reference" if "reference" in sources else sources[0]
        return nonempty[preferred], "exact_pair:" + "+".join(sorted(sources))
    if len(nonempty) == 3:
        pair_scores = {
            (left, right): _normalized_edit_similarity(
                _cjk_text(nonempty[left]), _cjk_text(nonempty[right])
            )
            for left, right in (
                ("raw", "server"),
                ("raw", "reference"),
                ("server", "reference"),
            )
        }
        if min(pair_scores.values()) >= 0.9:
            return nonempty["reference"], "three_way_high_similarity"
    return None, "no_consensus"


def _cjk_text(value: str) -> str:
    return "".join(CJK_PATTERN.findall(value))


def _matching_section(value: str) -> str | None:
    text = _cjk_text(value)
    if not text or len(text) > 8:
        return None
    best: tuple[float, str] | None = None
    for section in SECTION_NAMES:
        score = _normalized_edit_similarity(text, _cjk_text(section))
        if best is None or score > best[0]:
            best = (score, section)
    if best is None:
        return None
    threshold = 0.66 if len(text) >= 2 else 0.8
    return best[1] if best[0] >= threshold else None


def _annotation_role(box: LabelBox, page: PageRecord, page_number: int) -> str | None:
    x_min, y_min, x_max, y_max = _bounds(box)
    width = x_max - x_min
    height = y_max - y_min
    text = box.transcription.strip()
    cjk = _cjk_text(text)
    if page_number == 1:
        return "book_title"
    if text == "十三号":
        return "repository_mark"
    if x_min < page.width * 0.115 and height < page.height * 0.32:
        if "天" in cjk and "物" in cjk:
            return "running_title"
        return "folio_mark"
    if JAPANESE_OR_LATIN.search(text) or any(character.isdigit() for character in text):
        if len(cjk) < 8 or height < page.height * 0.28:
            return "interlinear_annotation"
    if width < 25 and height < 80:
        return "recognition_fragment"
    return None


def _classification(
    box: LabelBox, *, page: PageRecord, box_index: int
) -> tuple[str, str, float, str | None]:
    page_number = _page_number(page)
    heading_override = SECTION_HEADING_OVERRIDES.get((page_number, box_index))
    if heading_override is not None:
        return "text", "section_heading", 0.99, heading_override
    annotation_role = _annotation_role(box, page, page_number)
    if annotation_role is not None:
        return "annotation", annotation_role, 0.96, None

    title_seed = next(
        (
            seed
            for seed in FIGURE_SEEDS.get(page_number, ())
            if seed.caption_box_index == box_index
        ),
        None,
    )
    if title_seed is not None:
        return "caption", "figure_title", 0.93, title_seed.candidate_title
    if page_number in FIGURE_PAGE_NUMBERS:
        return "caption", "component_label", 0.86, None

    section = _matching_section(box.transcription)
    if section is not None:
        return "text", "section_heading", 0.9, section
    _, y_min, _, y_max = _bounds(box)
    cjk = _cjk_text(box.transcription)
    if len(cjk) >= 10 or y_max - y_min >= page.height * 0.28:
        return "text", "body", 0.92, None
    return "annotation", "interlinear_annotation", 0.72, None


def _load_reference(path: Path) -> tuple[dict[str, str], dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConversionError(f"unable to read reference text: {path}") from exc
    if not isinstance(payload, dict) or payload.get("evaluation_status") != "not_evaluated":
        raise ConversionError("reference text has an invalid status")
    raw_sections = payload.get("sections")
    if not isinstance(raw_sections, list) or len(raw_sections) != len(SECTIONS):
        raise ConversionError("reference text does not contain every registered section")
    sections: dict[str, str] = {}
    for expected_name, raw_section in zip(SECTIONS, raw_sections, strict=True):
        if not isinstance(raw_section, dict):
            raise ConversionError("reference section must be an object")
        title = str(raw_section.get("title", ""))
        if title.rsplit("/", maxsplit=1)[-1] != expected_name:
            raise ConversionError(
                f"reference section order mismatch: expected {expected_name}"
            )
        sections[expected_name] = _cjk_text(str(raw_section.get("text", "")))
    if not all(sections.values()):
        raise ConversionError("reference text contains no CJK characters")
    return sections, cast(dict[str, Any], payload)


def _edit_distance(left: str, right: str) -> int:
    if len(left) > len(right):
        left, right = right, left
    previous = list(range(len(left) + 1))
    for right_index, right_character in enumerate(right, start=1):
        current = [right_index]
        for left_index, left_character in enumerate(left, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[left_index] + 1,
                    previous[left_index - 1] + (left_character != right_character),
                )
            )
        previous = current
    return previous[-1]


def _align_reference_candidates(
    raw_lines: list[str], reference: str
) -> list[tuple[str, float, int, int]]:
    """Greedily align ordered OCR columns to a nearby reference span."""

    pointer = 0
    has_alignment = False
    output: list[tuple[str, float, int, int]] = []
    for raw_line in raw_lines:
        normalized = _cjk_text(raw_line)
        if not normalized:
            output.append(("", 0.0, pointer, pointer))
            continue
        best: tuple[float, int, int, str, float] | None = None
        min_length = max(1, len(normalized) - 8)
        max_length = len(normalized) + 10
        if has_alignment:
            starts = range(max(0, pointer - 4), min(len(reference), pointer + 80) + 1)
        else:
            # A retained page may start halfway through a section because a
            # preceding column was deleted as noise or fell on an earlier scan.
            starts = range(0, len(reference) + 1)
        for start in starts:
            for length in range(min_length, max_length + 1):
                end = min(len(reference), start + length)
                candidate = reference[start:end]
                if not candidate:
                    continue
                distance = _edit_distance(normalized, candidate)
                similarity = 1 - distance / max(len(normalized), len(candidate))
                gap_penalty = abs(start - pointer) * 0.003 if has_alignment else 0.0
                score = similarity - gap_penalty
                if best is None or score > best[0]:
                    best = (score, start, end, candidate, similarity)
        if best is None:
            output.append(("", 0.0, pointer, pointer))
            continue
        _, start, end, candidate, similarity = best
        output.append((candidate, max(0.0, min(1.0, similarity)), start, end))
        pointer = end
        has_alignment = True
    return output


def _crop_for_recognition(image: Image.Image, box: LabelBox) -> Image.Image:
    x_min, y_min, x_max, y_max = _bounds(box)
    padding = 8
    crop = image.crop(
        (
            max(0, math.floor(x_min) - padding),
            max(0, math.floor(y_min) - padding),
            min(image.width, math.ceil(x_max) + padding),
            min(image.height, math.ceil(y_max) + padding),
        )
    ).convert("RGB")
    if crop.height > crop.width * 1.2:
        crop = crop.rotate(90, expand=True)
    return ImageOps.expand(crop, border=6, fill="white")


def _result_payload(item: Any) -> dict[str, Any]:
    payload = getattr(item, "json", item)
    if callable(payload):
        payload = payload()
    if not isinstance(payload, dict):
        raise ConversionError("text recognition returned a non-object result")
    if isinstance(payload.get("res"), dict):
        payload = payload["res"]
    return cast(dict[str, Any], payload)


def _recognition_fingerprint(page: PageRecord, box: LabelBox) -> str:
    payload = json.dumps(
        {
            "image_sha256": page.sha256,
            "points": box.points,
            "transcription": box.transcription,
            "model": SERVER_MODEL,
            "input_shape": SERVER_INPUT_SHAPE,
            "rotation": "vertical_ccw_90_v1",
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _run_server_recognition(
    work: list[tuple[PageRecord, int, LabelBox]],
    *,
    project_root: Path,
    device: str,
    batch_size: int,
    engine: RecognitionEngine | None = None,
    cache_path: Path | None = None,
) -> dict[tuple[str, int], dict[str, Any]]:
    cache_items: dict[str, Any] = {}
    if cache_path is not None and cache_path.is_file():
        try:
            cache_payload = json.loads(cache_path.read_text(encoding="utf-8"))
            if (
                isinstance(cache_payload, dict)
                and cache_payload.get("model") == SERVER_MODEL
                and cache_payload.get("input_shape") == list(SERVER_INPUT_SHAPE)
                and isinstance(cache_payload.get("items"), dict)
            ):
                cache_items = cast(dict[str, Any], cache_payload["items"])
        except (OSError, json.JSONDecodeError):
            cache_items = {}

    results: dict[tuple[str, int], dict[str, Any]] = {}
    pending: list[tuple[PageRecord, int, LabelBox]] = []
    for page, box_index, box in work:
        cache_key = f"{page.page_id}-b{box_index:03d}"
        cached = cache_items.get(cache_key)
        fingerprint = _recognition_fingerprint(page, box)
        if isinstance(cached, dict) and cached.get("fingerprint") == fingerprint:
            results[(page.page_id, box_index)] = {
                "text": str(cached.get("text", "")),
                "confidence": float(cached.get("confidence", 0.0)),
                "latency_ms": float(cached.get("latency_ms", 0.0)),
                "cache_hit": True,
            }
        else:
            pending.append((page, box_index, box))

    if not pending:
        return results

    if engine is None:
        try:
            from paddleocr import TextRecognition  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ConversionError(
                "PaddleOCR runtime is required for --run-server-ocr"
            ) from exc
        engine = TextRecognition(
            model_name=SERVER_MODEL,
            device=device,
            input_shape=SERVER_INPUT_SHAPE,
        )
    for start in range(0, len(pending), batch_size):
        batch = pending[start : start + batch_size]
        arrays: list[Any] = []
        for page, _, box in batch:
            image_path = (project_root / page.image_path).resolve()
            with Image.open(image_path) as image:
                crop = _crop_for_recognition(image, box)
                try:
                    import numpy as np  # type: ignore[import-not-found]
                except ImportError as exc:
                    raise ConversionError("PaddleOCR runtime requires numpy") from exc
                arrays.append(np.asarray(crop))
        started = time.perf_counter_ns()
        raw_results = list(engine.predict(arrays, batch_size=batch_size))
        latency_ms = (time.perf_counter_ns() - started) / 1_000_000
        if len(raw_results) != len(batch):
            raise ConversionError("text recognition result count does not match inputs")
        per_item_latency = latency_ms / max(1, len(batch))
        for (page, box_index, box), raw_result in zip(batch, raw_results, strict=True):
            payload = _result_payload(raw_result)
            text = str(payload.get("rec_text", ""))
            try:
                score = float(payload.get("rec_score", 0.0))
            except (TypeError, ValueError) as exc:
                raise ConversionError("text recognition score is invalid") from exc
            results[(page.page_id, box_index)] = {
                "text": text,
                "confidence": max(0.0, min(1.0, score)),
                "latency_ms": per_item_latency,
                "cache_hit": False,
            }
            cache_items[f"{page.page_id}-b{box_index:03d}"] = {
                "fingerprint": _recognition_fingerprint(page, box),
                "text": text,
                "confidence": max(0.0, min(1.0, score)),
                "latency_ms": per_item_latency,
            }
        if cache_path is not None:
            _write_json_atomic(
                cache_path,
                {
                    "schema_version": "1.0",
                    "dataset_kind": "local_secondary_ocr_cache",
                    "evaluation_status": "not_evaluated",
                    "model": SERVER_MODEL,
                    "input_shape": list(SERVER_INPUT_SHAPE),
                    "items": cache_items,
                },
            )
    return results


def _normalized_bbox(box: LabelBox, page: PageRecord) -> dict[str, float]:
    x_min, y_min, x_max, y_max = _bounds(box)
    return {
        "x": x_min / page.width,
        "y": y_min / page.height,
        "width": (x_max - x_min) / page.width,
        "height": (y_max - y_min) / page.height,
    }


def generate_review_candidates(
    *,
    source_id: str = DEFAULT_SOURCE_ID,
    inventory_path: Path = INVENTORY_PATH,
    reference_path: Path = REFERENCE_PATH,
    output_path: Path = OUTPUT_PATH,
    project_root: Path = PROJECT_ROOT,
    processed_root: Path = PROCESSED_ROOT,
    run_server_ocr: bool = False,
    device: str = "cpu",
    batch_size: int = 16,
    engine: RecognitionEngine | None = None,
) -> dict[str, Any]:
    if batch_size < 1 or batch_size > 128:
        raise ConversionError("batch_size must be between 1 and 128")
    pages = _load_inventory(
        inventory_path=inventory_path,
        project_root=project_root,
        processed_root=processed_root,
        source_id=source_id,
    )
    source_dir = _resolve_source_dir(processed_root, source_id)
    label_path = source_dir / "Label.txt"
    pages_by_key = {page.image_key: page for page in pages}
    labels = _parse_annotation_file(label_path, pages_by_key)
    reference_sections, reference_payload = _load_reference(reference_path)

    work = [
        (page, box_index, box)
        for page in pages
        for box_index, box in enumerate(labels.get(page.image_key, []), start=1)
    ]
    server_results = (
        _run_server_recognition(
            work,
            project_root=project_root,
            device=device,
            batch_size=batch_size,
            engine=engine,
            cache_path=(SERVER_CACHE_PATH if run_server_ocr and engine is None else None),
        )
        if run_server_ocr or engine is not None
        else {}
    )

    classified: dict[tuple[str, int], tuple[str, str, float, str | None]] = {}
    body_by_section: dict[str, list[tuple[PageRecord, int, LabelBox]]] = {
        section: [] for section in SECTIONS
    }
    current_section: str | None = None
    for page in pages:
        page_number = _page_number(page)
        page_boxes = labels.get(page.image_key, [])
        for original_index in _reading_order_indices(page_boxes, page.width):
            box_index = original_index + 1
            anchored_section = SECTION_BODY_STARTS.get((page_number, box_index))
            if anchored_section is not None:
                current_section = anchored_section
            value = _classification(page_boxes[original_index], page=page, box_index=box_index)
            classified[(page.page_id, box_index)] = value
            if value[0] == "text" and value[1] == "body":
                if current_section is None:
                    raise ConversionError(
                        f"body box has no section anchor: {page.page_id} b{box_index:03d}"
                    )
                body_by_section[current_section].append(
                    (page, box_index, page_boxes[original_index])
                )

    reference_by_box: dict[
        tuple[str, int], tuple[str, str, float, int, int]
    ] = {}
    for section, section_work in body_by_section.items():
        reference_matches = _align_reference_candidates(
            [box.transcription for _, _, box in section_work],
            reference_sections[section],
        )
        for (page, box_index, _), match in zip(
            section_work, reference_matches, strict=True
        ):
            reference_by_box[(page.page_id, box_index)] = (section, *match)

    output_pages: list[dict[str, Any]] = []
    counts = {"text": 0, "caption": 0, "figure": 0, "annotation": 0}
    review_required = 0
    consensus_count = 0
    server_available = bool(server_results)
    for page in pages:
        page_number = _page_number(page)
        boxes = labels.get(page.image_key, [])
        ordered = _reading_order_indices(boxes, page.width)
        records: list[dict[str, Any]] = []
        for reading_order, original_index in enumerate(ordered, start=1):
            box = boxes[original_index]
            box_index = original_index + 1
            category, role, category_confidence, normalized_candidate = classified[
                (page.page_id, box_index)
            ]
            counts[category] += 1
            server = server_results.get((page.page_id, box_index))
            reference_match = reference_by_box.get((page.page_id, box_index))
            reference_section = reference_match[0] if reference_match else None
            reference_candidate = reference_match[1] if reference_match else None
            reference_confidence = reference_match[2] if reference_match else None
            section_candidate = normalized_candidate if role == "section_heading" else None
            title_candidate = normalized_candidate if role == "figure_title" else None
            candidates = [box.transcription]
            for candidate in (
                server["text"] if server else None,
                reference_candidate,
                section_candidate,
                title_candidate,
            ):
                if isinstance(candidate, str) and candidate and candidate not in candidates:
                    candidates.append(candidate)
            agreement_values = [
                _normalized_edit_similarity(_cjk_text(box.transcription), _cjk_text(value))
                for value in candidates[1:]
                if _cjk_text(value)
            ]
            agreement = max(agreement_values, default=1.0 if len(candidates) == 1 else 0.0)
            consensus_candidate, consensus_basis = _consensus_candidate(
                raw_text=box.transcription,
                server_text=server["text"] if server else None,
                reference_text=reference_candidate,
                normalized_candidate=normalized_candidate,
                role=role,
            )
            consensus_count += int(consensus_candidate is not None)
            needs_review = (
                category_confidence < 0.95
                or len(candidates) > 1
                or (server is not None and float(server["confidence"]) < 0.9)
            )
            review_required += int(needs_review)
            records.append(
                {
                    "box_id": f"{page.page_id}-b{box_index:03d}",
                    "original_box_index": box_index,
                    "reading_order": reading_order,
                    "raw_text": box.transcription,
                    "polygon": [[x, y] for x, y in box.points],
                    "bbox": _normalized_bbox(box, page),
                    "category_candidate": category,
                    "role_candidate": role,
                    "category_confidence": category_confidence,
                    "candidate_texts": candidates,
                    "server_ocr": server,
                    "reference_candidate": (
                        {
                            "text": reference_candidate,
                            "section": reference_section,
                            "alignment_confidence": reference_confidence,
                            "start": reference_match[3],
                            "end": reference_match[4],
                        }
                        if reference_match is not None
                        else None
                    ),
                    "normalized_candidate": normalized_candidate,
                    "agreement": agreement,
                    "consensus_candidate": consensus_candidate,
                    "consensus_basis": consensus_basis,
                    "needs_review": needs_review,
                    "verification_state": "inferred",
                }
            )

        figures = []
        for figure_index, seed in enumerate(FIGURE_SEEDS.get(page_number, ()), start=1):
            counts["figure"] += 1
            figures.append(
                {
                    "figure_id": f"{page.page_id}-f{figure_index:02d}",
                    "side": seed.side,
                    "bbox": {
                        "x": seed.bbox[0],
                        "y": seed.bbox[1],
                        "width": seed.bbox[2],
                        "height": seed.bbox[3],
                    },
                    "candidate_title": seed.candidate_title,
                    "caption_box_id": (
                        f"{page.page_id}-b{seed.caption_box_index:03d}"
                        if seed.caption_box_index is not None
                        else None
                    ),
                    "candidate_title_bbox": (
                        {
                            "x": seed.title_bbox[0],
                            "y": seed.title_bbox[1],
                            "width": seed.title_bbox[2],
                            "height": seed.title_bbox[3],
                        }
                        if seed.title_bbox is not None
                        else None
                    ),
                    "category_candidate": "figure",
                    "verification_state": "inferred",
                    "evidence": "visual_page_seed_v1",
                }
            )
        output_pages.append(
            {
                "page_id": page.page_id,
                "image_path": page.image_path,
                "image_sha256": page.sha256,
                "orientation_candidate": "vertical_right_to_left",
                "reading_order_review_state": "inferred",
                "boxes": records,
                "figures": figures,
            }
        )

    output: dict[str, Any] = {
        "schema_version": "1.0",
        "dataset_kind": "real_pilot_model_assisted_review_candidates",
        "evaluation_status": "not_evaluated",
        "pipeline_version": PIPELINE_VERSION,
        "source_id": source_id,
        "input_hashes": {
            "inventory_sha256": _sha256(inventory_path),
            "label_sha256": _sha256(label_path),
            "reference_sha256": _sha256(reference_path),
        },
        "providers": {
            "raw": {"provider": "PPOCRLabel", "model": "PP-OCRv5_mobile"},
            "secondary": {
                "provider": "PaddleOCR",
                "model": SERVER_MODEL,
                "input_shape": list(SERVER_INPUT_SHAPE),
                "available": server_available,
                "device": device if server_available else None,
            },
            "reference": {
                "source_name": reference_payload.get("source_name"),
                "source_url": reference_payload.get("source_url"),
                "retrieved_at": reference_payload.get("retrieved_at"),
                "status": "comparison_only",
            },
        },
        "statistics": {
            "pages": len(pages),
            "boxes": len(work),
            "figure_regions": counts["figure"],
            "category_candidates": counts,
            "needs_review": review_required,
            "consensus_candidates": consensus_count,
            "transcription_verified": 0,
            "caption_ground_truth_verified": 0,
        },
        "pages": output_pages,
        "disclaimer": (
            "All text, reading-order, region-class, and figure-title values in this "
            "artifact are inferred candidates. They must not be copied into corrected "
            "text or evaluation ground truth without scan-level human confirmation."
        ),
    }
    _write_json_atomic(output_path, output)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", default=DEFAULT_SOURCE_ID)
    parser.add_argument("--run-server-ocr", action="store_true")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()
    try:
        output = generate_review_candidates(
            source_id=args.source_id,
            run_server_ocr=args.run_server_ocr,
            device=args.device,
            batch_size=args.batch_size,
        )
    except ConversionError as exc:
        parser.error(str(exc))
    print(json.dumps(output["statistics"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
