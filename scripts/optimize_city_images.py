#!/usr/bin/env python3
"""Rebuild lightweight Android city icons from archived original WebPs.

All originals are read-only. Output files are replaced atomically with the
same basenames under drawable-nodpi. Check results using the --check flag.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import os
from pathlib import Path
import sys
import tempfile

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "design-assets/cities/original"
DEST = ROOT / "android/app/src/main/res/drawable-nodpi"
PATTERN = "price_city_*.webp"


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def originals(source: Path, dest: Path, min_count: int) -> list[Path]:
    if not source.is_dir() or not dest.is_dir():
        raise ValueError("Both original and Android drawable directories must exist")
    if source.resolve() == dest.resolve():
        raise ValueError("Originals and optimized images must use different directories")
    src = sorted(source.glob(PATTERN))
    current = {p.name for p in dest.glob(PATTERN)}
    if len(src) < min_count:
        raise ValueError(f"Expected at least {min_count} originals, found {len(src)}")
    if len(src) != len({p.name for p in src}):
        raise ValueError("Original filenames must be unique")
    extra = current - {p.name for p in src}
    if extra:
        raise ValueError(f"Android images missing originals: {sorted(extra)}")
    return src


def encode_image(path: Path, size: int, quality: int) -> bytes:
    with Image.open(path) as source:
        if source.format != "WEBP":
            raise ValueError(f"Not WebP: {path.name}")
        has_transparency = "A" in source.getbands() or "transparency" in source.info
        image = ImageOps.exif_transpose(source).convert("RGBA")
        image.thumbnail((size, size), Image.Resampling.LANCZOS)
        if image.size != (size, size):
            canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            canvas.alpha_composite(image, ((size - image.width) // 2, (size - image.height) // 2))
            image = canvas
        if not has_transparency:
            image = image.convert("RGB")
        stream = io.BytesIO()
        image.save(stream, format="WEBP", quality=quality, method=4, lossless=False)
        return stream.getvalue()


def validate_image(path: Path, output: Path, size: int, max_bytes: int) -> int:
    if not output.is_file():
        raise ValueError(f"Missing output: {output.name}")
    output_bytes = output.stat().st_size
    if not 0 < output_bytes < min(path.stat().st_size, max_bytes + 1):
        raise ValueError(f"Output too large or not smaller than original: {output.name} ({output_bytes} B)")
    with Image.open(path) as original, Image.open(output) as optimized:
        if optimized.format != "WEBP" or optimized.size != (size, size):
            raise ValueError(f"Invalid output format/dimensions: {output.name}")
        if "A" in original.getbands() and "A" not in optimized.getbands():
            raise ValueError(f"Alpha channel missing: {output.name}")
        if "A" in original.getbands() and original.getchannel("A").getextrema()[0] == 0:
            if optimized.getchannel("A").getextrema()[0] != 0:
                raise ValueError(f"Transparent pixels lost: {output.name}")
        optimized.load()
    return output_bytes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--dest", type=Path, default=DEST)
    parser.add_argument("--size", type=int, default=512)
    parser.add_argument("--quality", type=int, default=88)
    parser.add_argument("--min-count", type=int, default=56)
    parser.add_argument("--max-bytes", type=int, default=300_000)
    parser.add_argument("--check", action="store_true", help="Validate without modifying images")
    args = parser.parse_args()
    if not (128 <= args.size <= 2048 and 1 <= args.quality <= 100 and args.max_bytes > 0):
        parser.error("Invalid size, quality or maximum file size")

    src = originals(args.source, args.dest, args.min_count)
    original_digests = {p.name: checksum(p) for p in src}
    total_before = sum(p.stat().st_size for p in src)
    total_after = 0
    for path in src:
        destination = args.dest / path.name
        if not args.check:
            content = encode_image(path, args.size, args.quality)
            if len(content) >= min(path.stat().st_size, args.max_bytes + 1):
                raise ValueError(f"Optimized image still too large: {path.name}")
            temp_name = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="wb", suffix=".webp", prefix=".city-", dir=args.dest, delete=False
                ) as temporary:
                    temp_name = temporary.name
                    temporary.write(content)
                os.replace(temp_name, destination)
            finally:
                if temp_name is not None and os.path.exists(temp_name):
                    os.unlink(temp_name)
        total_after += validate_image(path, destination, args.size, args.max_bytes)

    for path in src:
        if checksum(path) != original_digests[path.name]:
            raise ValueError(f"An original was modified: {path.name}")
    ratio = 100 * (total_before - total_after) / total_before
    action = "Verified" if args.check else "Optimized"
    print(
        f"{action} {len(src)} city images: {total_before / 1_000_000:.2f} MB -> "
        f"{total_after / 1_000_000:.2f} MB ({ratio:.1f}% smaller). "
        "Original archive unchanged."
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
