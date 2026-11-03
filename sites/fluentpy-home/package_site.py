"""Stage the presentation homepage and docs as one static, manual deployment."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import zipfile
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

SITE = Path(__file__).resolve().parent
ROOT = SITE.parents[1]
PUBLIC = {".html", ".css", ".js", ".svg", ".png", ".gif", ".txt", ".json"}


class LocalLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = set()

    def handle_starttag(self, tag, attributes):
        for name, value in attributes:
            if name not in {"href", "src"} or not value:
                continue
            url = urlsplit(value)
            if not url.scheme and not url.netloc and url.path:
                self.links.add(unquote(url.path))


def stage(directory: Path) -> dict:
    directory = directory.resolve()
    if directory == ROOT or directory in ROOT.parents or directory == SITE:
        raise ValueError("choose a dedicated staging directory")
    marker = directory / "SITE-MANIFEST.json"
    if directory.exists() and any(directory.iterdir()) and not marker.is_file():
        raise ValueError("preserving a non-empty directory that is not a FluentPy site stage")
    directory.mkdir(parents=True, exist_ok=True)
    inventory = {}
    for source, prefix in (
        (SITE / "dist", Path()),
        (ROOT / "sites/fluentpy-docs/dist", Path("docs")),
    ):
        for path in sorted(source.rglob("*")):
            if not path.is_file() or path.is_symlink() or path.suffix not in PUBLIC:
                continue
            relative = path.relative_to(source)
            if any(part.startswith(".") for part in relative.parts):
                continue
            destination = directory / prefix / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
            inventory[(prefix / relative).as_posix()] = hashlib.sha256(
                destination.read_bytes()
            ).hexdigest()
    # One content fingerprint invalidates stale CSS, scripts and screenshots
    # after a manual deployment. The editable source keeps working on its own.
    homepage_files = {
        key: digest for key, digest in inventory.items() if not key.startswith("docs/")
    }
    asset_version = hashlib.sha256(
        json.dumps(homepage_files, sort_keys=True).encode("utf-8")
    ).hexdigest()[:12]
    index = directory / "index.html"
    html = index.read_text(encoding="utf-8").replace("?v=source", f"?v={asset_version}")
    index.write_text(html, encoding="utf-8", newline="\n")
    inventory["index.html"] = hashlib.sha256(index.read_bytes()).hexdigest()
    for relative in inventory:
        if not relative.endswith(".html"):
            continue
        page = directory / relative
        parser = LocalLinks()
        parser.feed(page.read_text(encoding="utf-8"))
        for link in parser.links:
            target = (page.parent / link).resolve()
            if not target.is_relative_to(directory):
                raise ValueError(f"local URL escapes the website: {relative}: {link}")
            if target.is_dir():
                target = target / "index.html"
            if not target.is_file():
                raise ValueError(f"missing local resource: {relative}: {link}")
    manifest = {
        "project": "FluentPy presentation and documentation",
        "created_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "source_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
        "homepage": "index.html",
        "documentation": "docs/index.html",
        "sha256": inventory,
    }
    marker.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=ROOT / "build/site-preview")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output and args.output.exists():
        parser.error(f"preserving existing deployment archive: {args.output}")
    manifest = stage(args.directory)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        instructions = (
            "FluentPy 完整网站部署包\n\n"
            "将压缩包内的 index.html、home.css、home.js、assets/ 和 docs/ 解压到网站根目录。\n"
            "根路径为展示主页；/docs/ 为文档。旧的根路径 #/ 文档链接会自动跳转。\n"
            "服务器不需要 Python、Qt 或 Node.js。不要只上传单个 index.html。\n"
            "新接口目前对应开发源码；网站上线和 PyPI 发布是独立操作。\n"
        )
        with zipfile.ZipFile(args.output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for relative in manifest["sha256"]:
                archive.write(args.directory / relative, relative)
            archive.write(args.directory / "SITE-MANIFEST.json", "SITE-MANIFEST.json")
            archive.writestr("部署说明.txt", instructions)
            archive.writestr(
                "SHA256SUMS.txt",
                "".join(
                    f"{digest}  {relative}\n" for relative, digest in manifest["sha256"].items()
                ),
            )
        print(f"Manual deployment archive: {args.output.resolve()}")
    print(f"Validated {len(manifest['sha256'])} static files in {args.directory.resolve()}")


if __name__ == "__main__":
    main()
