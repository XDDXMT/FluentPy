# 后端选择与兼容回退

FluentPy默认让组件保持可用，C扩展作为首选加速路径。扩展缺失、导入失败（包括不匹配的二进制），或旧扩展缺少某个组件的接口时，该组件自动使用Python兼容实现。

当前覆盖 CodeEdit 文本扫描、日期／日历运算、时间换算与滚轮、拖放筛选、快捷键校验、颜色策略和分格输入校验八组后端。Qt 负责界面与动画；回退不改变组件类名和使用方式。旧二进制只让缺少接口的那组回退，可用的其他 C 接口继续使用。

通过 `python -m pip install fluentpy-qt` 安装时，Windows x64 / 普通 CPython 3.13 会选择内含 C 扩展的 wheel。其他兼容环境使用通用 Python wheel，默认回退，无需编译器。安装名为 `fluentpy-qt`，导入名仍为 `fluentpy`。

| FLUENTPY_BACKEND | 行为 |
| --- | --- |
| `auto`（默认） | 对每组接口优先C，不可用时回退Python |
| `python` | 全部使用Python兼容实现，适合验证兼容性或定位问题 |
| `native` | 显式要求C；缺少对应接口时抛出构建提示，不静默回退 |

通常无需设置环境变量。可在启动前强制使用Python，例如Windows PowerShell：

```powershell
$env:FLUENTPY_BACKEND = 'python'
python examples/showcase.py
```

恢复默认模式：

```powershell
$env:FLUENTPY_BACKEND = 'auto'
```

`FLUENTPY_BUILD_NATIVE` 只控制源码构建时是否尝试生成二进制，不会为已安装的通用 wheel 自动补装扩展；`FLUENTPY_BACKEND` 控制运行时选择，两者用途不同。

## 查看实际选择

在创建QApplication之后，可通过各组件查询：

```python
from fluentpy import CodeEdit, DatePicker, TimePicker, FileDropWidget, ShortcutPicker

for widget in (CodeEdit(), DatePicker(), TimePicker(), FileDropWidget(), ShortcutPicker()):
    print(type(widget).__name__, widget.acceleration_backend())
```

输出为 `native` 或 `python`。源码工作台底部显示“C后端就绪”“Python兼容模式”或“混合后端”；悬停可查看实际选择。wheel 不包含工作台示例。

也可从 `fluentpy.backends` 导入 `text`、`date`、`time`、`calendar`、`drop`、`shortcut`、`color`、`input` 模块：`backend_name()` 返回当前选择，`native_available()` 判断对应 C 能力是否存在，`native_error()` 返回扩展导入或接口缺失的原因。即使 C 能力存在，显式 python 模式仍使用 Python。

回退只处理加速后端不可用，不隐藏非法日期、无效后缀或错误快捷键等输入问题。Python与C路径保持相同的日历边界、筛选顺序、拒绝原因和快捷键冲突规则，相关测试同时覆盖两种实现。

C加速的构建方式见[构建与打包](native-build.md)。构建后重启旧进程，以加载新的二进制与Python接口。
