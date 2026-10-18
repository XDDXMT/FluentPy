import os
import importlib.util
from pathlib import Path
import sys
import random
import types
import unittest
from unittest.mock import patch

from fluentpy.backends import color, _color_python as reference


class ColorBackendTests(unittest.TestCase):
    def test_hex_alpha_order_short_form_and_roundtrip(self):
        for text, value in (("#abc", (170,187,204,255)), ("80e4579b", (228,87,155,128)), ("#00000000", (0,0,0,0))):
            self.assertEqual(color.parse_hex(text), value)
            self.assertEqual(color.parse_hex(color.format_hex(*value, include_alpha=True)), value)

    def test_reference_and_native_conversion_parity(self):
        rng = random.Random(921)
        native = color._extension
        for _ in range(1200):
            rgba = tuple(rng.randrange(256) for _ in range(4))
            hsv = reference.rgb_to_hsv(*rgba[:3])
            actual = color.rgb_to_hsv(*rgba[:3])
            for left, right in zip(hsv, actual):
                self.assertAlmostEqual(left, right, places=10)
            if hsv[0] >= 0:
                self.assertEqual(color.hsv_to_rgba(*hsv, rgba[3]), rgba)
            self.assertEqual(color.format_hex(*rgba, include_alpha=True), reference.format_hex(*rgba, include_alpha=True))
            if native is not None and hasattr(native, 'color_hsv_to_rgba'):
                values = (rng.random()*360, rng.random(), rng.random(), rng.randrange(256))
                self.assertEqual(native.color_hsv_to_rgba(*values), reference.hsv_to_rgba(*values))
                self.assertEqual(native.color_parse_hex(reference.format_hex(*rgba, include_alpha=True)), rgba)

    def test_invalid_values_have_same_error_in_both_backends(self):
        native = color._extension
        cases = [('parse_hex',(value,)) for value in ('', '#12', '#abcd', '#gggggg', '#１２３', '\ud800', ' #123', None, 123)]
        cases += [('rgb_to_hsv',(value,0,0)) for value in (True, -1, 256, 10**200, 1.0, '1')]
        cases += [('hsv_to_rgba',(value,1,1)) for value in (True, -1, 361, float('nan'), float('inf'), 10**500, '0')]
        cases += [('hsv_to_rgba',(0,value,1)) for value in (-.1, 1.1, None, True)]
        for method, args in cases:
            with self.subTest(method=method,args=repr(args)):
                with self.assertRaises((ValueError,TypeError)) as error:
                    getattr(reference,method)(*args)
                if native is not None and hasattr(native,'color_'+method):
                    with self.assertRaises(type(error.exception)):
                        getattr(native,'color_'+method)(*args)

    def test_missing_and_older_extensions_fall_back_per_feature(self):
        path = Path(color.__file__)
        for extension in (None, types.SimpleNamespace(color_parse_hex=lambda value: None)):
            with patch('importlib.import_module',return_value=extension), patch.dict(os.environ, {'FLUENTPY_BACKEND':'auto'}):
                spec=importlib.util.spec_from_file_location('fluentpy.backends._older_color_test',path)
                module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
                self.assertEqual(module.backend_name(), 'python')
                self.assertEqual(module.parse_hex('#09f'), (0,153,255,255))
                with patch.dict(os.environ, {'FLUENTPY_BACKEND':'native'}), self.assertRaises(RuntimeError):
                    module.parse_hex('#09f')

    def test_forced_python_does_not_touch_extension(self):
        fake = unittest.mock.Mock()
        with patch.object(color,'_extension',fake), patch.dict(os.environ,{'FLUENTPY_BACKEND':'python'}):
            self.assertEqual(color.backend_name(),'python')
            self.assertEqual(color.hsv_to_rgba(360,1,1),(255,0,0,255))
            self.assertEqual(color.parse_hex('#fff'),(255,255,255,255))
        self.assertEqual(fake.mock_calls,[])
