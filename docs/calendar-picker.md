# 日历与日程

`CalendarPicker`选择一个日期，`DateRangePicker`选择连续日期区间，`DateTimePicker`组合日历与时／分／秒滚轮。三者均为实际Qt控件，弹层属于当前窗口内部，复用库内的按钮、Fluent图标和动画机制。

运行`python examples/calendar_picker.py`或双击`examples/run_calendar_picker.bat`；工作台的“日历与日程”页也复用相同组件。可附加`--dark`及`--open single|range|datetime`。

## 单个日期

```python
from fluentpy import CalendarPicker, DateRangePicker, DateTimePicker
from fluentpy.qt import QtCore

picker = CalendarPicker()
picker.set_date(QtCore.QDate(2024, 2, 26))
picker.dateChanged.connect(lambda value: print(value.toString("yyyy-MM-dd")))
picker.dateAccepted.connect(lambda value: print("选择完成", value))
```

初始为空，`date()`返回无效QDate；`clear()`或设置无效QDate清空。点击可用日期即提交。今天显示强调色实心圆，已选日期显示圆环；相邻月份日期也可点击。点击月份标题进入月份视图，再点进入年份视图。

## 日期区间

```python
interval = DateRangePicker()
interval.set_range(QtCore.QDate(2024, 3, 13), QtCore.QDate(2024, 3, 21))
interval.set_disabled_weekdays((5, 6))
interval.rangeChanged.connect(lambda start, end: print(start, end))
```

第一次点击选起点，悬停预览，第二次点击完成；支持反向和同一天。完成前保持旧值，Esc或外部点击取消草稿。`start_date()`／`end_date()`返回QDate副本；`rangeAccepted`在每次完成选择时发出。

灰色底色延伸到两个端点圆环的外缘，并沿圆弧裁切。跨行的中间段铺满行宽；同一天显示完整圆形底色。预览以190ms缓动伸缩，悬停140ms过渡，选中圆环200ms过渡，切月180ms；展开220ms、关闭140ms。

禁用策略只限制区间端点，允许跨过内部的周末／禁用日。区间是包含端点的自然日期范围，不会自动排除内部禁用日期。

## 日期时间

```python
scheduled = DateTimePicker()
scheduled.setDateTime(QtCore.QDateTime(QtCore.QDate(2026, 2, 10), QtCore.QTime(20, 0, 0)))
scheduled.dateTimeChanged.connect(lambda value: print(value.toString("yyyy-MM-dd HH:mm:ss")))
scheduled.set_date_time_bounds(
    QtCore.QDateTime(QtCore.QDate(2026, 2, 10), QtCore.QTime(9, 30, 15)),
    QtCore.QDateTime(QtCore.QDate(2026, 2, 10), QtCore.QTime(20, 0, 0)))
```

左侧日历和右侧时、分、秒均修改草稿；✓或时间滚轮上的Enter提交，×／Esc／外部点击取消。各列独立循环，秒59→00不进位。返回本地QDateTime，精确到秒，截去毫秒；其他时区的输入先转成本地时间。`date_time()`／`dateTime()`读取副本，`dateTimeAccepted`在每次确认时发出。

上下界包含完整时分秒；超界值夹紧，禁用日期报错。边界当天的滚轮也自动夹紧。默认日历为公历1至9999年，不提供时区选择器。

## 共同设置与操作

```python
picker.set_date_bounds(QtCore.QDate(2024, 1, 1), QtCore.QDate(2026, 12, 31))
picker.set_disabled_dates([QtCore.QDate(2024, 5, 1)])
picker.set_disabled_weekdays((5, 6))  # 0星期一，6星期日
picker.set_locale("en_US")
picker.set_first_weekday(6)          # Sunday
picker.set_placeholder_text("Pick a date")
```

配置先校验再生效。日历和区间已有值因此不可选时清空；日期时间超界时夹紧。无效程序设置抛出TypeError或ValueError，不隐藏错误。

方向键移动日期，PageUp／PageDown切月，Ctrl加翻页键切年；Home回到本周起点，Ctrl+Home回到今天。Tab／Shift+Tab在网格、标题、翻页和确认控件间循环。滚轮切月；时间滚轮支持鼠标滚动、拖动、点击与键盘。

弹层在边缘避让，窄窗口的日期时间改为上下排列。单日／区间至少需要280×250的所属窗口，日期时间至少需要280×350；更小窗口不展开。隐藏、禁用、切页或销毁时取消草稿。推荐字段高度36逻辑像素，单日／区间弹层360×410，日期时间常规680×470。

## C优先与Python兼容

`native/calendar_accel.c`负责月份42格、公历闰年、日期平移、禁用策略、区间规范化、日期时间夹紧与时分秒候选。`src/fluentpy/backends/_calendar_python.py`同步维护兼容实现。默认auto优先C；缺失、ABI不兼容或旧版缺少日历接口时自动回退Python，旧版仍可用的时间／日期C接口保持使用。

`acceleration_backend()`返回`native`或`python`。Qt负责动画、布局、绘制和输入事件。此处没有对小规模日期计算承诺固定加速倍数。
