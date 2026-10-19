# 构建与发布

项目安装名为 **fluentpy-qt**，Python 导入名为 **fluentpy**。当前版本见 `pyproject.toml` 与 `src/fluentpy/__init__.py`，两处必须保持一致。公开发布记录见 [PyPI](https://pypi.org/project/fluentpy-qt/) 和 [GitHub Releases](https://github.com/XDDXMT/FluentPy/releases)。

## 构建发布文件

发布工具需要 Python 3.12+；组件库本身支持 Python 3.10+。在仓库根目录准备独立的构建环境：

```powershell
python -m venv build/pypi-tools
.\build\pypi-tools\Scripts\python.exe -m pip install build twine wheel "setuptools>=77"
```

构建通用 wheel 和源码包：

```powershell
.\build\pypi-tools\Scripts\python.exe -X utf8 -B scripts/prepare_release.py
```

在 Windows x64 / 普通 CPython 3.13 下，同时构建含 C 扩展的 wheel：

```powershell
python scripts/fetch_zig.py
.\build\pypi-tools\Scripts\python.exe -X utf8 -B scripts/prepare_release.py --native --zig .toolchains/zig-x86_64-windows-0.14.1/zig.exe
```

文件写入 `dist/pypi/<版本>/`。两个 wheel 从同一个 sdist 的独立目录构建，避免本机 `.pyd` 混入通用包。脚本会检查包元数据并生成 SHA-256 清单，不会上传，也不会覆盖已有的发布目录。原生扩展的其他构建方式见[编译与打包](native-build.md)。

## 发布与安装验证

仅维护者需要上传权限。使用官方 [Twine](https://twine.readthedocs.io/en/stable/) 上传复核过的当前版本 `.whl` 和 `.tar.gz`；`release.json` 只用于本地校验，不上传。不要对根目录 `dist/*` 使用通配上传，其中可能包含其他版本和工作台、网站部署包。

PyPI 账号需完成邮箱验证和双重验证。API token 通过上传工具的隐藏输入提示填写；不写入源码、仓库或命令行参数。公开仓库不包含个人发布助手或凭据。

发布后核对 PyPI 文件列表、版本及 SHA-256，并在独立环境安装验证：

```powershell
python -m venv build/install-check
.\build\install-check\Scripts\python.exe -m pip install --index-url https://pypi.org/simple fluentpy-qt
.\build\install-check\Scripts\python.exe -c "import fluentpy; print(fluentpy.__version__)"
```

检查输出版本，并验证实际界面和后端选择。已有版本的文件不能覆盖；修复需要递增版本后重新构建。

官方参考：[Python 打包教程](https://packaging.python.org/en/latest/tutorials/packaging-projects/)、[PyPI API token](https://pypi.org/help/#apitoken)。
