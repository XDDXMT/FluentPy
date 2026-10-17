# 时间选择器

`TimePicker`提供小时／分钟滚轮；设置`use_12_hour=True`时增加AM／PM列。点击字段任意一列打开页内浮层，滚动、拖动、点击相邻行或使用方向键选择，✓／Enter确认，×／Esc／点击外部取消。

```python
from fluentpy import TimePicker
from fluentpy.qt import QtCore

picker = TimePicker()  # 在QApplication创建后使用
picker.setTime(QtCore.QTime(14, 0))
picker.timeChanged.connect(lambda value: print(value.toString("HH:mm")))
picker.timeAccepted.connect(lambda value: print("确认", value.toString("HH:mm")))

ampm = TimePicker(use_12_hour=True)
ampm.setTime(QtCore.QTime(14, 0))  # 显示2 / 00 / PM
```

## 数据与交互

- 默认空值显示“小时／分钟”；12小时制还显示“AM/PM”。`time()`返回已提交QTime副本；空值返回无效QTime。
- 两种显示方式始终使用24小时制QTime传值，精确到分钟；传入的秒和毫秒截去，不四舍五入。午夜显示12:00 AM，正午显示12:00 PM。
- 各列独立选择：分钟59→00不改变小时；12小时模式下小时11→12保持原AM／PM，周期由第三列单独选择。AM／PM只各显示一行，空白行不能选择。
- `timeChanged`仅在已提交值改变时发出；`timeAccepted`在每次确认时发出，包括原值确认。取消不发出这两个信号。
- `set_time()`与`setTime()`设置值，`clear()`或无效QTime清空。`set_12_hour_clock()`／`set12HourClock()`只改变显示方式，保留已提交值并取消未保存草稿。
- 左右切换列、上下选择、PageUp／PageDown跳五项；Tab／Shift+Tab在滚轮、确认和取消之间切换。

## 布局与后端

字段推荐300×38逻辑像素，浮层约320像素宽、九行候选，在矮窗口中自动减少候选行。浮层为所属窗口的普通Qt子控件，不创建Qt.Popup或额外系统窗口；入场220ms淡入轻移，退场140ms，滚轮130ms缓动。隐藏、禁用、切页或销毁时收起并清理动画。支持明暗主题与强调色。

输入校验、时制换算、步进和候选行优先使用`native/time_accel.c`，扩展缺失、不兼容或旧版没有时间接口时自动回退Python。`picker.acceleration_backend()`返回`native`或`python`，遵循统一`FLUENTPY_BACKEND=auto/python/native`策略；未声称时间选择操作获得固定性能倍率。

单独运行`python examples/time_picker.py`或双击`examples/run_time_picker.bat`。完整工作台的“输入与日期”页也包含两种模式。修改源码或C扩展后，重启旧的示例程序以加载更新。
