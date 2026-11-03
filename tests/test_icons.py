"""Bundled icon completeness and the unchanged official music SVG."""

import hashlib
import json
import os
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from fluentpy import FluentIcon, fluent_icon, fluent_icon_name
from fluentpy.qt import QtWidgets

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "src" / "fluentpy" / "assets" / "icons"
MUSIC_DIGEST = "6dacdfca1f1d955e41ef48412b3fb9e8567120ee17cee6f3ed1c4563170e34aa"
MUSIC_COMMIT = "a347af95478f989038cccbf085978865264c048a"


class IconTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_all_public_enums_match_bundled_assets_and_preserve_microsoft_icons(self):
        enums = list(FluentIcon)
        files = {path.name for path in ASSETS.glob("ic_fluent_*_24_regular.svg")}
        self.assertEqual(len(files), 2624)
        self.assertEqual(len(enums), 2625)
        self.assertEqual(files | {FluentIcon.LEAF.value}, {icon.value for icon in enums})
        self.assertEqual(enums[enums.index(FluentIcon.MONEY) + 1], FluentIcon.MUSIC_NOTE_2)

    def test_music_svg_is_the_unchanged_pinned_official_asset(self):
        data = (ASSETS / FluentIcon.MUSIC_NOTE_2.value).read_bytes()
        self.assertEqual(len(data), 1076)
        self.assertEqual(hashlib.sha256(data).hexdigest(), MUSIC_DIGEST)
        root = ET.fromstring(data)
        self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
        self.assertEqual(root.attrib["viewBox"], "0 0 24 24")
        self.assertEqual((root.attrib["width"], root.attrib["height"]), ("24", "24"))
        paths = root.findall("{http://www.w3.org/2000/svg}path")
        self.assertTrue(paths)
        self.assertTrue(all(path.attrib.get("d") for path in paths))

    def test_music_icon_renders_through_the_public_loader(self):
        for argument in (FluentIcon.MUSIC_NOTE_2, FluentIcon.MUSIC_NOTE_2.value):
            icon = fluent_icon(argument)
            self.assertFalse(icon.isNull())
            pixmap = icon.pixmap(24, 24)
            self.assertFalse(pixmap.isNull())
            image = pixmap.toImage()
            self.assertTrue(
                any(
                    image.pixelColor(x, y).alpha()
                    for y in range(image.height())
                    for x in range(image.width())
                )
            )
            self.assertEqual(fluent_icon_name(argument), "Music Note 2")

    def test_provenance_and_complete_microsoft_license_are_retained(self):
        source = (ASSETS / "SOURCE.md").read_text(encoding="utf-8")
        notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
        license_text = (ROOT / "licenses" / "Microsoft-Fluent-System-Icons-LICENSE.txt").read_text(
            encoding="utf-8"
        )
        self.assertIn(MUSIC_COMMIT, source)
        self.assertIn(MUSIC_DIGEST, source)
        self.assertIn("2624 regular 24px SVG icons", source)
        self.assertIn("2624 icons", notices)
        self.assertIn("MUSIC_NOTE_2", notices)
        self.assertIn("Permission is hereby granted, free of charge", license_text)
        self.assertIn('THE SOFTWARE IS PROVIDED "AS IS"', license_text)

    def test_complete_catalog_has_reproducible_sources_and_hashes(self):
        manifest = json.loads((ASSETS / "UPSTREAM.json").read_text("utf-8"))
        self.assertEqual(manifest["commit"], "9eb184e96268d3293462f9d9d19225b4c7b07774")
        self.assertEqual(manifest["license"], "MIT")
        self.assertEqual(len(manifest["icons"]), 2624)
        preserved = []
        for filename, entry in manifest["icons"].items():
            data = (ASSETS / filename).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), entry["sha256"], filename)
            self.assertEqual(getattr(FluentIcon, entry["enum"]).value, filename)
            if entry["matches_snapshot"]:
                blob = hashlib.sha1(
                    b"blob " + str(len(data)).encode("ascii") + b"\0" + data
                ).hexdigest()
                self.assertEqual(blob, entry["upstream_git_blob"], filename)
            else:
                preserved.append(filename)
            self.assertFalse(fluent_icon(filename).pixmap(24, 24).isNull(), filename)
        self.assertEqual(
            sorted(preserved), ["ic_fluent_code_24_regular.svg", "ic_fluent_copy_24_regular.svg"]
        )
        self.assertEqual(FluentIcon.TEXT_BOLD_RU.value, "ic_fluent_text_bold_ru_24_regular.svg")
        self.assertNotEqual(FluentIcon.LEAF_ONE.value, FluentIcon.LEAF.value)
        self.assertTrue((ROOT / "licenses/Microsoft-Fluent-System-Icons-NOTICE.txt").is_file())

    def test_eyedropper_asset_matches_official_download_and_renders(self):
        data = (ASSETS / FluentIcon.EYEDROPPER.value).read_bytes()
        self.assertEqual(
            hashlib.sha256(data).hexdigest(),
            "760f2318a6cca80a85e254428b843d97e4f3c974c2293c80ea1a11836e8b42ec",
        )
        self.assertFalse(fluent_icon(FluentIcon.EYEDROPPER).pixmap(24, 24).isNull())

    def test_leaf_is_a_packaged_vector_available_through_the_public_loader(self):
        path = ASSETS / FluentIcon.LEAF.value
        root = ET.fromstring(path.read_bytes())
        self.assertEqual(root.attrib["viewBox"], "0 0 24 24")
        self.assertTrue(root.findall("{http://www.w3.org/2000/svg}path"))
        self.assertFalse(root.findall(".//{http://www.w3.org/2000/svg}image"))
        for size in (16, 24, 48):
            self.assertFalse(fluent_icon(FluentIcon.LEAF).pixmap(size, size).isNull())
        self.assertEqual(fluent_icon_name(FluentIcon.LEAF), "Leaf")


if __name__ == "__main__":
    unittest.main()
