# 消息条

`InfoBar` 与 `ProgressInfoBar` 是 FluentPy 自己的消息条实现。只借鉴公开页面展示的交互与视觉结构；没有复制 QFluentWidgets 的源码、样式、文案或图片，也不依赖其软件包。现有 `Toast`、`ColorToast`、`ProgressToast`、`Button` 和 `ProgressBar` 均继续复用。

运行 `python examples/info_bar.py` 或双击 `examples/run_info_bar.bat`；工作台入口：消息与对话框 → 自定义测试 → 组件选择“消息条”或“任务消息条”。工作台以实时预览和简化参数编辑为主，独立示例保留完整逐项用例。

工作台“消息与对话框”顶部选择“嵌入示例”：关闭页面消息观察布局补位；填写备注后提交，空值显示警告、有效内容显示成功；手动推进35%的任务进度并完成或重新开始。点击“恢复全部示例”可再次显示已经关闭的消息。这些示例由实际Qt布局管理，无需先触发浮层。

## 普通状态消息

```python
from fluentpy import InfoBar

bar = InfoBar.success(
    "保存完成", detail="当前设置已经写入本地文件。", parent=window,
    orientation="horizontal", placement="top-center", timeout_ms=4000,
    action_text="打开目录", action_callback=open_output_directory,
)
```

`info`、`success`、`warning`、`error` 分别显示信息、成功、警告、失败状态。也可直接构造 `InfoBar(..., tone="accent")` 或用 `InfoBar.notify()` 设置任意已有色调。`color` 覆盖状态图标颜色；`set_background(light, dark)` 指定明暗主题背景，`set_background()` 恢复状态背景。`set_icon()` 接受现有 `FluentIcon` 或 `QIcon`，None恢复默认状态图标。

`orientation="horizontal"` 横向排列标题和正文；`"vertical"` 纵向排列。长文由实际Qt布局换行并撑高；`card_width` 是浮层可见卡片的建议宽度，不含阴影，受所属窗口约束。自动宽度范围280～720逻辑像素。

`closable=False` 隐藏关闭按钮，应用仍可调用 `close()`。`action_text` 和 `set_action()` 自定义按钮文字与回调，默认点击后关闭；`close_on_action=False` 保持显示。操作按钮和用户额外控件在标题／正文下方排列。

## 内联与自定义内容

```python
from fluentpy import Button, InfoBar, LineEdit

bar = InfoBar("检查设置", "请确认输出目录。", window,
              tone="warning", orientation="vertical", closable=False)
editor = LineEdit("输入目录", bar.content_widget)
bar.content_layout.addWidget(editor)
confirm = Button("确认目录", bar.content_widget)
confirm.clicked.connect(bar.close)
bar.content_layout.addWidget(confirm)
window.content_layout.addWidget(bar)
bar.show()
```

`content_layout` 是统一内容容器的现有QVBoxLayout，直接添加原生控件或嵌套布局；不要重复创建容器布局。动态增加、隐藏、删除控件后会重新测量高度。

直接加入页面布局时，消息条位置和宽度由页面布局管理，关闭动画只改变透明度。调用 `show_at()` 则进入现有浮层排列；不要将同一个消息条同时加入页面布局和浮层排列。支持 `top-left`、`top-center`、`top-right`、`bottom-left`、`bottom-center`、`bottom-right`，与既有吐司共用补位动画。

工厂方法创建的消息条关闭后自动释放；直接构造的实例由应用或父控件管理，可在隐藏后重新显示。`closed()` 在关闭动画结束并真正接受关闭时发出。通过 `set_timeout()` 设置倒计时；0手动关闭，浮层倒计时在入场动画后开始，悬停暂停。

## 任务消息

```python
from fluentpy import ProgressInfoBar

task = ProgressInfoBar.start("正在导出", detail="正在准备文件…",
                            parent=window, indeterminate=True)
task.set_progress(65)
task.set_detail("已处理 65%，正在写入剩余文件。")
task.finish("导出完成", timeout_ms=1800)
# 失败路径使用 task.fail("导出失败", timeout_ms=0)
```

任务消息复用现有 `ProgressBar`、任务图标和消息条布局，不执行实际导出、上传等业务任务。

- `set_progress()` 接受有限的数字，显示值平滑过渡，目标范围0～100；`value()` 读取目标值。
- `set_indeterminate(True)` 隐藏百分比条并显示旋转状态；提交百分比后自动恢复进度条。
- `finish()` 将进度更新到100并显示成功；`fail()` 保留已完成进度并显示失败。`state()` 返回running／success／error。
- `progressChanged(float)`、`stateChanged(str)`、`finished(bool)` 可供应用监听；终态只提交一次，后续进度和重复结束不会覆盖状态。
- `start()` 不自动关闭；完成默认1800ms后关闭，失败默认保持。未知进度动画在隐藏、关闭和完成时停止。C扩展不可用时，以上Qt界面功能仍可正常使用。
