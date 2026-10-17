# 可选 C 后端：编译与打包

FluentPy的界面、信号和Qt对象由Python与Qt管理，`fluentpy._native`提供可选C加速，不需要Qt的C++开发包。默认auto模式在扩展不可用时自动回退Python，CodeEdit、日期、时间、拖放和快捷键组件均可继续使用，无需为基本运行安装C编译器。

日期日历、时制换算与时间滚轮、文件拖放策略、快捷键校验和文本扫描都优先使用同一扩展中的对应接口。缺失、不兼容或旧版二进制缺少某组接口时，仅该组切换到兼容实现，不禁用组件；可用的其他C接口继续使用。构建成功后重启应用即可恢复C加速。

构建脚本编译`native/text_accel.c`、`native/date_accel.c`、`native/time_accel.c`、`native/calendar_accel.c`、`native/drop_accel.c`和`native/shortcut_accel.c`六份源文件。Python兼容策略位于`src/fluentpy/backends/`，与C实现保持返回值、输入校验和拒绝原因一致。Qt仍负责界面、原生文件信息、按键事件及QKeySequence转换。模式与诊断见[后端选择与回退](backends.md)。

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

这个纯Python包仍能使用日期、文件拖放、快捷键和代码编辑器的兼容后端；C扩展是可选加速。当前构建产物已在不加载C模块的独立进程中检查实际录制、筛选、日期操作和完整工作台。

默认 `FLUENTPY_BUILD_NATIVE=auto`：尝试构建可选扩展；编译器不可用时 setuptools 会输出警告，保留 Python 实现。若要发布原生包，应使用 `1`，使任何编译失败直接终止构建；若要发布跨平台 Python 包，应使用 `0`，避免平台标签受可选扩展影响。

清理当前终端的构建选项：

```powershell
Remove-Item Env:FLUENTPY_BUILD_NATIVE -ErrorAction SilentlyContinue
Remove-Item Env:FLUENTPY_ZIG -ErrorAction SilentlyContinue
```

源码包包含 C 文件、构建脚本、测试与基准复现资料，不包含已编译二进制、下载工具链或构建缓存。Python 包元数据、MIT 许可证、第三方许可证和图标来源说明均随构建保留。

扩展机制与 wheel 的工作方式参见 [setuptools 扩展模块文档](https://setuptools.pypa.io/en/latest/userguide/ext_modules.html) 与 [CPython 扩展构建文档](https://docs.python.org/3/extending/building.html)。
