"""Native/reference differential coverage without importing Qt.

The namespace package below loads the real backend source and native binary
without executing fluentpy.__init__, whose widget exports normally import Qt.
Run directly with ``python -B -m unittest discover -s tests -p test_native_backend.py``.
"""

import importlib.util
import json
import os
import random
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

_SOURCE = Path(__file__).resolve().parents[1] / "src" / "fluentpy"
_NAMESPACE = "_fluentpy_accel_test_package"
_package = types.ModuleType(_NAMESPACE)
_package.__path__ = [str(_SOURCE)]
sys.modules[_NAMESPACE] = _package
_spec = importlib.util.spec_from_file_location(
    f"{_NAMESPACE}.backends",
    _SOURCE / "backends" / "__init__.py",
    submodule_search_locations=[str(_SOURCE / "backends")],
)
_backends = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _backends
_spec.loader.exec_module(_backends)
backend = sys.modules[f"{_NAMESPACE}.backends.text"]


class BackendSelectionTests(unittest.TestCase):
    def test_python_can_be_forced(self):
        with patch.dict(os.environ, {"FLUENTPY_BACKEND": "python"}):
            self.assertEqual(backend.backend_name(), "python")
            self.assertEqual(backend.json_spans('{"value": true}'), [(1, 7, 0), (10, 4, 3)])

    def test_auto_uses_native_when_available(self):
        with patch.dict(os.environ, {"FLUENTPY_BACKEND": "auto"}):
            self.assertEqual(
                backend.backend_name(), "native" if backend.native_available() else "python"
            )
            self.assertEqual(backend.json_spans("-1.5e+2"), [(0, 7, 2)])

    def test_missing_extension_falls_back_and_forced_mode_is_visible(self):
        with (
            patch.object(backend, "_extension", None),
            patch.object(backend, "_native_import_error", "test binary missing"),
        ):
            self.assertFalse(backend.native_available())
            self.assertEqual(backend.native_error(), "test binary missing")
            with patch.dict(os.environ, {"FLUENTPY_BACKEND": "auto"}):
                self.assertEqual(backend.backend_name(), "python")
                self.assertEqual(backend.json_spans("null"), [(0, 4, 3)])
            with patch.dict(os.environ, {"FLUENTPY_BACKEND": "native"}):
                with self.assertRaisesRegex(RuntimeError, "compiled fluentpy._native"):
                    backend.json_spans("null")
                with self.assertRaises(RuntimeError):
                    backend.backend_name()
            with self.assertRaises(RuntimeError):
                backend.json_spans_native("null")

    def test_real_import_without_a_binary_does_not_need_qt(self):
        namespace = "_fluentpy_missing_binary_test"
        package = types.ModuleType(namespace)
        package.__path__ = []  # Deliberately hide the compiled sibling module.
        subpackage = types.ModuleType(f"{namespace}.backends")
        subpackage.__path__ = [str(_SOURCE / "backends")]
        module_name = f"{namespace}.backends.text"
        with patch.dict(sys.modules, {namespace: package, subpackage.__name__: subpackage}):
            spec = importlib.util.spec_from_file_location(
                module_name, _SOURCE / "backends" / "text.py"
            )
            missing = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(missing)
            self.assertFalse(missing.native_available())
            self.assertIn("_native", missing.native_error())
            with patch.dict(os.environ, {"FLUENTPY_BACKEND": "auto"}):
                self.assertEqual(missing.json_spans("false"), [(0, 5, 3)])
            with patch.dict(os.environ, {"FLUENTPY_BACKEND": "native"}):
                with self.assertRaisesRegex(RuntimeError, "compiled fluentpy._native"):
                    missing.json_spans("false")

    def test_invalid_selection_is_rejected(self):
        with patch.dict(os.environ, {"FLUENTPY_BACKEND": "c-ish"}):
            with self.assertRaisesRegex(ValueError, "FLUENTPY_BACKEND"):
                backend.json_spans("1")

    def test_reference_rejects_non_string_arguments(self):
        for value in (None, 4, True, b"{}", [], {}):
            with self.subTest(value=value), self.assertRaises(TypeError):
                backend.json_spans_python(value)

    def test_reference_utf16_offsets_and_kind_ids(self):
        text = '🎵 {"a": "😀", "b": -1, "c": null}'
        expected = [(4, 3, 0), (9, 4, 1), (15, 3, 0), (20, 2, 2), (24, 3, 0), (29, 4, 3)]
        self.assertEqual(backend.json_spans_python(text), expected)


