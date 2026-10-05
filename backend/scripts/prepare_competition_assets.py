"""Render existing scans for documents and extend explicit AI evidence coverage."""
from __future__ import annotations

import json

from PIL import Image, ImageDraw

from scripts.release_bundle import MANIFEST, ROOT, manifest_at


def main() -> None:
    manifest = manifest_at(ROOT)
    out = ROOT / "output/competition/assets"
    out.mkdir(parents=True, exist_ok=True)
    contact = Image.new("RGB", (1200, 900), "white")
    draw = ImageDraw.Draw(contact)
    for index, figure in enumerate(manifest.figures):
        asset = next(a for a in manifest.assets if a.asset_id == figure.asset_id)
        with Image.open(ROOT / "backend/data/assets" / asset.relative_path) as source:
            b = figure.bbox
            crop = source.crop((round(b.x * source.width), round(b.y * source.height),
                                round((b.x + b.width) * source.width),
                                round((b.y + b.height) * source.height))).convert("RGB")
        crop.save(out / (figure.figure_id + ".jpg"), quality=90)
        crop.thumbnail((290, 250))
        x, y = (index % 4) * 300, (index // 4) * 300
        contact.paste(crop, (x, y + 25))
        draw.text((x + 5, y + 5), figure.figure_id, fill="black")
    contact.save(out / "contact.jpg")
    protocol = json.loads((ROOT / "backend/data/experiments/domestic-queries-v1.json").read_text(
        encoding="utf-8"))
    protocol["protocol_id"] = "domestic-fixed-queries-v2-spatial"
    protocol["disclaimer"] += " V2固定保留原24输入；仅扩展背景图AI证据与局部主张范围。"
    protocol["manifest_name"] = MANIFEST
    (ROOT / "backend/data/experiments/domestic-queries-v2.json").write_text(
        json.dumps(protocol, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
