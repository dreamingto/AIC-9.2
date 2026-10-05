"""Download a provenance-rich public-domain reference text for OCR comparison.

The reference is a comparison aid from Wikisource, not a silent replacement
for the scanned edition.  Edition differences and Wikisource transcription
errors remain possible, so downstream code must keep every match as a model
candidate until a human confirms the scan glyphs.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import tempfile
import time
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from scripts.convert_ppocrlabel_annotations import PROJECT_ROOT, ConversionError

OUTPUT_PATH = (
    PROJECT_ROOT / "backend" / "data" / "real_pilot" / "naifu_wikisource_reference.json"
)
API_URL = "https://zh.wikisource.org/w/api.php"
PIPELINE_VERSION = "naifu-wikisource-reference-v1"
SECTIONS = (
    "乃服第二",
    "蠶種",
    "蠶浴",
    "種忌",
    "種類",
    "抱養",
    "養忌",
    "葉料",
    "食忌",
    "病癥",
    "老足",
    "結繭",
    "取繭",
    "物害",
    "擇繭",
    "造綿",
    "治絲",
    "調絲",
    "緯絡",
    "經具",
    "過糊",
    "邊維",
    "經數",
    "花機式",
    "腰機式",
    "結花本",
    "穿經",
    "分名",
    "熟練",
    "龍袍",
    "倭緞",
    "布衣",
    "枲著",
    "夏服",
    "裘",
    "褐 氊",
)


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _extract_reference_text(wikitext: str) -> str:
    onlyinclude = re.search(
        r"<onlyinclude>(.*?)</onlyinclude>", wikitext, flags=re.DOTALL | re.IGNORECASE
    )
    body = onlyinclude.group(1) if onlyinclude else wikitext
    body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
    body = re.sub(r"<ref\b.*?</ref>", "", body, flags=re.DOTALL | re.IGNORECASE)
    body = re.sub(r"<ref\b[^>]*/>", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\[\[(?:[^\]|]+\|)?([^\]]+)\]\]", r"\1", body)
    previous = None
    while previous != body:
        previous = body
        body = re.sub(r"\{\{[^{}]*\}\}", "", body, flags=re.DOTALL)
    body = re.sub(r"<[^>]+>", "", body)
    body = re.sub(r"'{2,}", "", body)
    lines = [line.strip() for line in html.unescape(body).splitlines()]
    return "\n".join(line for line in lines if line and not line.startswith("{{"))


def _fetch_bytes(url: str, *, proxy: str | None = None) -> bytes:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "zh.wikisource.org":
        raise ConversionError("reference URL is outside zh.wikisource.org")
    handlers: list[Any] = []
    if proxy:
        handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    opener = urllib.request.build_opener(*handlers)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "JiTu-Suoyin-Research/1.0 (public-domain OCR pilot)"},
    )
    last_error: OSError | None = None
    for attempt in range(3):
        try:
            with opener.open(request, timeout=60) as response:
                return cast(bytes, response.read())
        except OSError as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(attempt + 1)
    raise ConversionError(f"unable to download reference: {url}") from last_error


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            delete=False,
            suffix=".part",
            newline="\n",
        ) as temporary:
            temporary.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        temporary_path.replace(path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def download_reference(
    *,
    output_path: Path = OUTPUT_PATH,
    proxy: str | None = None,
    fetcher: Callable[[str], bytes] | None = None,
) -> dict[str, Any]:
    """Fetch all 乃服 sections and save a local comparison artifact."""

    fetch = fetcher or (lambda url: _fetch_bytes(url, proxy=proxy))
    titles = [f"天工開物/{section}" for section in SECTIONS]
    pages_by_title: dict[str, tuple[dict[str, Any], str, str]] = {}
    for start in range(0, len(titles), 5):
        batch_titles = titles[start : start + 5]
        query = urllib.parse.urlencode(
            {
                "action": "query",
                "format": "json",
                "formatversion": "2",
                "prop": "revisions",
                "rvprop": "content",
                "rvslots": "main",
                "titles": "|".join(batch_titles),
            }
        )
        url = f"{API_URL}?{query}"
        raw = fetch(url)
        try:
            payload = json.loads(raw.decode("utf-8"))
            raw_pages = payload["query"]["pages"]
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ConversionError("invalid Wikisource batch response") from exc
        if not isinstance(raw_pages, list):
            raise ConversionError("Wikisource batch pages must be an array")
        for raw_page in raw_pages:
            if not isinstance(raw_page, dict) or not isinstance(
                raw_page.get("title"), str
            ):
                continue
            page = cast(dict[str, Any], raw_page)
            pages_by_title[cast(str, page["title"])] = (
                page,
                url,
                _sha256_bytes(raw),
            )

    records: list[dict[str, Any]] = []
    for title in titles:
        page_record = pages_by_title.get(title)
        if page_record is None:
            raise ConversionError(f"Wikisource response is missing: {title}")
        page, batch_url, response_hash = page_record
        try:
            wikitext = page["revisions"][0]["slots"]["main"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ConversionError(f"invalid Wikisource response for: {title}") from exc
        if not isinstance(wikitext, str):
            raise ConversionError(f"Wikisource wikitext is not text for: {title}")
        text = _extract_reference_text(wikitext)
        if not text:
            raise ConversionError(f"Wikisource section is empty after parsing: {title}")
        records.append(
            {
                "title": title,
                "page_url": f"https://zh.wikisource.org/wiki/{urllib.parse.quote(title)}",
                "batch_api_url": batch_url,
                "batch_response_sha256": response_hash,
                "text": text,
            }
        )

    output: dict[str, Any] = {
        "schema_version": "1.0",
        "dataset_kind": "real_pilot_external_reference_text",
        "evaluation_status": "not_evaluated",
        "pipeline_version": PIPELINE_VERSION,
        "source_name": "Wikisource",
        "source_url": "https://zh.wikisource.org/wiki/天工開物",
        "license_status": "public_domain",
        "retrieved_at": datetime.now(UTC).isoformat(),
        "sections": records,
        "disclaimer": (
            "This transcription may use another edition and may contain community "
            "errors. It is context for candidate generation, not scan ground truth."
        ),
    }
    _write_json_atomic(output_path, output)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proxy", help="Optional HTTP(S) proxy, for example http://127.0.0.1:7890")
    args = parser.parse_args()
    try:
        output = download_reference(proxy=args.proxy)
    except ConversionError as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {
                "status": "downloaded",
                "sections": len(cast(list[Any], output["sections"])),
                "evaluation_status": output["evaluation_status"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
