# 菜单

工作台：**按钮与菜单 → 右键菜单**，在预览区域点击鼠标右键。多级、勾选、控件混排等类型均可从同一右键入口测试；键盘菜单键／Shift+F10 也可打开。独立示例：`python examples/menus.py`，Windows 可双击 `examples/run_menus.bat`。

工作台的输入框、文本区、代码编辑器及数值输入中的编辑菜单也统一使用 `ActionMenu`。复制、粘贴、撤销、只读与密码限制沿用 Qt 原有动作；分格输入的粘贴继续调用组件的整段粘贴接口。导航入口与概览卡片可右键查看示例、复制分类名称，文档标签可右键新建、切换、复制标题或关闭。

## 原有 ActionMenu

继续使用真实 `QAction` 管理图标、文字、可用状态、快捷键提示和勾选。动作变化会同步更新显示。菜单在所属窗口内部展开，共用已有淡入位移动画；长菜单由原有 FluentScrollBar 滚动。

```python
from fluentpy import ActionMenu, FluentIcon
from fluentpy.qt import QtCore, QtWidgets

menu = ActionMenu(window)
menu.add_action("打开文档", icon=FluentIcon.DOCUMENT_SAVE, callback=lambda: print("打开"))
menu.add_separator()
menu.add_action("显示扩展名", checkable=True, checked=True)
area = QtWidgets.QFrame(window)
area.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
area.customContextMenuRequested.connect(lambda point: menu.popup_at(area, point))
```

`addActions`／`addAction` 接受原生 QAction。快捷键参数提供显示文字；应用自行注册真正的 QAction／QShortcut 快捷键。

## 子菜单

```python
export = menu.add_menu("导出", icon=FluentIcon.ARROW_EXPORT)
export.add_action("JSON 配置")
images = export.add_menu("图像格式")
images.add_action("PNG 图像")
images.add_action("SVG 图像")
```

`add_menu` 返回新的子 ActionMenu；也可以提供尚未关联父级的已有 ActionMenu。`addMenu("名称")` 是便捷入口，`setTitle` 和 `setIcon` 同步修改父级入口。
同一子菜单不能共享给多个父级，不能形成循环；普通 QAction 继续允许共享。删除子菜单时移除父入口，隐藏锚点或窗口时关闭整条链并清理事件监听。

悬停180ms展开，点击或 → 立即展开；← 返回父级，Esc 逐级关闭。叶子动作执行一次，随后关闭整条菜单链。菜单在窗口右侧空间不足时向左展开，父级条目仍可点击。
条目高亮渐变，子菜单从所属条目一侧轻移展开，关闭时平滑淡出。收起时立即交还鼠标与键盘，连续右键可中断关闭动画并在新位置重新展开；隐藏窗口或锚点则立即清理。

## 勾选与互斥

已有 `checkable=True` 动作独立勾选。互斥项交给原生 `QActionGroup`：

```python
from fluentpy.qt import QtGui

group = QtGui.QActionGroup(menu)
group.setExclusive(True)
group.addAction(menu.add_action("按名称", checkable=True, checked=True))
group.addAction(menu.add_action("按修改日期", checkable=True))
```

互斥组选中项显示圆点，普通勾选项显示勾号，状态由 QAction／QActionGroup 管理。

## 原生控件混排

`add_widget(widget)`／`addWidget(widget)` 使用原生 `QWidgetAction` 接管内容，可与动作和分隔线混排。输入框、滑块、复选框等保留本来的交互；其他动作更新不会清空内嵌控件状态。

```python
from fluentpy import LineEdit, ToolTipSlider
from fluentpy.qt import QtWidgets

options = QtWidgets.QWidget()
layout = QtWidgets.QVBoxLayout(options)
layout.addWidget(LineEdit("筛选名称"))
layout.addWidget(ToolTipSlider())
menu.add_widget(options)
menu.add_separator()
menu.add_action("应用设置")
```

原有 `set_content_widget` 用于整个菜单只承载一个内容容器，保持兼容；这一模式与 QAction 行不可混用。

## 右键定位

`popup_at(anchor, QPoint)` 中的点属于锚点控件的局部坐标，可直接连接 `customContextMenuRequested`。普通 `popup(anchor)` 仍在控件附近展开。

工作台的输入框、文本区、代码编辑器、数值输入与表格使用统一的 ActionMenu。编辑器沿用 Qt 的原有动作和快捷键，保留只读、密码及分格输入的整段粘贴行为；动态创建的编辑器也会接入。导航与组件卡片可右键查看示例或复制分类名称，文档标签支持新建、切换、复制标题和关闭。原本禁用右键菜单的 FluentScrollBar 保持原有策略。

## 系统托盘

`SystemTrayMenu` 继承真正的 `QMenu`，能够交给原生 `QSystemTrayIcon.setContextMenu`。它在窗口之外使用系统菜单行为，配色跟随主题；QMenu 的子菜单、动作组和执行接口均由 Qt 提供。

```python
from fluentpy import SystemTrayMenu, fluent_icon
from fluentpy.qt import QtWidgets

tray_menu = SystemTrayMenu(window)
tray_menu.add_action("显示窗口", callback=window.show)
tray_menu.addSeparator()
tray_menu.add_action("保持后台运行", checkable=True, checked=True)
tray = QtWidgets.QSystemTrayIcon(fluent_icon(FluentIcon.SETTINGS), window)
tray.setContextMenu(tray_menu)
# 应用需要时调用 tray.show()
```

示例默认不创建托盘图标；只有点击“显示系统托盘图标”才启用，切页或关闭示例会隐藏。实际可用性由当前桌面环境决定。

参考[公开菜单交互分类](https://qfluentwidgets.com/zh/pages/components/menu/)，在已有 ActionMenu 与 Qt 原生接口上独立实现，未复制参考项目的源码、示例文字、样式表或素材。
