from __future__ import annotations

import json
import urllib.parse
from pathlib import Path

from scripts.download_naifu_reference import (
    SECTIONS,
    _extract_reference_text,
    download_reference,
)


def test_extract_reference_text_removes_mediawiki_wrappers() -> None:
    value = """
{{header|title=測試}}
<onlyinclude>
凡[[絲|絲線]]，{{small|旁註}}可用。<ref>來源</ref>
第二行
</onlyinclude>
{{PD-old}}
"""

    assert _extract_reference_text(value) == "凡絲線，可用。\n第二行"


def test_download_reference_keeps_provenance_and_warning(tmp_path: Path) -> None:
    seen: list[str] = []

    def fetcher(url: str) -> bytes:
        seen.append(url)
        titles = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["titles"][0].split(
            "|"
        )
        return json.dumps(
            {
                "query": {
                    "pages": [
                        {
                            "title": title,
                            "revisions": [
                                {
                                    "slots": {
                                        "main": {
                                            "content": "<onlyinclude>正文</onlyinclude>"
                                        }
                                    }
                                }
                            ],
                        }
                        for title in titles
                    ]
                }
            },
            ensure_ascii=False,
        ).encode()

    output_path = tmp_path / "reference.json"
    result = download_reference(output_path=output_path, fetcher=fetcher)

    assert len(seen) == 8
    assert len(result["sections"]) == len(SECTIONS)
    assert result["evaluation_status"] == "not_evaluated"
    assert "not scan ground truth" in result["disclaimer"]
    assert output_path.is_file()
