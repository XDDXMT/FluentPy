"""Verify the static documentation, assets, public names and Python examples."""
import ast
import contextlib
import io
import json
import os
import sys
from pathlib import Path
from PIL import Image, ImageChops

os.environ["QT_QPA_PLATFORM"] = "offscreen"
SITE = Path(__file__).resolve().parent
ROOT = SITE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
import fluentpy
from fluentpy import FluentWindow
from fluentpy.qt import QtCore, QtGui, QtWidgets

data = json.loads((SITE / "dist" / "data.js").read_text(encoding="utf-8").removeprefix("window.DOCS_DATA = ").rstrip(";\n"))
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
app.setQuitOnLastWindowClosed(False)
retained = []
errors = []
sys.excepthook = lambda kind, error, traceback: errors.append(str(error))
checked = 0
animated_previews = data.get("animatedPreviews", {})
for name, media in animated_previews.items():
    directory = SITE / "dist" / "assets" / "previews"
    with Image.open(directory / media["image"]) as animation, Image.open(directory / media["poster"]) as poster:
        expected_size = (media["width"], media["height"])
        assert animation.format == "GIF" and animation.n_frames >= 6, name
        assert animation.size == poster.size == expected_size, name
        assert animation.info.get("loop") == 0, name
        first = animation.convert("RGB")
        durations, changed = [], False
        for index in range(animation.n_frames):
            animation.seek(index)
            durations.append(animation.info.get("duration", 0))
            changed |= ImageChops.difference(first, animation.convert("RGB")).getbbox() is not None
        assert all(duration > 0 for duration in durations) and changed, name
        print(f"Validated {name}: {animation.n_frames} GIF frames, {sum(durations)} ms, {expected_size}")
for name in data["api"]:
    assert hasattr(fluentpy, name), name
assert {icon["name"] for icon in data["icons"]} == {icon.name for icon in fluentpy.FluentIcon}
assert len({p["id"] for p in data["pages"]}) == len(data["pages"])
for group in data["groups"]:
    assert all(any(p["id"] == name for p in data["pages"]) for name in group["pages"])
for page in data["pages"]:
    if page.get("cover"):
        cover = SITE / "dist" / "assets" / "previews" / f"{page['cover']['image']}-light.png"
        assert cover.exists() and cover.stat().st_size > 100, cover
    window = FluentWindow()
    context = {"window": window, "app": app, "QtCore": QtCore, "QtGui": QtGui, "QtWidgets": QtWidgets}
    for section in page["sections"]:
        for card in section.get("gallery", []):
            asset = SITE / "dist" / "assets" / "previews" / f"{card['image']}-light.png"
            assert asset.exists() and asset.stat().st_size > 100, asset
            assert any(p["id"] == card["page"] for p in data["pages"]), card
        for step in section.get("steps", []):
            assert any(p["id"] == step["page"] for p in data["pages"]), step
        preview = section["preview"]
        if preview and preview not in ("icons", "api-index"):
            if preview in animated_previews:
                assert animated_previews[preview]["image"].endswith("-light.gif"), preview
            else:
                asset = SITE / "dist" / "assets" / "previews" / f"{preview}-light.png"
                assert asset.exists() and asset.stat().st_size > 100, asset
        code = section["code"]
        if not code or section.get("language") == "PowerShell" or code.startswith(("git ", "python ")):
            continue
        parsed = ast.parse(code)
        # The browser shows complete app setup; this check reuses one QApplication.
        parsed.body = [node for node in parsed.body if "QApplication(" not in ast.unparse(node) and "sys.exit(" not in ast.unparse(node)]
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(parsed, f"{page['id']}/{section['id']}", "exec"), context)
        checked += 1
    retained.append(context)
for icon in data["icons"]:
    assert (SITE / "dist" / icon["file"]).exists(), icon
assert not errors, errors
print(f"Validated {len(data['pages'])} pages, {len(data['api'])} API entries, {checked} executable Python snippets, {len(data['icons'])} icons, {len(animated_previews)} animations and all Qt preview images.")
