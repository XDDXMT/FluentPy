"""The drop policy preserves behavior in C and Python modes."""

import os
import unittest
from unittest.mock import patch

from fluentpy.backends import drop


class DropBackendTests(unittest.TestCase):
    def test_suffix_normalization_and_validation(self):
        self.assertEqual(
            drop.normalize_extensions([" JPG ", "*.PNG", ".gif", ".png", ".tar.gz"]),
            (".jpg", ".png", ".gif", ".tar.gz"),
        )
        self.assertEqual(drop.normalize_extensions(["*"]), ())
        self.assertEqual(drop.normalize_extensions(["*.*", ".png"]), ())
        self.assertEqual(drop.normalize_extensions([]), ())
        for value in (".png", b".png", None, [1], [None]):
            with self.subTest(value=value), self.assertRaises(TypeError):
                drop.normalize_extensions(value)
        for value in ([""], ["."], ["p/ng"], ["p\\ng"], [".p?g"], [".p*g"], [".p ng"], [".p\0ng"]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                drop.normalize_extensions(value)

    def test_batch_filtering_order_and_all_rejection_reasons(self):
        paths = [
            ("图片 😀.PNG", 1),
            ("data.txt", 1),
            ("相册", 2),
            ("lost.jpg", 0),
            ("pipe.jpg", 3),
            ("图片 😀.PNG", 1),
            ("", 1),
            ("nul\0.png", 1),
        ]
        accepted, rejected = drop.filter_paths(paths, ["png", "jpg"])
        self.assertEqual(accepted, [("图片 😀.PNG", 1), ("相册", 2)])
        self.assertEqual(
            [reason for _path, reason in rejected],
            ["extension", "missing", "type", "duplicate", "invalid", "invalid"],
        )
        accepted, rejected = drop.filter_paths(paths, [], allow_files=False, multiple=False)
        self.assertEqual(accepted, [("相册", 2)])
        self.assertIn(("图片 😀.PNG", "type"), rejected)

    def test_single_selection_skips_invalid_before_first_valid(self):
        accepted, rejected = drop.filter_paths(
            [("a.txt", 1), ("b.PNG", 1), ("c.gif", 1)], ["png", "gif"], multiple=False
        )
        self.assertEqual(accepted, [("b.PNG", 1)])
        self.assertEqual(rejected, [("a.txt", "extension"), ("c.gif", "multiple")])

    def test_case_sensitive_paths_and_case_insensitive_suffixes(self):
        paths = [("Image.JPG", 1), ("image.jpg", 1)]
        self.assertEqual(len(drop.filter_paths(paths, ["JPG"], case_sensitive=True)[0]), 2)
        self.assertEqual(
            drop.filter_paths(paths, ["JPG"], case_sensitive=False),
            ([("Image.JPG", 1)], [("image.jpg", "duplicate")]),
        )

    def test_large_batch_is_not_truncated(self):
        candidates = [(f"C:/相册/照片 {index} 😀.png", 1) for index in range(10000)]
        accepted, rejected = drop.filter_paths(candidates + candidates, ["png"])
        self.assertEqual(accepted, candidates)
        self.assertEqual(len(rejected), 10000)
        self.assertEqual({reason for _path, reason in rejected}, {"duplicate"})

    def test_malformed_metadata_is_an_error_not_a_partial_result(self):
        for candidate in (
            ["path"],
            [("path",)],
            [("path", 1, 2)],
            [(3, 1)],
            [("path", True)],
            [("path", 4)],
            [("path", -1)],
        ):
            with self.subTest(candidate=candidate), self.assertRaises((TypeError, ValueError)):
                drop.filter_paths(candidate, [])

    def test_auto_falls_back_and_explicit_native_stays_strict(self):
        for backend in ("auto", "python"):
            with patch.dict(os.environ, {"FLUENTPY_BACKEND": backend}):
                self.assertEqual(drop.filter_paths([("a.png", 1)], ["png"])[0], [("a.png", 1)])
        with patch.object(drop, "_extension", None):
            with patch.dict(os.environ, {"FLUENTPY_BACKEND": "auto"}):
                self.assertEqual(drop.backend_name(), "python")
                self.assertEqual(drop.normalize_extensions(["png"]), (".png",))
            with patch.dict(os.environ, {"FLUENTPY_BACKEND": "native"}):
                with self.assertRaisesRegex(RuntimeError, "compiled.*drop backend.*Rebuild"):
                    drop.normalize_extensions(["png"])
