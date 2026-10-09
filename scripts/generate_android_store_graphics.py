"""Generate deterministic store graphics matching the native launcher palette.

Run: python -m pip install Pillow
     python scripts/generate_android_store_graphics.py --out android/dist/store
"""
from argparse import ArgumentParser
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

NAVY = "#12394F"
TEAL = "#00BDA9"
WHITE = "#E9F4F5"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    )
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def symbol(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float) -> None:
    def point(u: float, v: float) -> tuple[int, int]:
        return (round(x + u * scale), round(y + v * scale))

    globe = [point(20, 20), point(88, 88)]
    draw.ellipse(globe, outline=WHITE, width=round(4 * scale))
    draw.line([point(20, 54), point(88, 54)], fill=WHITE, width=round(3 * scale))
    draw.line([point(54, 20), point(54, 88)], fill=WHITE, width=round(3 * scale))
    draw.arc([point(33, 20), point(75, 88)], 75, 285,
             fill=WHITE, width=round(3 * scale))
    draw.arc([point(33, 20), point(75, 88)], 255, 105,
             fill=WHITE, width=round(3 * scale))
    plane = [(19, 51), (50, 45), (76, 21), (84, 25),
             (64, 55), (86, 67), (82, 74), (53, 66),
             (36, 80), (30, 77), (40, 57), (21, 59)]
    draw.polygon([point(a, b) for a, b in plane], fill=TEAL)


def generate(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    icon = Image.new("RGB", (512, 512), NAVY)
    symbol(ImageDraw.Draw(icon), 0, 0, 512 / 108)
    icon.save(output / "play-icon-512.png", optimize=True)

    feature = Image.new("RGB", (1024, 500), NAVY)
    pen = ImageDraw.Draw(feature)
    pen.rounded_rectangle((42, 48, 436, 451), radius=50, fill="#17495F")
    symbol(pen, 40, 49, 395 / 108)
    pen.text((490, 130), "Flight Iran Bot 24", font=font(49, bold=True), fill=WHITE)
    pen.text((493, 235), "Airport directory", font=font(31), fill="#BEE9E4")
    pen.text((493, 294), "Travel checklist", font=font(31), fill="#BEE9E4")
    pen.rounded_rectangle((493, 378, 866, 384), radius=3, fill=TEAL)
    feature.save(output / "feature-graphic-1024x500.png", optimize=True)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("android/dist/store"))
    generate(parser.parse_args().out)
