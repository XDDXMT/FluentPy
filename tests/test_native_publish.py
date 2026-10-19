"""A running example must retain its binary, including on a failed replacement."""

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "native_build_helper", ROOT / "scripts/build_native.py"
)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class NativePublishTests(unittest.TestCase):
    def test_locked_old_binary_is_retained_and_replacement_failure_restores_it(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(helper, "ROOT", Path(folder)):
            root = Path(folder)
            output = root / "module.pyd"
            compiled = root / "compiled.pyd"
            compiled.write_bytes(b"new binary")
            copy = helper.shutil.copy2
            for fail in (False, True):
                output.write_bytes(b"old running binary")
                calls = []

                def copying(source, target):
                    calls.append(True)
                    if len(calls) == 1:
                        raise PermissionError("in use")
                    if fail:
                        Path(target).write_bytes(b"partial")
                        raise OSError("disk full")
                    return copy(source, target)

                with patch.object(helper.shutil, "copy2", copying):
                    if fail:
                        with self.assertRaises(OSError):
                            helper._publish_extension(compiled, output, root)
                        self.assertEqual(output.read_bytes(), b"old running binary")
                    else:
                        helper._publish_extension(compiled, output, root)
                        self.assertEqual(output.read_bytes(), b"new binary")
                        self.assertEqual(
                            next((root / "in-use").iterdir()).read_bytes(), b"old running binary"
                        )
