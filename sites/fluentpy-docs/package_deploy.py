"""Create and verify a complete static deployment, including every local asset."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath

from PIL import Image

SITE = Path(__file__).resolve().parent
from source_project import repository_root

ROOT = repository_root()
STATIC = SITE / "dist"
PUBLIC_EXTENSIONS = {".html", ".css", ".js", ".svg", ".png", ".gif", ".txt"}
CHINA_TIME = timezone(timedelta(hours=8))


class LocalLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = set()

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if (
                key in {"src", "href"}
                and value
                and not value.startswith(("#", "http:", "https:", "data:"))
            ):
                self.paths.add(value.split("?", 1)[0])


def required_assets(data, index):
    parser = LocalLinks()
    parser.feed(index)
    required = parser.paths | {"assets/icons-LICENSE.txt", "assets/FluentPy-LICENSE.txt"}
    for icon in data["icons"]:
        required.add(icon["file"])
    for media in data["animatedPreviews"].values():
        required.update("assets/previews/" + media[key] for key in ("image", "poster"))
    for page in data["pages"]:
        if page.get("cover"):
            required.add(f"assets/previews/{page['cover']['image']}-light.png")
        for section in page["sections"]:
            if section.get("migration"):
                required.update(
                    "assets/previews/" + section["migration"][key]
                    for key in ("beforeImage", "afterImage", "focusImage")
                )
            preview = section.get("preview")
            if (
                preview
                and preview not in {"icons", "api-index"}
                and preview not in data["animatedPreviews"]
            ):
                required.add(f"assets/previews/{preview}-light.png")
            for card in section.get("gallery", []):
                required.add(f"assets/previews/{card['image']}-light.png")
            for link in section.get("links", []):
                href = link.get("href", "")
                if href.startswith("assets/"):
                    required.add(href.split("?", 1)[0])
    return required


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT
        / "dist"
        / "docs"
        / f"FluentPy-docs-complete-{datetime.now(CHINA_TIME):%Y%m%d}.zip",
    )
    args = parser.parse_args()
    payload = {}
    for file in sorted(STATIC.rglob("*")):
        relative = file.relative_to(STATIC)
        if not file.is_file() or any(part.startswith(".") for part in relative.parts):
            continue
        if file.suffix.lower() not in PUBLIC_EXTENSIONS or file.name == "showcase-light.gif":
            continue
        payload[relative.as_posix()] = file.read_bytes()

    data = json.loads(
        payload["data.js"]
        .decode("utf-8")
        .removeprefix("window.DOCS_DATA = ")
        .strip()
        .removesuffix(";")
    )
    # A new cache key also refreshes any previously cached missing-image response.
    digest = hashlib.sha256(
        b"".join(name.encode() + b"\0" + value for name, value in sorted(payload.items()))
    ).hexdigest()[:16]
    data["previewVersion"] = "deploy-" + digest
    payload["data.js"] = (
        "window.DOCS_DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n"
    ).encode("utf-8")
    cache_version = hashlib.sha256(
        b"".join(
            payload[name]
            for name in (
                "data.js",
                "app.js",
                "styles.css",
                "native-flow.js",
                "native-flow.css",
                "migration.js",
                "migration.css",
            )
        )
    ).hexdigest()[:16]
    index = payload["index.html"].decode("utf-8")
    index = re.sub(
        r'((?:styles\.css|native-flow\.css|migration\.css|data\.js|native-flow\.js|migration\.js|app\.js)\?v=)[^"\s]+',
        lambda match: match[1] + cache_version,
        index,
    )
    payload["index.html"] = index.encode("utf-8")

    required = required_assets(data, index)
    assert required <= payload.keys(), f"Missing assets: {sorted(required - payload.keys())}"
    assert "assets/previews/buttons-light.png" in required
    for name, content in payload.items():
        assert not PurePosixPath(name).is_absolute() and ".." not in PurePosixPath(name).parts
        if name.endswith((".png", ".gif")):
            with Image.open(io.BytesIO(content)) as picture:
                picture.verify()
        elif name.endswith(".svg"):
            ET.fromstring(content)
        elif name.endswith(".css"):
            css = content.decode("utf-8")
            for url in re.findall(r"url\(\s*['\"]?([^)'\"]+)", css):
                if not url.startswith(("data:", "http:", "https:", "#")):
                    path = (PurePosixPath(name).parent / url.split("?", 1)[0]).as_posix()
                    assert path in payload, (name, path)

    counts = Counter(PurePosixPath(name).suffix for name in payload)
    marker = {
        "project": "FluentPy docs",
        "public_url": "https://fluentpy.mcxmcl.cn/",
        "packaged_at": datetime.now(CHINA_TIME).isoformat(),
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "source_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
        "preview_version": data["previewVersion"],
        "checked_local_references": len(required),
        "pages": len(data["pages"]),
        "icons": len(data["icons"]),
        "asset_counts": dict(counts),
    }
    payload["deployment.json"] = (json.dumps(marker, ensure_ascii=False, indent=2) + "\n").encode(
        "utf-8"
    )
    instructions = """FluentPy 完整静态文档部署包

1. 在宝塔中，将本压缩包上传并解压覆盖到：
   /www/wwwroot/fluentpy.mcxmcl.cn/
2. 解压后应有：
   /www/wwwroot/fluentpy.mcxmcl.cn/dist/index.html
   /www/wwwroot/fluentpy.mcxmcl.cn/dist/assets/previews/buttons-light.png
3. 宝塔站点的网站根目录设置为：
   /www/wwwroot/fluentpy.mcxmcl.cn/dist
4. 打开 https://fluentpy.mcxmcl.cn/#/introduction。
   覆盖后使用 Ctrl+F5 刷新；使用CDN时刷新首页及data.js的缓存。

本包包含完整图片、SVG图标、GIF动画、JS、CSS与许可证。
网页为纯静态文件，无需在服务器安装Python、Qt或Node.js。
包内文件使用dist/相对路径，解压时保持此目录结构。
deployment.json记录部署版本，SHA256SUMS.txt记录全部静态文件校验值。
"""
    checksums = "".join(
        f"{hashlib.sha256(value).hexdigest()}  dist/{name}\n"
        for name, value in sorted(payload.items())
    )
    archive = args.output.resolve()
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for name, value in sorted(payload.items()):
            entry = zipfile.ZipInfo("dist/" + name)
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(entry, value)
        bundle.writestr("部署说明.txt", instructions.encode("utf-8-sig"))
        bundle.writestr("SHA256SUMS.txt", checksums)
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        for name, value in payload.items():
            assert bundle.read("dist/" + name) == value
    report = {
        **marker,
        "archive": str(archive),
        "bytes": archive.stat().st_size,
        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "static_files": len(payload),
    }
    report_file = ROOT / "build" / "deployment" / "complete-package-report.json"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
