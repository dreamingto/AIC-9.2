"""Input and filesystem security helpers used by the API and ingestion paths."""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import Settings
from app.core.errors import DomainError

ALLOWED_IMAGE_MIME = {"image/png", "image/jpeg", "image/webp", "image/gif"}


@dataclass(frozen=True, slots=True)
class ImageInfo:
    mime_type: str
    width: int | None
    height: int | None


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _detect_magic(content: bytes) -> str | None:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"RIFF") and len(content) >= 12 and content[8:12] == b"WEBP":
        return "image/webp"
    if content.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    return None


def validate_image_bytes(
    content: bytes, declared_mime: str | None, settings: Settings
) -> ImageInfo:
    """Validate size, magic bytes, declared MIME and actual raster decoding."""

    if not content:
        raise DomainError("INVALID_IMAGE", "图片内容为空", 422)
    if len(content) > settings.max_upload_bytes:
        raise DomainError("INVALID_IMAGE", "图片超过大小限制", 413)
    if declared_mime and declared_mime not in ALLOWED_IMAGE_MIME:
        raise DomainError("INVALID_IMAGE", "不支持的图片类型", 422)
    detected = _detect_magic(content)
    if detected is None:
        raise DomainError("INVALID_IMAGE", "无法识别图片格式", 422)
    if declared_mime and declared_mime != detected:
        raise DomainError("INVALID_IMAGE", "声明的图片类型与文件内容不一致", 422)
    try:
        # Verify first, then reopen to obtain dimensions.  This catches files
        # with a valid header but truncated/corrupt encoded data.
        with Image.open(io.BytesIO(content)) as image:
            image.verify()
        with Image.open(io.BytesIO(content)) as image:
            width, height = image.size
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise DomainError("INVALID_IMAGE", "图片文件损坏或无法解码", 422) from exc
    if width <= 0 or height <= 0 or width * height > settings.max_image_pixels:
        raise DomainError("INVALID_IMAGE", "图片像素数超过限制", 413)
    return ImageInfo(detected, width, height)


def sanitize_image_bytes(content: bytes, detected_mime: str | None = None) -> bytes:
    """Orient and re-encode a raster image as metadata-free PNG.

    ``detected_mime`` is accepted for API symmetry and future policy checks;
    decoding still relies on Pillow rather than the caller's MIME header.
    """

    del detected_mime
    try:
        with Image.open(io.BytesIO(content)) as source:
            source.load()
            oriented = ImageOps.exif_transpose(source)
            rgb = oriented.convert("RGB")
            if oriented is not source:
                oriented.close()
        output = io.BytesIO()
        rgb.save(output, format="PNG", optimize=False)
        rgb.close()
        return output.getvalue()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise DomainError("INVALID_IMAGE", "图片文件损坏或无法解码", 422) from exc


def resolve_safe_path(root: Path, relative_path: str) -> Path:
    """Resolve a relative resource and prove it remains under ``root``."""

    root_resolved = root.expanduser().resolve(strict=False)
    candidate = (root_resolved / relative_path).resolve(strict=False)
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise DomainError("INVALID_ASSET_PATH", "资源路径不合法", 422) from exc
    return candidate
