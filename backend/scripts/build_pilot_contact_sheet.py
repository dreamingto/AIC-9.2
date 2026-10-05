"""Build a small local contact sheet from already rendered ancient-book scans."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw


def build_contact_sheet(directory: Path, output: Path, pattern: str = "page-*.png") -> None:
    paths = sorted(directory.glob(pattern))
    if not paths:
        raise ValueError("no rendered pages matched")
    columns, cell_w, cell_h = 4, 360, 300
    sheet = Image.new("RGB", (columns * cell_w, math.ceil(len(paths) / columns) * cell_h), "white")
    draw = ImageDraw.Draw(sheet)
    for index, path in enumerate(paths):
        x, y = index % columns * cell_w, index // columns * cell_h
        with Image.open(path) as source:
            thumb = source.convert("RGB")
            thumb.thumbnail((cell_w - 12, cell_h - 32))
            sheet.paste(thumb, (x + (cell_w - thumb.width) // 2, y + 25))
        draw.text((x + 8, y + 6), path.stem, fill="black")
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=90)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--pattern", default="page-*.png")
    args = parser.parse_args()
    build_contact_sheet(args.directory, args.output, args.pattern)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