@unittest.skipUnless(
    backend.native_available(), "native extension is not built for this interpreter"
)
class NativeScannerTests(unittest.TestCase):
    def assert_same(self, source):
        expected = backend.json_spans_python(source)
        actual = backend.json_spans_native(source)
        self.assertEqual(actual, expected, repr(source))
        total = len(source.encode("utf-16-le", errors="surrogatepass")) // 2
        last_end = 0
        for start, length, kind in actual:
            self.assertGreaterEqual(start, last_end)
            self.assertGreater(length, 0)
            self.assertLessEqual(start + length, total)
            self.assertIn(kind, range(4))
            last_end = start + length

    def test_unicode_escaped_and_incomplete_input_matches_reference(self):
        samples = [
            "",
            "{}",
            "[]",
            '""',
            '{"": ""}',
            '"🎵": "😀"',
            '{"title": "🎵 true \\"quoted\\"", "gain": -1.5e+2, "ready": false}',
            '"unterminated',
            '"escaped\\"',
            '"tail\\',
            '"a\\\n"b"',
            '"a\nb" : 5',
            '"a\r\nb"\u2003: true',
            "true false null True FALSE NULL true_ xnull null中 true² ²null",
            "1 -2 0 -0 01 -01 1. 1..2 1.2 1e2 1e+2 1e- 1e+ 1e2. --2 .2 x2 2x",
            "1٢٣ 1.٢ 1e٢ ٢ ² 1² 𐒠1 1𐒠 1𐒠.٢",
            '\ud800 {"\udfff": "𐀀", "x": 3}\udfff',
            '\x00 "null"\x00 null\x00 1\x00 "a"\x00: 5',
            '"a"\u2028\u2029: "b"',
        ]
        for source in samples:
            with self.subTest(source=repr(source)):
                self.assert_same(source)

    def test_deterministic_malformed_input_fuzz(self):
        randomizer = random.Random(0xF1E17)
        alphabet = '"\\:,.{}[] -+0123456789eEtrufalsn_\n\r\t中é²٢🎵\ud800\udfff\x00\u2003'
        for _ in range(1200):
            source = "".join(randomizer.choices(alphabet, k=randomizer.randrange(0, 240)))
            self.assert_same(source)

    def test_structured_ten_thousand_line_document_matches_reference(self):
        # Pretty JSON with Unicode strings, not a repeated short ASCII token.
        source = json.dumps(
            [
                {"id": index, "name": f"音符 🎵 {index}", "ready": index % 2 == 0, "gain": -1.25e3}
                for index in range(2000)
            ],
            ensure_ascii=False,
            indent=2,
        )
        self.assertGreaterEqual(source.count("\n"), 10_000)
        self.assert_same(source)

    def test_subclasses_and_lone_surrogates_are_safe(self):
        class StringSubclass(str):
            pass

        for source in (StringSubclass('{"x": 1}'), "\ud800", '"\ud800\udfff": 1', '😀 "a" : "😀"'):
            self.assert_same(source)

    def test_many_escaped_quotes_in_unfinished_string(self):
        # Every quote is a possible opening after the first candidate fails.
        # Keep the oracle small (its regex backtracking is quadratic), then
        # exercise a large suffix directly without a timing-dependent assert.
        self.assert_same('"' + '\\"' * 300)
        source = '"' + '\\"' * 50_000
        self.assertEqual(backend.json_spans_native(source), [])

    def test_invalid_native_arguments_and_arity(self):
        for value in (None, 4, True, b"{}", [], {}):
            with self.subTest(value=value), self.assertRaises(TypeError):
                backend.json_spans_native(value)
        with self.assertRaises(TypeError):
            backend._extension.json_spans()
        with self.assertRaises(TypeError):
            backend._extension.json_spans("", "")


if __name__ == "__main__":
    unittest.main()
