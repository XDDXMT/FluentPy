# FluentPy for Qt

**Fluent 风格的 Qt for Python 桌面组件库，由性邓的小馒头独立开发，采用 MIT 许可证。**

[中文文档](https://fluentpy.mcxmcl.cn/) · [源码与示例](https://github.com/XDDXMT/FluentPy) · [问题反馈](https://github.com/XDDXMT/FluentPy/issues)

## 安装

需要 Python 3.10+。建议在新建的虚拟环境内安装：

```console
python -m venv .venv
# Windows
.venv\Scripts\python -m pip install fluentpy-qt
# macOS / Linux
.venv/bin/python -m pip install fluentpy-qt
```

PyPI 安装名是 **`fluentpy-qt`**，代码导入名仍为 **`fluentpy`**。
PyPI 上的 `fluentpy` 是其他作者的独立项目，请勿用 `pip install fluentpy` 安装本组件库。
两个项目的导入名称冲突，应放在不同的虚拟环境中使用。

PySide6 会作为依赖安装。Qt、PySide6 等依赖遵循各自的许可证。

## 第一个窗口

```python
import sys
from fluentpy import AccentButton, FluentWindow
from fluentpy.qt import QtWidgets

app = QtWidgets.QApplication(sys.argv)
window = FluentWindow("你好，FluentPy")
window.resize(800, 560)
window.set_title_bar_enabled(True)
button = AccentButton("你好，世界")
window.content_layout.addWidget(button)
window.show()
sys.exit(app.exec())
```

## 组件

- 按钮、输入、前后缀输入、分格密码、复选框和各类下拉选择。
- 表格、滑块、日期时间滚轮、日历、颜色编辑器和取色。
- 卡片、可展开容器、导航、流畅窗口、启动页面及主题渐变。
- 高级右键菜单、消息条、吐司、进度提示和对话框。
- 拖放、快捷键录制、代码编辑器和音符时间轴。

工作台和独立示例在源码仓库的 `examples/` 中，可从源码运行 `python examples/showcase.py`。
wheel 安装的是组件库，不包含示例工作台。

## 可选 C 加速

Qt 负责界面和动画；C 扩展加速文本、日期、时间、日历、拖放、快捷键、颜色和输入策略。
默认优先使用 C，扩展缺失或不兼容时自动回退 Python，基本运行无需 C 编译器。

当前提供 Windows x64 / CPython 3.13 的原生 wheel，以及不含本机二进制的通用 Python wheel。
其他 Python 版本和平台使用通用 wheel，运行兼容后端；也可从源码编译对应扩展。
`FLUENTPY_BACKEND=python` 可强制回退，`native` 要求对应 C 接口可用。

当前实际验证环境为 Windows x64、CPython 3.13、PySide6 / Qt 6.11.1。
其他平台的桌面表现需另行验证。Windows 11 云母效果在系统不支持时回退普通背景。

项目处于早期开发阶段。组件接口、用法及 C 构建说明见[官方文档](https://fluentpy.mcxmcl.cn/)。

## 来源与许可

FluentPy 独立实现组件，仅参考公开的 Fluent 设计与交互思路，不包含参考组件库的源码、样式或示例素材。
Microsoft Fluent UI System Icons 的 MIT 许可与来源声明随包提供。
详情见[第三方声明](https://github.com/XDDXMT/FluentPy/blob/main/THIRD_PARTY_NOTICES.md)。
