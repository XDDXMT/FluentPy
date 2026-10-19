import importlib.util
import os
import random
import unittest
from unittest.mock import patch

from fluentpy.backends import _input_python as reference
from fluentpy.backends import input as backend


class InputBackendTests(unittest.TestCase):
    def test_segmentation_unicode_padding_and_truncation(self):
        self.assertEqual(backend.split_code("12", 4), ("1", "2", "", ""))
        self.assertEqual(backend.split_code("中文🙂A", 4, False), tuple("中文🙂A"))
        self.assertEqual(backend.split_code("123456", 4, truncate=True), tuple("1234"))

    def test_native_and_python_match_random_codes_and_invalid_inputs(self):
        native = backend._extension
        rng = random.Random(57)
        for _ in range(500):
            length = rng.randint(1, 32)
            text = "".join(rng.choice("0123456789") for _ in range(rng.randint(0, length)))
            self.assertEqual(backend.split_code(text, length), reference.split_code(text, length))
            if native is not None:
                self.assertEqual(
                    native.input_split_code(text, length), reference.split_code(text, length)
                )
        invalid = [
            (None, 4),
            ("x", 4),
            ("１２３", 4),
            ("a\n", 4, False),
            ("\ud800", 4, False),
            ("12345", 4),
            ("", 0),
            ("", 33),
            ("", True),
            ("", 10**300),
            ("", 4, 1),
            ("", 4, True, 1),
        ]
        for args in invalid:
            with self.subTest(args=repr(args)):
                with self.assertRaises((ValueError, TypeError)) as error:
                    reference.split_code(*args)
                if native is not None:
                    with self.assertRaises(type(error.exception)):
                        native.input_split_code(*args)

    def test_old_extension_fallback_and_explicit_native(self):
        for extension in (None, object()):
            with (
                patch("importlib.import_module", return_value=extension),
                patch.dict(os.environ, {"FLUENTPY_BACKEND": "auto"}),
            ):
                spec = importlib.util.spec_from_file_location(
                    "fluentpy.backends._old_input", backend.__file__
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                self.assertEqual(module.backend_name(), "python")
                self.assertEqual(module.split_code("1234", 4), tuple("1234"))
                with (
                    patch.dict(os.environ, {"FLUENTPY_BACKEND": "native"}),
                    self.assertRaises(RuntimeError),
                ):
                    module.split_code("1", 4)

    def test_python_mode_does_not_call_native(self):
        fake = unittest.mock.Mock()
        with (
            patch.object(backend, "_extension", fake),
            patch.dict(os.environ, {"FLUENTPY_BACKEND": "python"}),
        ):
            self.assertEqual(backend.split_code("1234", 4), tuple("1234"))
        self.assertEqual(fake.mock_calls, [])
