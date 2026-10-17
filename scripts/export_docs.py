"""Export the website into an independent, self-contained documentation checkout."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "sites/fluentpy-docs"
PUBLIC = {".html", ".css", ".js", ".svg", ".png", ".gif", ".txt"}
README = '''# FluentPy Docs

[官网](https://fluentpy.mcxmcl.cn/) · [组件库源码](https://github.com/XDDXMT/FluentPy) · [文档问题](https://github.com/XDDXMT/FluentPy-Docs/issues)

FluentPy 官方中文文档的独立开源仓库。包含网站 HTML、CSS、JavaScript、全部静态页面数据、106 个 Fluent 图标、真实 Qt 控件截图和 GIF，以及内容生成、媒体录制、校验和打包脚本。项目采用 [MIT 许可证](LICENSE)。

## 直接预览

```sh
git clone https://github.com/XDDXMT/FluentPy-Docs.git
cd FluentPy-Docs
python -m http.server 8767 --bind 0.0.0.0 --directory dist
```

打开 <http://127.0.0.1:8767/#/introduction>。Windows 可双击 `启动本地文档.bat`。现成的 `dist/` 可独立预览和部署，无需 Node.js、Qt 或 C 编译器；局域网访问使用本机实际 IP。

## 修改与生成

| 位置 | 内容 |
| --- | --- |
| `dist/index.html`、`dist/styles.css`、`dist/app.js` | 布局、主题、导航、搜索、示例与 API 视图 |
| `build_content.py` | 组件内容、分类与源码接口提取 |
| `dist/data.js` | 生成的页面数据，不直接编辑 |
| `dist/assets/` | 本地图片、GIF、SVG 与许可文件 |
| `dist/native-flow.*`、`dist/migration.*` | C 后端说明和 Qt 接口过渡动画 |
| `capture_*.py` | 使用 FluentPy 原生 Qt 控件生成媒体 |
| `validate_site.py`、`package_deploy.py` | 校验与完整静态包 |
| `SOURCE.json` | 本次同步对应的组件库提交和文件校验值 |

编辑 HTML、CSS 或 JS 后即可预览。修改文档内容、提取 API 或录制 Qt 画面时，需要单独检出组件库：

```sh
git clone https://github.com/XDDXMT/FluentPy.git ../FluentPy
python -m pip install -e ../FluentPy
python -m pip install -r requirements.txt
python build_content.py
python validate_site.py
```

脚本自动寻找相邻的 `FluentPy/`。如源码位于其他目录，先设置 `FLUENTPY_SOURCE_ROOT`：

```powershell
$env:FLUENTPY_SOURCE_ROOT = 'D:\\path\\to\\FluentPy'
python build_content.py
python validate_site.py
```

Linux/macOS 使用 `export FLUENTPY_SOURCE_ROOT=/path/to/FluentPy`。组件库中的 Python 回退可在没有 C 扩展时运行；后端计算以 C 为首选加速，Qt 继续负责界面。

更新首页实际界面用 `python capture_workbench_redesign.py`。其他控件由对应的 `capture_*.py` 维护；录制需要 Qt、Pillow 和适合的系统字体。临时报告写入组件库的 `build/`，工作台配图也会同步该组件库的 README 图片。重新录制后运行内容生成与校验。

## 部署

直接将 `dist/` 作为静态站点根目录，或生成包含全部资源和校验清单的压缩包：

```sh
python -m pip install -r requirements.txt
python package_deploy.py --output build/FluentPy-docs-complete.zip
```

包内包含 `dist/`、`部署说明.txt` 和 `SHA256SUMS.txt`。覆盖部署时保留目录结构，将网站根目录指向 `dist/`。正式主页为 <https://fluentpy.mcxmcl.cn/>。服务器无需 Python、Qt 或 Node.js。

## 同步与许可

本仓库由组件库内的 `scripts/export_docs.py` 导出；对应版本见 `SOURCE.json`。组件库内保留文档副本，贡献文档时请明确修改的来源并同步相关内容。

FluentPy 的网站源码及文档采用 MIT，保留原始版权声明与许可文本。Microsoft Fluent System Icons 的许可在 `dist/assets/icons-LICENSE.txt`；第三方声明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。Qt/PySide6 及可选 PyQt6 的许可单独适用，本仓库不分发它们的二进制。
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="A new or empty directory")
    parser.add_argument("--update", action="store_true", help="Refresh an unmodified previous export, preserving Git metadata")
    args = parser.parse_args()
    destination = args.output.resolve()
    if destination.exists() and any(destination.iterdir()):
        if not args.update or not (destination / "SOURCE.json").is_file():
            parser.error("Use an empty directory, or --update with an unmodified previous export.")
        previous = json.loads((destination / "SOURCE.json").read_text(encoding="utf-8"))
        if previous.get("component_repository") != "https://github.com/XDDXMT/FluentPy":
            parser.error("The destination is not a FluentPy documentation export.")
        for name, checksum in previous["sha256"].items():
            path = (destination / name).resolve()
            if not path.is_relative_to(destination) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != checksum:
                parser.error(f"Preserving modified destination file: {name}")
    if destination == ROOT or ROOT in destination.parents:
        parser.error("Choose a directory outside the component repository.")
    destination.mkdir(parents=True, exist_ok=True)
    exported = set()
    for path in SITE.iterdir():
        if path.is_file() and path.suffix in {".py", ".bat"}:
            shutil.copy2(path, destination / path.name)
            exported.add(path.name)
    for path in (SITE / "dist").rglob("*"):
        if not path.is_file() or path.suffix.lower() not in PUBLIC or path.name == "showcase-light.gif":
            continue
        relative = path.relative_to(SITE)
        if any(part.startswith(".") for part in relative.parts):
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        exported.add(relative.as_posix())
    shutil.copy2(ROOT / "LICENSE", destination / "LICENSE")
    (destination / "README.md").write_text(README, encoding="utf-8")
    (destination / "requirements.txt").write_text("Pillow>=10\n", encoding="utf-8")
    (destination / ".gitignore").write_text("__pycache__/\n*.py[cod]\n.venv/\nvenv/\n.openai/\nnode_modules/\nbuild/\n*.log\n*.zip\n.env\n.env.*\n", encoding="utf-8")
    (destination / ".gitattributes").write_text("* text=auto eol=lf\n*.png binary\n*.gif binary\n", encoding="utf-8")
    (destination / "THIRD_PARTY_NOTICES.md").write_text('''# Third-party notices

## Microsoft Fluent UI System Icons

- Source: https://github.com/microsoft/fluentui-system-icons
- Copyright (c) 2020 Microsoft Corporation. MIT licensed.
- Bundled resources: 106 SVG icons in `dist/assets/icons/`.
- Complete license: `dist/assets/icons-LICENSE.txt`.
- FluentPy's own brand mark is in `dist/assets/mark.svg`.

## Qt for Python

Screenshots and recordings are produced from FluentPy's Qt controls. Qt, PySide6 and the optional PyQt6 fallback are separately licensed dependencies used to run capture and validation scripts. Their binaries are not bundled here; FluentPy's MIT license does not replace their licenses.
''', encoding="utf-8")
    exported.update({"LICENSE", "README.md", "requirements.txt", ".gitignore", ".gitattributes", "THIRD_PARTY_NOTICES.md"})
    for name in exported:
        path = destination / name
        if path.suffix.lower() not in {".png", ".gif"}:
            path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
    inventory = {name: hashlib.sha256((destination / name).read_bytes()).hexdigest() for name in sorted(exported)}
    website_data = json.loads((SITE / "dist/data.js").read_text(encoding="utf-8").removeprefix("window.DOCS_DATA = ").rstrip(";\n"))
    metadata = {"component_repository":"https://github.com/XDDXMT/FluentPy", "component_version":website_data["version"],
        "component_commit":subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "component_worktree_dirty":bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
        "documentation_directory":"sites/fluentpy-docs", "sha256":inventory}
    (destination / "SOURCE.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Exported {len(inventory) + 1} files to {destination}")


if __name__ == "__main__":
    main()
