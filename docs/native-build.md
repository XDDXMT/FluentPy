# 可选 C 后端：编译与打包

FluentPy 的界面、信号和 Qt 对象仍由 Python 与 Qt 管理。`native/text_accel.c` 提供独立的文本扫描热路径，编译为 `fluentpy._native`，不需要 Qt 的 C++ 开发包。未安装本机扩展时，CodeEdit 的文本扫描自动回退 Python；普通组件的安装和使用不要求 C 编译器。

日期选择器的日历运算也位于同一 C 扩展。DatePicker 需要包含日期接口的新扩展，不提供新增 Python 日历算法；未编译时其他组件仍可导入，日期区提示构建。以下命令会一并编译文本与日期源文件，已有旧版 `.pyd` 也应重新构建。

## 当前支持范围

- C 源码使用 CPython API，面向 Python 3.10 及以上；当前已验证 Windows x64、CPython 3.13。
- 扩展使用普通 CPython ABI。生成的 `.pyd` 或 wheel 只适用于对应 Python 小版本、操作系统和架构，不能直接复制给其他 Python 版本使用。
- 标准编译方式由 setuptools 调用平台编译器：Windows 使用兼容当前 Python 的 MSVC，Linux/macOS 使用系统 C 编译器。
- 仓库还提供 Windows x64 的 Zig 编译入口，可在没有 Visual Studio 的电脑上使用。该入口暂不支持自由线程版 CPython。

## Windows：本地独立工具链

在仓库根目录执行：

```powershell
python -B scripts/fetch_zig.py
python -B scripts/build_native.py --zig .toolchains/zig-x86_64-windows-0.14.1/zig.exe
```

下载器只从 [Zig 官方站点](https://ziglang.org/download/) 获取固定的 0.14.1 Windows x64 版本，下载量约 82 MB，并核对仓库中固定的 SHA256。工具链、编译缓存和临时文件保存在本仓库的 `.toolchains/`、`build/` 中，不修改系统 PATH，也不要求管理员权限。

已下载工具链的情况下，只需运行第二条命令。生成文件位于 `src/fluentpy/_native<当前解释器扩展后缀>`，例如 Python 3.13 x64 下的 `_native.cp313-win_amd64.pyd`。修改 C 文件后重新编译，并重启已经导入过该扩展的 Python 程序。

已有系统编译器时可直接执行：

```powershell
python -m pip install "setuptools>=77"
python -B scripts/build_native.py
```

此入口直接调用本地 `setup.py`，因此当前环境需要 setuptools；源码安装时使用的隔离构建环境不代替这一步。

独立编译命令失败时会返回非零退出码，不会把失败当作“成功启用 C”。

## 构建 wheel

项目使用 setuptools 构建。一般开发环境可先安装标准构建前端：

```powershell
python -m pip install build
```

构建包含 C 扩展的 wheel，并明确要求编译成功：

```powershell
$env:FLUENTPY_BUILD_NATIVE = '1'
$env:FLUENTPY_ZIG = (Resolve-Path .toolchains/zig-x86_64-windows-0.14.1/zig.exe).Path
python -m build --wheel --outdir dist/native
```

使用系统编译器时不设置 `FLUENTPY_ZIG`。Windows x64、Python 3.13 的原生 wheel 标签为 `cp313-cp313-win_amd64`。收到对应 wheel 的用户安装时不需要编译器。

构建不包含任何本机代码的通用 Python wheel：

```powershell
$env:FLUENTPY_BUILD_NATIVE = '0'
python -m build --wheel --outdir dist/python-only
```

该 wheel 的标签为 `py3-none-any`，即使源码目录已经存在开发用 `.pyd`，也不会把它打包进去。

默认 `FLUENTPY_BUILD_NATIVE=auto`：尝试构建可选扩展；编译器不可用时 setuptools 会输出警告，保留 Python 实现。若要发布原生包，应使用 `1`，使任何编译失败直接终止构建；若要发布跨平台 Python 包，应使用 `0`，避免平台标签受可选扩展影响。

清理当前终端的构建选项：

```powershell
Remove-Item Env:FLUENTPY_BUILD_NATIVE -ErrorAction SilentlyContinue
Remove-Item Env:FLUENTPY_ZIG -ErrorAction SilentlyContinue
```

源码包包含 C 文件、构建脚本、测试与基准复现资料，不包含已编译二进制、下载工具链或构建缓存。Python 包元数据、MIT 许可证、第三方许可证和图标来源说明均随构建保留。

扩展机制与 wheel 的工作方式参见 [setuptools 扩展模块文档](https://setuptools.pypa.io/en/latest/userguide/ext_modules.html) 与 [CPython 扩展构建文档](https://docs.python.org/3/extending/building.html)。
