# 滑块

工作台：直接点击侧栏的 **滑块**，或在组件概览中搜索 `Slider`。独立示例：`python examples/sliders.py`，Windows 可双击 `examples/run_sliders.bat`。

## 原有 Slider

继续继承原生 `QSlider`。水平与竖向采用同一套主题绘制，点击轨道定位，按住拖动；原生方向键、Home／End、PageUp／PageDown、步长、滚轮和范围接口继续可用。
坐标转换使用 Qt 的 QStyle 滑块映射函数，绘制和命中测试保持一致，支持 RTL 和 `setInvertedAppearance`。

```python
from fluentpy import Slider
from fluentpy.qt import QtCore

slider = Slider(QtCore.Qt.Orientation.Horizontal)
slider.setRange(0, 100)
slider.setValue(35)
slider.setSingleStep(1)
slider.valueChanged.connect(print)

vertical = Slider(QtCore.Qt.Orientation.Vertical)
vertical.setFixedSize(38, 220)
```

悬停时中心圆放大，按住时缩小；键盘焦点用圆环标示，禁用时使用主题禁用色。
点击轨道、键盘和程序调整时，手柄与已选轨道平滑过渡；直接拖动始终紧随指针，真实数值与信号不会等待动画结束。连续调整会从当前画面续接，隐藏或禁用时停止动画。
原有 `set_track_gradient` 和 `clear_track_gradient` 仍可使用，渐变及棋盘底纹也支持竖向。

## ToolTipSlider

```python
from fluentpy import ToolTipSlider

value_slider = ToolTipSlider()
value_slider.setRange(-50, 150)
value_slider.setValue(35)
```

默认显示当前数值，例如 `35`；不会把任意取值范围转换为百分比。提示在悬停、键盘聚焦或拖动时跟随实际滑块，位于所属窗口内部，不创建独立弹窗，也不接收鼠标。窗口边缘会避让；隐藏、禁用、失焦或离开时按交互状态收起。
提示使用淡入、轻移和淡出动画，快速移入移出可以平滑反向；跟随绘制中的手柄，拖动时不单独滞后。
`setValueFormat` 接受 Python 格式文字，例如 `{value}`、`{value}%`、`{value:03d} px`；格式无效时拒绝并保留旧格式。

## RangeSlider

```python
from fluentpy import RangeSlider

interval = RangeSlider()
interval.setRange(0, 100)
interval.setValues(20, 80)
interval.valuesChanged.connect(lambda lower, upper: print(lower, upper))
interval.setActiveHandle("upper")
```

- `values()` 返回 `(lower, upper)`；`lowerValue()`、`upperValue()` 返回端点。
- `setValues(lower, upper)` 原子设置有序且在允许范围内的整数区间，非法值不改变原值。
- `setLowerValue`／`setUpperValue` 设置单端点；拖动时端点互不穿越。
- `valuesChanged(int, int)` 表示已提交区间；两个端点也分别有 `lowerValueChanged`／`upperValueChanged`。
- `setActiveHandle("lower" | "upper")` 选择键盘目标；Space 切换端点，方向键与 Home／End 调整当前端点，Tab 离开组件。
- `setRange` 仍设置允许的最小／最大值；改变范围时，两个端点一起夹紧。继承的 `rangeChanged` 表示允许范围，区间业务使用 `valuesChanged`。

## 松开后提交

`setTracking(False)` 保留 Qt 的拖动草稿规则：`sliderMoved`／`sliderPosition` 用于过程预览，松开时提交 `valueChanged`。区间组件也在松开时提交 `valuesChanged`，拖动时只移动当前端点的预览。

实现基于本项目原有 Slider 与 Qt 接口。参考[公开滑块交互分类](https://qfluentwidgets.com/zh/pages/components/slider/)，未复制其代码、样式或素材。
