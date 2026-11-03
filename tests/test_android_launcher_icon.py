"""Enforce consistent white-background WebP launcher resources without Pillow dependencies."""
from pathlib import Path
from struct import unpack
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "android/app/src/main/res"
ANDROID = "{http://schemas.android.com/apk/res/android}"


def test_launcher_image_is_square_optimized_webp():
    data = (RES / "drawable-nodpi/ic_launcher_brand.webp").read_bytes()
    assert data[:4] == b"RIFF"
    assert data[8:12] == b"WEBP"
    assert data[12:16] == b"VP8 "  # Opaque WebP; Android provides the white background.
    assert unpack("<I", data[4:8])[0] == len(data) - 8
    # Lossy WebP VP8 frame header stores 14-bit width and height at 26..29.
    assert data[23:26] == b"\x9d\x01\x2a"
    width = unpack("<H", data[26:28])[0] & 0x3FFF
    height = unpack("<H", data[28:30])[0] & 0x3FFF
    assert (width, height) == (512, 512)
    assert len(data) < 32_768


def test_all_launcher_variants_use_same_white_background_image():
    manifest = ElementTree.parse(ROOT / "android/app/src/main/AndroidManifest.xml")
    application = manifest.find("application")
    assert application is not None
    assert application.attrib[ANDROID + "icon"] == "@drawable/ic_launcher"
    assert application.attrib[ANDROID + "roundIcon"] == "@drawable/ic_launcher"

    legacy = ElementTree.parse(RES / "drawable/ic_launcher.xml").getroot()
    assert legacy.tag == "layer-list"
    items = legacy.findall("item")
    assert len(items) == 2
    assert items[0].attrib[ANDROID + "drawable"] == "@color/white"
    bitmap = items[1].find("bitmap")
    assert bitmap is not None
    assert bitmap.attrib[ANDROID + "src"] == "@drawable/ic_launcher_brand"
    assert bitmap.attrib[ANDROID + "gravity"] == "fill"

    adaptive = ElementTree.parse(RES / "drawable-anydpi-v26/ic_launcher.xml").getroot()
    assert adaptive.tag == "adaptive-icon"
    assert adaptive.find("background").attrib[ANDROID + "drawable"] == "@color/white"
    assert (
        adaptive.find("foreground").attrib[ANDROID + "drawable"]
        == "@drawable/ic_launcher_foreground"
    )

    foreground = ElementTree.parse(RES / "drawable/ic_launcher_foreground.xml").getroot()
    assert foreground.tag == "inset"
    assert foreground.attrib[ANDROID + "drawable"] == "@drawable/ic_launcher_brand"
    assert foreground.attrib[ANDROID + "inset"] == "12dp"


def test_store_art_uses_the_launcher_image():
    source = (ROOT / "scripts/generate_android_store_graphics.py").read_text()
    assert "drawable-nodpi/ic_launcher_brand.webp" in source
    assert "Image.open(LAUNCHER_ART)" in source
    assert "Image.new(\"RGBA\", (512, 512), \"white\")" in source
