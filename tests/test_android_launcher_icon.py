"""Enforce consistent transparent launcher resources without Pillow dependencies."""
from pathlib import Path
from struct import unpack
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "android/app/src/main/res"
ANDROID = "{http://schemas.android.com/apk/res/android}"


def test_launcher_image_is_square_png_with_alpha():
    data = (RES / "drawable-nodpi/ic_launcher_art.png").read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    width, height, depth, color, *_ = unpack(">IIBBBBB", data[16:29])
    assert width == height and width >= 192
    assert depth == 8
    assert color in (3, 4, 6)
    if color == 3:
        assert b"tRNS" in data  # transparency in indexed PNGs


def test_all_launcher_variants_use_the_same_unframed_image():
    manifest = ElementTree.parse(ROOT / "android/app/src/main/AndroidManifest.xml")
    application = manifest.find("application")
    assert application is not None
    assert application.attrib[ANDROID + "icon"] == "@drawable/ic_launcher"
    assert application.attrib[ANDROID + "roundIcon"] == "@drawable/ic_launcher"

    legacy = ElementTree.parse(RES / "drawable/ic_launcher.xml").getroot()
    assert legacy.tag == "bitmap"
    assert legacy.attrib[ANDROID + "src"] == "@drawable/ic_launcher_art"

    adaptive = ElementTree.parse(RES / "drawable-anydpi-v26/ic_launcher.xml").getroot()
    assert adaptive.tag == "adaptive-icon"
    assert adaptive.find("background").attrib[ANDROID + "drawable"] == "@android:color/transparent"
    assert (\n        adaptive.find("foreground").attrib[ANDROID + "drawable"]\n        == "@drawable/ic_launcher_foreground"\n    )

    foreground = ElementTree.parse(RES / "drawable/ic_launcher_foreground.xml").getroot()
    assert foreground.tag == "inset"
    assert foreground.attrib[ANDROID + "drawable"] == "@drawable/ic_launcher_art"
    assert foreground.attrib[ANDROID + "inset"] == "18dp"


def test_store_art_uses_the_launcher_image():
    source = (ROOT / "scripts/generate_android_store_graphics.py").read_text()
    assert "drawable-nodpi/ic_launcher_art.png" in source
    assert "Image.open(LAUNCHER_ART)" in source
