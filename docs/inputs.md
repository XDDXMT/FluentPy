# 前后缀与分格输入

运行 `python examples/advanced_inputs.py`，Windows 可双击 `examples/run_advanced_inputs.bat`。
工作台：“文本与选择”页向下滚动。网页文档：输入框 → 带前缀与后缀的输入框／多格密码与验证码。

## AffixLineEdit

```python
from fluentpy import AffixLineEdit

address = AffixLineEdit("example.hostname", prefix="https://", suffix=".com")
address.setText("fluentpy")
print(address.text())  # fluentpy
print(address.full_text())  # https://fluentpy.com
address.set_prefix("http://")
address.set_suffix(".cn")
```

直接继承已有 LineEdit，保留焦点底线、输入／清空、只读、验证器和 Qt 信号。前后缀是固定的 Qt 标签，点击装饰区仍会聚焦输入框；不进入可编辑文本、复制和清除结果。可同时设置前后缀，也可只设置一侧。窄宽度下缩略装饰文字并保留编辑空间，完整装饰保留为提示。

`prefixChanged(str)`／`suffixChanged(str)` 只表示装饰变化；中间值继续使用 QLineEdit 的 `textChanged`。`full_text()` 是显示片段的简单连接，不做网址或金额有效性校验，实际业务验证由应用提供。

## PinCodeEdit

```python
from fluentpy import PinCodeEdit

pin = PinCodeEdit(4, masked=True)  # 默认仅允许ASCII数字
pin.completed.connect(lambda _value: print("填写完整"))
pin.textChanged.connect(lambda value: print("已填写位数：", len(value)))

code = PinCodeEdit(6, masked=False)  # 明文验证码
code.set_text("123456")
code.set_length(4)  # 保留并截断为1234
```

每一格直接复用原生 LineEdit。支持 1～32 格、单字符输入后前进、左右方向键、Home／End、Tab 离开、Delete、空格位退格回删、整段粘贴与输入法提交。每格存放一个 Unicode 字符；`digits_only=False` 接受可显示的字符。`set_masked(False)` 显示明文；默认 Password 回显模式继续使用 Qt 的掩码和复制保护。

- `text()`：返回已填写字符连接后的实际值，即使掩码显示也返回明文；不要记录真实密码。
- `set_text(value)`：原子设置值，超长或非法字符抛出异常，原值不变。
- 用户整段粘贴：从首格回填，超长截断；短片段从当前格写入。非法字符拒绝整次粘贴，空剪贴板不改变原值。
- `is_complete()`／`completed(str)`：检查每格是否均已填写，完成信号在新的完整值形成时发出。
- `clear()`、`set_read_only()`、`set_digits_only()`、`set_length()`：控制内容、只读、字符限制与格数。程序设置值不受只读限制。
- `cells()`：只读元组中是实际的 LineEdit 控件，供应用设置辅助信息；组控件拥有并管理其生命周期。

字符校验、分格和截断通过 `fluentpy.backends.input.split_code` 调用 `native/input_accel.c`；保留行为兼容的 Python 实现。自动模式下旧扩展缺少本组接口时只回退分格输入，不影响其他 C 接口。控件事件、布局、动画和剪贴板操作由 Qt 处理。
