"""A failed quality check must not create a release output directory."""

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "prepare_release", ROOT / "scripts/prepare_release.py"
)
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


class ReleaseQualityTests(unittest.TestCase):
    def test_failed_quality_gate_leaves_no_partially_prepared_release(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src/fluentpy").mkdir(parents=True)
            (root / "scripts").mkdir()
            (root / "pyproject.toml").write_text(
                '[project]\nname = "fluentpy-qt"\nversion = "9.9.9"\n', encoding="utf-8"
            )
            (root / "src/fluentpy/__init__.py").write_text(
                '__version__ = "9.9.9"\n', encoding="utf-8"
            )
            (root / "scripts/check_quality.py").write_text(
                "raise SystemExit(17)\n", encoding="utf-8"
            )
            with (
                patch.object(release, "ROOT", root),
                patch.object(sys, "argv", ["prepare_release"]),
            ):
                with self.assertRaises(subprocess.CalledProcessError) as error:
                    release.main()
            self.assertEqual(error.exception.returncode, 17)
            self.assertFalse((root / "dist").exists())
