from pathlib import Path


def test_project_files_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    assert (root / "LICENSE").exists()
    assert (root / "pyproject.toml").exists()
    assert (root / "src" / "fluentpy" / "__init__.py").exists()
