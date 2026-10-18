# 卡片组件

卡片与折叠容器可从 `fluentpy` 直接导入，默认圆角为 8 个逻辑像素，明暗配色跟随 `theme`。

| 类型 | 用途 | 内容布局 |
| --- | --- | --- |
| `CardWidget` | 应用条目与内容容器 | 自行添加 Qt 布局 |
| `SimpleCardWidget` | 悬浮、按下时保持稳定背景 | 自行添加 Qt 布局 |
| `ElevatedCardWidget` | 带轻阴影渐变的悬浮卡片 | 自行添加 Qt 布局 |
| `HeaderCardWidget` | 标题条与内容区 | `body_layout` / `viewLayout` |
| `GroupHeaderCardWidget` | 图标、文字与控件组成的设置分组 | `add_group()` / `addGroup()` |
| `ExpandableCardWidget` | 标题条控制的动画折叠卡片 | `body_layout` / `viewLayout` |
| `AccordionWidget` | 多张折叠卡片的纵向容器 | `add_card()` / `addCard()` |

普通卡片和所有卡片的内容区只作为容器，操作由内部按钮、输入框等控件完成；悬浮卡片仅保留轻阴影过渡。折叠卡片的标题条是切换入口，可点击或聚焦后按 Space / Enter 展开与收起。`set_border_radius()` / `setBorderRadius()` 可调整卡片圆角。

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

## 折叠设置卡片

`ExpandableCardWidget` 的构造参数为 `title=""`、`parent=None` 和关键字参数 `expanded=False`。通过 `view` / `body_layout` 放置现有 Qt 控件，无需自己管理收起后的高度。标题条切换时，内容高度与箭头平滑过渡，周围卡片随 Qt 布局移动；内部控件及表单值保留。

```python
from fluentpy import AccentButton, AccordionWidget, Button, ComboBox, ExpandableCardWidget, Slider
from fluentpy.qt import QtWidgets

panels = AccordionWidget()
blend = panels.add_card(ExpandableCardWidget("混合", expanded=True))
blend.body_layout.addWidget(QtWidgets.QLabel("混合模式", blend.view))
mode = ComboBox(blend.view)
mode.addItems(["正常", "正片叠底", "滤色"])
mode.setFixedWidth(150)
blend.body_layout.addWidget(mode)
blend.body_layout.addWidget(QtWidgets.QLabel("不透明度", blend.view))
opacity = Slider(parent=blend.view)
opacity.setRange(0, 100)
opacity.setValue(40)
blend.body_layout.addWidget(opacity)

actions = QtWidgets.QHBoxLayout()
apply = AccentButton("应用", blend.view)
reset = Button("重置", blend.view)
actions.addWidget(apply, 1)
actions.addWidget(reset, 1)
blend.body_layout.addLayout(actions)
apply.clicked.connect(lambda: print(mode.currentText(), opacity.value()))
reset.clicked.connect(lambda: (mode.setCurrentIndex(0), opacity.setValue(40)))

for title in ("色度", "锐化"):
    card = panels.add_card(ExpandableCardWidget(title))
    card.body_layout.addWidget(Slider(parent=card.view))

# 将 panels 添加到应用自己的布局中。
```

| 接口 | 行为 |
| --- | --- |
| `set_expanded(expanded, animated=True)` | 展开或收起；`animated=False` 立即切换 |
| `is_expanded()` / `isExpanded()` | 读取当前目标展开状态 |
| `toggle()` | 切换展开状态 |
| `expandedChanged(bool)` | 目标展开状态改变时发出的信号 |
| `set_title()` / `setTitle()`、`title()` | 更新或读取标题 |
| `header_button` | 可聚焦的原生标题按钮 |
| `view`、`body_layout` / `viewLayout` | 内容控件与同一内容布局 |

`setExpanded()` 是 `set_expanded()` 的 Qt 风格入口。点击内容区的应用、重置等按钮不会改变卡片的展开状态。

`AccordionWidget` 默认允许多组独立展开。构造时传入 `exclusive=True`，或调用 `set_exclusive(True)`，即可最多保留一组展开；仍然允许全部收起。`add_card()` 返回加入的卡片，`cards()` 按布局顺序读取卡片，`remove_card(card, delete=False)` 将卡片移出容器，`delete=True` 同时按 Qt 生命周期释放卡片及其控件。上述设置也提供 `addCard()`、`removeCard()`、`setExclusive()`、`isExclusive()` 入口。

运行 `python examples/expandable_cards.py`，或双击 `examples/run_expandable_cards.bat`，可查看截图中的三组参数、主题切换和独立／互斥展开。工作台的“卡片容器”页也接入了折叠设置。本地文档 `#/cards/expandable` 展示实际 Qt 组件录制的动画。

折叠卡片的布局、绘制与动画属于 Qt / Python 界面逻辑，不依赖 C 扩展；强制 Python 后端时也可使用。

## 尺寸与资源

应用列表示例采用适合实际桌面的紧凑密度：行高 72、标题 14px、说明 12px、图标 40，打开按钮使用库默认的 80×32。表情卡片为 128×128，Unicode 表情使用 40px。所有数值都是 Qt 逻辑像素，由 Qt 跟随系统 DPI 缩放；参考图仅用于风格和布局，不把截图物理像素当作控件尺寸。

标题、说明和按钮保持常规字重，英文优先 Segoe UI、中文回退 Microsoft YaHei UI。第一条展示与网站共用的项目主图标及 `PluentPy` / `MIT License`，第二条展示 `FluentIcon.BUILDING_BANK` 及“文本” / “我是文本”。卡片本体不限定应用行尺寸，可自行组合内容布局。

外观与行为需求参考用户截图及 [QFluentWidgets 的公开卡片说明](https://qfluentwidgets.com/pages/components/cardwidget/)。组件与布局在本仓库独立编写，不依赖 `qfluentwidgets` 包。示例表情使用 Unicode 与系统 Emoji 字体；应用行使用项目主图标与微软官方 `FluentIcon.BUILDING_BANK`。图标库中仍保留此前新增的 [Music Note 2 SVG](https://github.com/microsoft/fluentui-system-icons/blob/main/assets/Music%20Note%202/SVG/ic_fluent_music_note_2_24_regular.svg)，以及微软图标的完整 MIT 许可。既有 `Card` / `ExamplePanel` 保持原有用途。
