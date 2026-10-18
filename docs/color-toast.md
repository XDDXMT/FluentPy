# 顶部色条通知

`ColorToast` 继承现有 `Toast`，复用窗口内表面、关闭按钮、淡入淡出、堆叠与补位。标题、正文使用 Qt 标签，操作按钮直接使用库内 `Button`。

独立示例：`python examples/color_toast.py`，或双击 `examples/run_color_toast.bat`。工作台入口：消息与对话框 → 自定义测试 → 组件选择“顶部色条吐司”。工作台以实时预览、简化参数和折叠高级选项为主，下文的完整逐项操作也可在独立示例中测试。

```python
from fluentpy import ColorToast

notice = ColorToast.notify(
    "通知标题",
    detail="这是一条带操作按钮的消息。",
    parent=window,
    placement="top-center",
    color="#858585",
    action_text="查看详情",
    action_callback=lambda: print("查看详情"),
    card_width=300,
    timeout_ms=4000,
)
```

## 颜色与内容

顶部色条为3个逻辑像素，跟随卡片圆角裁切。`color` 接受有效 QColor、颜色字符串或 Qt.GlobalColor。读取 `color()` 得到目标颜色副本；修改已显示通知时以160ms过渡到新色。

```python
notice.set_color("#009faa")
notice.set_title("新的标题")
notice.set_detail("更新后的正文，长文字会自动换行。")
notice.set_color(None)  # 清除自定义颜色，恢复当前tone的主题色
notice.set_tone("warning")  # 选择警告色，并清除自定义颜色覆盖
```

`tone` 支持 `success`、`error`、`warning`、`accent` 和 `info`。也可使用 `ColorToast.success()`、`.error()`、`.warning()`、`.info()` 快捷创建。指定自定义颜色后，主题切换仍保留该颜色；未指定时使用当前tone对应的明暗主题颜色。

标题与正文按纯文本显示，正文为空时隐藏正文行。默认自动测量可见宽度，范围240～520逻辑像素；`card_width` 可设120～1200或None。该值不包含阴影留白，并始终受所属窗口边界约束。高度由实际Qt布局测量，包含换行、按钮和用户添加的控件，不再分别估算文字高度。

## 操作按钮和自动关闭

```python
notice.set_action("重试", callback=retry, close_on_action=False)
notice.actionTriggered.connect(on_action)
notice.set_timeout(0)  # 手动关闭
notice.set_action("")  # 移除操作按钮及占位
```

点击按钮发出 `actionTriggered()` 并执行已连接的回调，默认关闭本条通知。`close_on_action=False` 保持显示。替换操作时断开先前通过 `set_action` 设置的回调，保留其他信号监听者。

按钮文字完全由应用提供：创建时使用 `action_text="立即重试"`，创建后使用 `set_action("打开文件", callback=open_file)`。`action_button` 是已有的 `Button` 实例，可继续设置图标、提示文字等属性。独立示例与工作台中，勾选“显示操作按钮”后即可编辑旁边的“按钮文字”输入框。

默认在入场结束后停留4000ms，鼠标悬停时暂停倒计时，离开后继续。`timeout_ms=0` 手动关闭。通过 `notify()` 或快捷方法创建的通知关闭后自动释放；直接构造 `ColorToast(...).show_at(...)` 则由应用管理生命周期。

## 在同一容器中编排自己的内容

`content_widget` 是统一的内容容器，`content_layout` 是它现有的 `QVBoxLayout`。标题、正文和可选操作行已在这个布局中；使用 `addWidget()`、`addLayout()` 继续添加内容，不要再给该容器创建第二个布局。通知会在添加、隐藏、删除控件或尺寸变化后重新测量并调整堆叠。

```python
from fluentpy import Button, ColorToast, LineEdit
from fluentpy.qt import QtWidgets

notice = ColorToast("保存备注", "内容和按钮均由应用编排。", window, card_width=340)
editor = LineEdit("输入备注", notice.content_widget)
notice.content_layout.addWidget(editor)

actions = QtWidgets.QHBoxLayout()
save = Button("保存", notice.content_widget)
cancel = Button("取消", notice.content_widget)
save.clicked.connect(lambda: print(editor.text()))
save.clicked.connect(notice.close)
cancel.clicked.connect(notice.close)
actions.addWidget(save)
actions.addWidget(cancel)
actions.addStretch()
notice.content_layout.addLayout(actions)
notice.show_at("top-right")
```

自定义按钮使用自己的 `clicked` 回调，关闭行为由应用决定；通知不自动改写这些按钮的内容。控件归内容容器所有，随通知释放。空间由所属窗口限制，自定义控件应使用可伸缩的布局，避免设置超出窗口的固定尺寸。示例中的“自定义内容示例”会显示一个输入框和两个原生按钮，可直接操作。

## 六种位置与混合叠放

`Toast`、`ColorToast` 与 `ProgressToast` 都支持：

| 顶部 | 底部 |
| --- | --- |
| top-left | bottom-left |
| top-center | bottom-center |
| top-right | bottom-right |

最新消息靠近锚定边；顶部向下叠放，底部向上叠放。相同窗口与位置的三种通知共用排列器，关闭后平滑补位；居中位置随卡片宽度与窗口尺寸重新居中。不同窗口和位置互相独立，空间不足时保留较新的消息。

```python
from fluentpy import ProgressToast

ProgressToast.start("Custom toast view", parent=window,
                    placement="bottom-center", indeterminate=True,
                    severity="warning")
```

这种小型进度提示继续使用原有 `ProgressToast`，循环轨道仍只显示一段移动实心线。顶部色条通知的布局、颜色和动画均属于Qt界面呈现，不新增计算后端；C扩展不可用时仍可使用。
