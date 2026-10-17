# 文本处理 C 后端与性能实测

FluentPy 现在提供可选的 CPython C 扩展 `fluentpy._native`。第一批接入的是 CodeEdit 的 JSON 词元识别与 UTF-16 位置映射；Python 负责组件接口和交互，Qt 负责文档、排版与绘制。C 源码位于 `native/text_accel.c`，不依赖 Qt C++ 开发包。

## 使用方式

已编译扩展时自动使用 C，无需更换前端类名或业务代码：

```python
from fluentpy import CodeEdit
from fluentpy.backends.text import native_available

editor = CodeEdit()
editor.set_code('{"name": "FluentPy", "enabled": true}')
print(native_available())             # 当前解释器能否导入 C 扩展
print(editor.acceleration_backend())  # 当前高亮器使用 native 或 python
```

缺少与当前 Python 匹配的扩展时，默认自动回退到 Python。设置环境变量可以明确选择后端，建议在启动程序前设置：

```powershell
$env:FLUENTPY_BACKEND = 'auto'    # 默认：可用时使用 C
$env:FLUENTPY_BACKEND = 'python'  # 强制兼容实现，用于性能对照
$env:FLUENTPY_BACKEND = 'native'  # 要求 C；缺失时明确报错
```

以上三行是互斥的配置示例，选择需要的一行。编辑器在载入内容、切换语言或重新高亮时刷新后端选择，不在每一行上重复读取配置。

同一模式也作用于日期、拖放与快捷键策略。默认auto在对应C接口不可用时自动使用Python，不会禁用组件；`python`可强制兼容实现，`native`仅用于明确要求C的场景。详见[后端选择与回退](backends.md)。

编译与 wheel 安装详见 [C 后端构建说明](native-build.md)。当前实际编译和运行验证为 Windows x64、CPython 3.13.1、PySide6 / Qt 6.11.1；其他 Python 版本需要对应二进制或重新编译，不能共用这个 `.pyd`。

## 可以运行的对照 Demo

```powershell
python examples/text_performance.py
```

Windows 可双击 `examples/run_text_performance.bat`。界面提供 1,000、10,000、50,000 行 JSON，对照冻结的原始版本、Python 后端和 C 后端。测量在独立进程运行，示例窗口与下方编辑区仍可操作。界面会读取最近一次 `benchmarks/text-performance.json`，再次测试时更新报告。

命令行复现：

```powershell
python -B scripts/benchmark_text.py --lines 10000 --repeat 5 --output benchmarks/text-performance-10000.json
python -B scripts/benchmark_text.py --lines 50000 --repeat 3 --output benchmarks/text-performance-50000.json
```

## 如何理解结果

JSON 扫描的提速只对应迁入 C 的部分。载入与首帧还包含 Qt 文档创建、完整语法高亮、排版和绘制；滚动、按钮与布局不会自动获得同样的倍数。

本次原始数据、每轮耗时、Python/Qt 版本、源码 SHA-256 与完整性校验均保存在 `benchmarks/text-performance-*.json`。10,000 行数据包含 1,249 条记录、中文与 emoji，共 268,231 字节 UTF-8、266,481 个 UTF-16 单元、14,997 个高亮片段。

2026-10-16 本机实测：AMD Ryzen 9 9950X3D，Windows x64。10,000 行取五轮、50,000 行取三轮中位数。

| JSON 行数 | 项目 | 原始版本 | Python 后端 | C 后端 | C 相对原始 |
| --- | --- | ---: | ---: | ---: | ---: |
| 10,000 | JSON 逐行扫描 | 25.28 ms | 24.87 ms | 1.91 ms | 13.21x |
| 10,000 | 完整载入与首帧 | 64.93 ms | 66.54 ms | 42.73 ms | 1.52x |
| 10,000 | 完整重新高亮 | 98.31 ms | 98.18 ms | 73.69 ms | 1.33x |
| 10,000 | 30 次滚动绘制 | 100.43 ms | 98.53 ms | 100.59 ms | 1.00x |
| 50,000 | JSON 逐行扫描 | 127.21 ms | 123.88 ms | 10.73 ms | 11.85x |
| 50,000 | 完整载入与首帧 | 292.60 ms | 295.22 ms | 180.12 ms | 1.62x |
| 50,000 | 完整重新高亮 | 463.03 ms | 468.02 ms | 349.98 ms | 1.32x |
| 50,000 | 30 次滚动绘制 | 104.15 ms | 100.24 ms | 107.80 ms | 0.97x |

测量方法：每轮使用新进程，轮换后端执行顺序，取中位数；所有后端处理完全相同的输入。载入计时包含完整文档着色、三次事件处理及首帧；完成后另行检查文本完全相等、全部行数及高亮片段数。编辑计时先把目标行滚入视口，滚动计时包含 30 次实际绘制。逐行扫描使用与高亮器相同的输入方式。

## 万行 JSON 与 LineEdit

`LineEdit` 继承 Qt 的单行 `QLineEdit`，默认 `maxLength` 为 32,767；长文本可能被截断。本次万行输入在默认配置下实际只保留 32,767 个 UTF-16 单元，不能把这份不完整结果算作万行数据的提速。Qt 的单行定位、字体排版已经由原生实现负责，这个 JSON 扫描扩展没有加速 LineEdit。[Qt 官方说明](https://doc.qt.io/qt-6/qlineedit.html#maxLength-prop)

多行 JSON 应使用 CodeEdit，需要普通多行内容可使用 TextEdit。CodeEdit 的底层是面向大段纯文本优化的 QPlainTextEdit，仍提供原生光标、选择、复制粘贴与撤销重做。[Qt 官方说明](https://doc.qt.io/qt-6/qplaintextedit.html#detailed-description)

## 正确性与当前范围

两种后端都只做容错的语法着色，不验证或改写 JSON。C 输出与 Qt 一致的 UTF-16 位置，覆盖 emoji、孤立代理项、转义、Unicode 数字与编辑中的不完整内容。未闭合字符串中大量转义引号采用线性处理，避免重复扫描。

测试同时验证 native/Python 差分、缺失扩展回退、强制后端失败、撤销和重新选择后端。扩展当前仍使用普通 CPython GIL；这不是后台加载 API，Qt 对象操作继续在界面线程进行。
