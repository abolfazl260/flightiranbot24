"""Generate Play Store images using the same transparent emblem as the Android launcher.

Run: python scripts/generate_android_store_graphics.py --out android/dist/store
Pillow is required; no remote assets are downloaded.
"""
from argparse import ArgumentParser
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

NAVY = "#12394F"
TEAL = "#00BDA9"
WHITE = "#E9F4F5"
LAUNCHER_ART = (
    Path(__file__).resolve().parents[1]
    / "android/app/src/main/res/drawable-nodpi/ic_launcher_art.png"
)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    )
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def emblem(size: int) -> Image.Image:
    with Image.open(LAUNCHER_ART) as original:
        art = original.convert("RGBA")
    if art.getpixel((0, 0))[3] != 0:
        raise ValueError("Android launcher emblem must have a transparent outer background")
    return art.resize((size, size), Image.Resampling.LANCZOS)


def generate(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)

    icon = Image.new("RGBA", (512, 512), NAVY)
    icon.alpha_composite(emblem(512))
    icon.convert("RGB").save(output / "play-icon-512.png", optimize=True)

    feature = Image.new("RGBA", (1024, 500), NAVY)
    pen = ImageDraw.Draw(feature)
    pen.rounded_rectangle((42, 48, 436, 451), radius=50, fill="#17495F")
    feature.alpha_composite(emblem(395), (41, 51))
    pen = ImageDraw.Draw(feature)
    pen.text((490, 130), "Flight Iran Bot 24", font=font(49, bold=True), fill=WHITE)
    pen.text((493, 235), "Airport directory", font=font(31), fill="#BEE9E4")
    pen.text((493, 294), "Travel checklist", font=font(31), fill="#BEE9E4")
    pen.rounded_rectangle((493, 378, 866, 384), radius=3, fill=TEAL)
    feature.convert("RGB").save(output / "feature-graphic-1024x500.png", optimize=True)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("android/dist/store"))
    generate(parser.parse_args().out)
