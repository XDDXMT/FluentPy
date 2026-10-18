# 颜色与取色

运行 `python examples/colors.py`，或双击 `examples/run_colors.bat`。
工作台：`python examples/showcase.py --page colors`。
官网文档：<https://fluentpy.mcxmcl.cn/#/colors>。

这组控件使用现有 Button、LineEdit、SpinBox、ComboBox、Slider、ActionMenu、MaskedDialog 和 FluentScrollBar；色谱、色块、渐变轨道与取色预览属于颜色组件本身的 Qt 绘制。

## 编辑弹层

```python
from fluentpy import ColorPickerButton

picker = ColorPickerButton("#80e4579b", parent=window, enable_alpha=True)
picker.colorPreviewed.connect(lambda color: print("草稿：", color.name()))
picker.colorChanged.connect(lambda color: print("确认：", color.name()))
window.content_layout.addWidget(picker)
```

编辑草稿不会修改按钮颜色；确定后才提交，取消、Esc、点击外侧或隐藏窗口均保留原色。弹层限制在所属窗口内，空间不足时使用原有滚动条。

Hex 接受 `#RGB`、`#RRGGBB` 和 **`#AARRGGBB`**，8 位格式透明度在最前，与 Qt 一致。输入无效时保留最后一个有效颜色并暂停确认。`enable_alpha=False` 隐藏 Alpha 并保持不透明。

## 色板与对话框

```python
from fluentpy import ColorPaletteButton, ColorDialog

palette = ColorPaletteButton("#0078d4", window)
palette.set_color(None)  # 自动颜色，color() 返回无效 QColor
palette.automaticSelected.connect(lambda: print("应用负责解析自动颜色"))

dialog = ColorDialog("#e4579b", "选择背景颜色", window, enable_alpha=True)
dialog.currentColorChanged.connect(lambda color: print("预览", color.name()))
dialog.colorSelected.connect(lambda color: print("确认", color.name()))
dialog.open()
```

色板包含 60 个主题色和 10 个标准色，“更多颜色”打开同一个 ColorDialog。对话框复用窗口内遮罩，`color()` 读取已提交颜色，`current_color()` 读取草稿。调用 `set_color()` 不会发出提交信号；确认才发出 `colorSelected`。使用预览信号修改应用时，应连接 `rejected` 恢复应用原状态。

## 嵌入面板与圆形色块

```python
from fluentpy import ColorPickerPanel, ColorSwatchGroup

editor = ColorPickerPanel("#e4579b", window)
editor.set_format("hsv")  # 或 rgb
swatches = ColorSwatchGroup(["#4ba6ed", "#72d4f4", "#253e72", "#c7a2ec"], window)
swatches.colorChanged.connect(editor.set_color)
```

面板实时发出 `colorChanged`；`validate()` 检查 Hex 并返回 bool。`set_previous_color()` 设置对照色。色块组使用互斥的原生 Button 与 Qt 网格布局，窗口变窄时换行；支持 1～256 个颜色。颜色读取接口返回 QColor 副本。

## 屏幕取色

```python
from fluentpy import EyeDropperButton, ScreenColorPicker

eyedropper = EyeDropperButton("#0078d4", window)
eyedropper.colorChanged.connect(lambda color: print(color.name()))
eyedropper.failed.connect(print)

# 无按钮的用法：按应用自己的触发操作调用 picker.start()
picker = ScreenColorPicker(window)
picker.colorSelected.connect(lambda color: print(color.name()))
```

只有显式启动才读取屏幕，启动时保存截图，预览不会采到取色覆盖层。单击／Enter／Space 确认，Esc／右键取消，方向键逐逻辑像素微调。支持多显示器、负坐标及不同屏幕像素比例。取色结束、窗口隐藏、控件删除和应用退出时释放覆盖层、截图及鼠标形状。屏幕截图受系统限制时发出 `failed(str)`，原颜色不变。

文档取色配图使用合成测试画布，没有采集桌面内容。吸管来自 [Microsoft Fluent System Icons](https://github.com/microsoft/fluentui-system-icons/blob/main/assets/Eyedropper/SVG/ic_fluent_eyedropper_24_regular.svg)。

## 后端与复用接口

Hex 解析、格式化及 RGB／HSV 转换由 `native/color_accel.c` 承接；`fluentpy.backends.color` 自动选择后端，并同步维护 Python 实现。设置 `FLUENTPY_BACKEND=python` 强制兼容实现，`native` 显式要求 C，默认 `auto` 在旧／缺失扩展时按功能回退。Qt 负责交互、布局、动画、绘制与屏幕截图。

现有 `Slider.set_track_gradient([(0, color1), (1, color2)], checkerboard=True, thickness=8)` 可用于其他渐变参数条；`clear_track_gradient()` 恢复默认外观。仅水平轨道使用渐变，原有 QSlider 信号、键盘和鼠标行为继续保留。

现有 `ActionMenu.set_content_widget(widget)` 也可承载其他 Qt 表单，接管内容所有权并复用原窗口内弹层；自定义内容与 QAction 行不能混用。
