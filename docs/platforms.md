# Linux、macOS 与 Windows

0.8.1 增加跨平台窗口策略、系统字体、数据目录和原生打包。控件继续使用 Qt，C 扩展不依赖 Win32；没有匹配的扩展时自动使用 Python 回退。

## 安装和运行

在目标系统创建虚拟环境，避免混用系统 Python 与其他 Qt 应用的依赖：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install fluentpy-qt
```

开发版从仓库根目录执行 `.venv/bin/python -m pip install -e .`，运行 `.venv/bin/python examples/showcase.py`。Windows 对应解释器为 `.venv\Scripts\python.exe`。组件库的 Python 版本要求不代表所有 PySide6 版本支持同样的系统；最低系统版本、glibc 与 CPU 架构需同时满足所选 Qt/PySide6 的要求。

Debian / Ubuntu 的桌面环境通常已安装部分依赖。若提示 xcb、OpenGL 或 PulseAudio 动态库缺失，可按发行版安装：

```sh
sudo apt-get install libegl1 libopengl0 libxkbcommon-x11-0 libxcb-cursor0 \
  libxcb-icccm4 libxcb-keysyms1 libxcb-shape0 libxcb-xinerama0 \
  libxcb-render-util0 libpulse0 fonts-noto-cjk
```

音频还需要发行版对应的 ALSA 库：Ubuntu 22.04 使用 `libasound2`，较新发行版可能使用 `libasound2t64`。媒体格式、音频设备和视频输出由 Qt 后端及系统解码能力决定。FluentPy 不会自动安装系统库或修改桌面配置。

## 窗口、字体与快捷键

- Windows 保留 Fluent 集成标题栏与系统调整大小边框。Windows 11 云母效果按系统能力启用。
- macOS 默认保留系统窗口边框和系统窗口按钮；Fluent 标题区域仍可放搜索框、页面标签和导航。普通 Qt 子控件使用系统字体，代码编辑器优先 SF Mono / Menlo。
- Wayland 默认保留系统窗口边框，由合成器负责移动和调整大小。X11 可以使用 Fluent 自定义标题栏。不要用强制全局坐标移动代替 `QWindow.startSystemMove()`。
- Linux 使用系统 UI 字体及 Noto CJK 回退；未安装中文字体时应由用户安装字体。FluentPy 不捆绑商业系统字体。
- 复制、粘贴、剪切等使用 Qt 标准快捷键，跟随系统的 Ctrl / Command 映射；用户自行设置的快捷键仍以指定序列为准。

应用可显式指定边框策略：

```python
window.set_title_bar_enabled(True)  # 按平台自动选择
window.set_title_bar_enabled(True, native_frame=True)  # 系统边框 + Fluent 工具区
window.set_title_bar_enabled(True, native_frame=False)  # 自定义 Fluent 标题栏
```

切换策略保留页面、输入内容和标题栏自定义布局。macOS 原生全屏和窗口装饰由系统管理；跨平台模式不仿造云母或修改系统权限。Wayland 的全局定位、任务栏、窗口阴影和激活策略仍由具体合成器决定。

屏幕取色需要系统允许读取屏幕：macOS 可能要求屏幕录制授权；Wayland 可能不支持 `QScreen.grabWindow()`。取色不可用时发出 `failed` 信号，不阻止使用应用内颜色面板。文件选择使用 Qt 文件对话框，头像与裁剪仅修改内存图像，不覆盖源文件。

## 数据目录

工作台日志和性能报告通过 Qt `QStandardPaths.GenericDataLocation` 定位，附加 `FluentPy/Workbench`：

| 系统 | 常规位置 |
| --- | --- |
| Windows | `%LOCALAPPDATA%\FluentPy\Workbench` |
| Linux | `$XDG_DATA_HOME/FluentPy/Workbench`，默认 `~/.local/share/FluentPy/Workbench` |
| macOS | `~/Library/Application Support/FluentPy/Workbench` |

工作台偏好仍使用 `QSettings`，按系统保存。应用沙盒可能改变实际路径，应以 Qt 返回值为准。

## C 扩展与工作台打包

Linux 使用 GCC / Clang 和当前 Python 的开发头文件；macOS 使用 Xcode Command Line Tools。不要把 Windows `.pyd` 拷贝到其他平台。

```sh
python scripts/build_native.py
FLUENTPY_BACKEND=native python examples/showcase.py
```

通用 Python wheel 基础运行无需编译器；`FLUENTPY_BACKEND=python` 可强制回退，`native` 用于检查 C 扩展，`auto` 为默认。

工作台必须在目标系统及架构构建：

```sh
python -m pip install pyinstaller Pillow
python scripts/build_workbench.py --output dist/workbench/local
```

默认允许 Python 回退；加 `--require-native` 要求九组 C 后端齐全。Windows 输出 ZIP，Linux 输出保留可执行权限的 tar.gz，macOS 输出包含 `.app` 和框架符号链接的 tar.gz。脚本不交叉编译，不覆盖已有输出目录。Linux 包仍依赖桌面系统库，宜在目标范围内较旧的发行版构建。macOS 的公开分发应由维护者使用自己的证书签名并公证，脚本不申请证书或修改 Gatekeeper。

## 自动验证

`.github/workflows/platforms.yml` 覆盖 Windows、Linux、Intel Mac 和 Apple Silicon Mac。每种系统编译 C 扩展，分别运行 C / Python 测试，并从同一个源码包在独立目录构建、安装和检查两种 wheel。Linux 另用 Xvfb / xcb，Mac 使用 Cocoa，检查实际 Qt 工作台页面与启动流程。手动运行工作流可生成各平台便携构建产物。

CI 结果与构建产物见 [Desktop platforms](https://github.com/XDDXMT/FluentPy/actions/workflows/platforms.yml)。自动测试不代表每个 Linux 桌面、显卡、媒体解码器或 macOS 权限组合都已经人工验收。

参考：[Qt for Linux](https://doc.qt.io/qt-6/linux.html)、[Qt for macOS](https://doc.qt.io/qt-6/macos.html)、[QStandardPaths](https://doc.qt.io/qt-6/qstandardpaths.html)、[QWindow 系统移动与缩放](https://doc.qt.io/qt-6/qwindow.html#startSystemMove)。
