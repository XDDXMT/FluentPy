# Windows 便携工作台

[下载 FluentPy 工作台 0.7.1 · Windows x64](https://github.com/XDDXMT/FluentPy/releases/download/v0.7.1/FluentPy-Workbench-0.7.1-windows-x64.zip)

解压整个压缩包，双击 `FluentPy-Workbench/FluentPy-Workbench.exe`。无需安装 Python、PySide6 或编译器，不需要管理员权限。请保留同目录的 `_internal` 文件夹。

便携版包含工作台、独立代码编辑与性能对照窗口、八组 C 后端、107 个图标及 Qt 运行环境。沿用实际启动遮罩，在创建页面前先显示；使用文件夹形式分发，避免每次启动都解包整个 Qt 运行环境。

工作台设置保存在当前 Windows 用户下。性能报告写入 `%LOCALAPPDATA%\FluentPy\Workbench\benchmarks`，不会要求写入程序目录。项目、图标和第三方运行环境的声明随压缩包提供。

## 从源码构建

在 Windows x64 / CPython 3.13 环境安装项目依赖、`pyinstaller==6.20.0` 和 Pillow，并先构建当前 C 扩展，然后运行：

```powershell
python -B scripts/build_workbench.py
```

输出位于 `dist/workbench/0.7.1/`，包含程序文件夹、便携压缩包、`SHA256SUMS.txt` 和构建清单。已有程序目录不会覆盖；重新构建时先保留或移动之前的输出。

对解压后的 EXE 执行安装自检：

```powershell
.\FluentPy-Workbench.exe --self-test C:\Temp\fluentpy-check\report.json
```

自检使用内置运行环境，核对 C 后端、图标、启动遮罩和全部页面的明暗主题；报告与截图写入指定报告目录。它不依赖源码路径，也不更改用户的工作台设置。
