# 卡片组件

五类卡片可从 `fluentpy` 直接导入，默认圆角为 8 个逻辑像素，明暗配色跟随 `theme`。

| 类型 | 用途 | 内容布局 |
| --- | --- | --- |
| `CardWidget` | 应用条目与内容容器 | 自行添加 Qt 布局 |
| `SimpleCardWidget` | 悬浮、按下时保持稳定背景 | 自行添加 Qt 布局 |
| `ElevatedCardWidget` | 带轻阴影渐变的悬浮卡片 | 自行添加 Qt 布局 |
| `HeaderCardWidget` | 标题条与内容区 | `body_layout` / `viewLayout` |
| `GroupHeaderCardWidget` | 图标、文字与控件组成的设置分组 | `add_group()` / `addGroup()` |

卡片本体只作为容器，不响应点击、按压或 Space / Enter 激活，不显示手形光标或点击焦点边框。交互由内部按钮、输入框等控件完成；悬浮卡片仅保留轻阴影过渡。`set_border_radius()` / `setBorderRadius()` 可调整圆角。

```python
from fluentpy import Button, GroupHeaderCardWidget, HeaderCardWidget
from fluentpy.qt import QtWidgets

requirements = HeaderCardWidget("系统要求")
requirements.body_layout.addWidget(QtWidgets.QLabel("运行环境就绪", requirements.view))

settings = GroupHeaderCardWidget("基本设置")
choose = Button("选择")
row = settings.add_group("📁", "构建目录", "选择输出位置", choose)
choose.clicked.connect(lambda: print("选择目录"))
```

分组在窄窗口内会把操作控件放到文字下方。`groups()` 返回当前行的元组，`set_group_text()` 更新文字，`set_group_control()` 替换操作控件，`remove_group()` 移除一行。旧控件与被移除的行按 Qt 生命周期释放；不应在删除后继续使用它们。

标题使用 `set_title()` / `setTitle()` 更新；`set_header_visible(False)` 隐藏标题及分隔线，保留内容。`header_layout` 可用于添加标题条右侧操作。

运行 `python examples/cards.py` 或 Windows 双击 `examples/run_cards.bat` 查看五类卡片的交互、亮暗主题及圆角设置。本地网页 `#/cards` 提供截图、悬浮 GIF 和源码生成的接口参考。

应用列表示例采用适合实际桌面的紧凑密度：行高 72、标题 14px、说明 12px、图标 40，打开按钮使用库默认的 80×32。表情卡片为 128×128，Unicode 表情使用 40px。所有数值都是 Qt 逻辑像素，由 Qt 跟随系统 DPI 缩放；参考图仅用于风格和布局，不把截图物理像素当作控件尺寸。

标题、说明和按钮保持常规字重，英文优先 Segoe UI、中文回退 Microsoft YaHei UI。第一条展示与网站共用的项目主图标及 `PluentPy` / `MIT License`，第二条展示 `FluentIcon.BUILDING_BANK` 及“文本” / “我是文本”。卡片本体不限定应用行尺寸，可自行组合内容布局。

外观与行为需求参考用户截图及 [QFluentWidgets 的公开卡片说明](https://qfluentwidgets.com/pages/components/cardwidget/)。组件与布局在本仓库独立编写，不依赖 `qfluentwidgets` 包。示例表情使用 Unicode 与系统 Emoji 字体；应用行使用项目主图标与微软官方 `FluentIcon.BUILDING_BANK`。图标库中仍保留此前新增的 [Music Note 2 SVG](https://github.com/microsoft/fluentui-system-icons/blob/main/assets/Music%20Note%202/SVG/ic_fluent_music_note_2_24_regular.svg)，以及微软图标的完整 MIT 许可。既有 `Card` / `ExamplePanel` 保持原有用途。
