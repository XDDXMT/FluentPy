import os
import unittest
from unittest.mock import patch

from fluentpy.backends import shortcut

CTRL, ALT, SHIFT, META, NUM = 0x04000000, 0x08000000, 0x02000000, 0x10000000, 0x20000000


class ShortcutBackendTests(unittest.TestCase):
    def test_ascii_case_and_modifier_order(self):
        self.assertEqual(shortcut.normalize(ord('a'), CTRL | SHIFT), (ord('A'), CTRL | SHIFT))
        self.assertEqual(shortcut.modifier_labels(CTRL | ALT | SHIFT | META | NUM), ('Ctrl', 'Alt', 'Shift', 'Meta', 'Num'))
        self.assertEqual(shortcut.normalize(0, 0), (0, 0))
        self.assertEqual(shortcut.modifier_labels(0), ())

    def test_modifier_combinations_and_key_categories(self):
        flags = [CTRL, ALT, SHIFT, META, NUM]
        for bits in range(32):
            modifiers = sum(flag for i, flag in enumerate(flags) if bits & (1 << i))
            for key in (0x20, ord('+'), ord('Z'), 0x4e2d, 0x1f600, 0x01000004, 0x01000030, 0x01000048):
                with self.subTest(key=key, modifiers=modifiers):
                    self.assertEqual(shortcut.normalize(key, modifiers), (key, modifiers))

    def test_invalid_keys_and_modifier_bits_are_rejected(self):
        for key in (-1, 0, 1, 0xd800, 0xdfff, 0x110000, 0x01ffffff, 0x01000020, 0x01000021, 0x01000026):
            with self.subTest(key=key), self.assertRaises((ValueError, OverflowError)):
                shortcut.normalize(key, CTRL)
        for modifiers in (-1, 1, 0x40000000, 2**70):
            with self.subTest(modifiers=modifiers), self.assertRaises((ValueError, OverflowError)):
                shortcut.normalize(ord('A'), modifiers)
        for value in (True, False, 'A', None, 3.2):
            with self.subTest(value=value), self.assertRaises(TypeError):
                shortcut.normalize(value, CTRL)

    def test_conflicts_are_normalized_exact_and_empty_does_not_conflict(self):
        reserved = [(ord('a'), CTRL), (ord('A'), ALT), (0, 0)]
        self.assertTrue(shortcut.conflicts(ord('A'), CTRL, reserved))
        self.assertFalse(shortcut.conflicts(ord('A'), CTRL | SHIFT, reserved))
        self.assertFalse(shortcut.conflicts(0, 0, reserved))
        self.assertFalse(shortcut.conflicts(ord('B'), CTRL, reserved))

    def test_entire_reserved_list_is_validated_even_after_a_match(self):
        for reserved in ('Ctrl+A', [None], [(1,)], [(65,)], [(65, CTRL), (False, 0)], [(65, CTRL), (66, 1)]):
            with self.subTest(reserved=reserved), self.assertRaises((TypeError, ValueError)):
                shortcut.conflicts(65, CTRL, reserved)
        items = [(0x1000 + index, CTRL) for index in range(20000)]
        self.assertTrue(shortcut.conflicts(items[-1][0], CTRL, items))

    def test_auto_falls_back_and_python_can_be_forced(self):
        for mode in ('auto', 'python'):
            with patch.dict(os.environ, {'FLUENTPY_BACKEND': mode}):
                self.assertEqual(shortcut.normalize(65, CTRL), (65, CTRL))
        with patch.object(shortcut, '_extension', None):
            with patch.dict(os.environ, {'FLUENTPY_BACKEND': 'auto'}):
                self.assertEqual(shortcut.backend_name(), 'python')
                self.assertEqual(shortcut.normalize(65, CTRL), (65, CTRL))
            with patch.dict(os.environ, {'FLUENTPY_BACKEND': 'native'}):
                with self.assertRaisesRegex(RuntimeError, 'compiled.*shortcut backend.*Rebuild'):
                    shortcut.normalize(65, CTRL)
