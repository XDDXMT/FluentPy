# 开发与贡献

FluentPy 使用 Python 组织公开接口和 Qt 界面，C 扩展处理计算并保留 Python 兼容实现。修改前先确认代码所属层，避免在界面绘制中重复实现后端计算。

## 环境与检查

建议在虚拟环境中安装开发依赖：

```console
python -m pip install -e ".[dev]"
python scripts/check_quality.py
python -m pytest
```

`check_quality.py` 统一运行 Ruff 和 clang-format，检查 Python 导入、格式、基本静态错误，以及 C 源码格式。工具版本固定在 `pyproject.toml` 的开发依赖中。需要自动整理时运行：

```console
python scripts/check_quality.py --fix
```

自动修复后仍应阅读差异并运行相关测试。`scripts/prepare_release.py` 在生成发布目录前执行质量检查；检查失败时终止构建。

## 目录职责

| 位置 | 职责 |
| --- | --- |
| `src/fluentpy/__init__.py`、`widgets/__init__.py` | 公开组件导出，保持现有导入方式兼容 |
| `src/fluentpy/widgets/` | Qt 组件、绘制、交互与对象生命周期 |
| `src/fluentpy/backends/` | 后端选择、C 绑定调用与兼容实现 |
| `native/` | C 计算及 CPython 接口，参数和返回值与兼容实现一致 |
| `examples/` | 可独立运行的示例和工作台，业务演示不进入组件实现 |
| `tests/` | 参数、交互、生命周期和安装行为验证 |
| `scripts/` | 可复用的构建、检查与基准工具 |
| `sites/fluentpy-docs/` | 文档内容、生成器和配图录制工具 |

组件按职责组织。普通按钮和外观变体在 `button.py`，切换、下拉、分体和加载按钮分别在对应模块。`advanced_button.py` 保留旧模块的导出；新增代码从公开入口或具体组件模块导入。窗口内菜单使用 `ActionMenu`，系统托盘使用 `SystemTrayMenu`，两者的定位和关闭方式不同。

模块拆分应以复用关系和生命周期为依据。只服务一个组件的辅助类与该组件放在一起；跨组件共享的绘制或交互代码再提取为私有辅助模块。

## 命名、接口与注释

- Python 自定义接口使用 `snake_case`；覆盖 Qt 接口时保留 `setText`、`paintEvent` 等原名。
- 新增或修改公开接口时补充参数和返回类型。Qt 信号、所有权、取值范围和异常行为应在文档或 docstring 中说明。
- 注释解释约束和取舍，例如为什么需要监听父控件、为什么绘制范围跨过分隔线。直观的赋值和转发无需逐行解释。
- 保留与问题有关的兼容说明；删除重复描述代码动作、宣传性质或已失效的注释。
- 不使用通配导入。独立示例确需先定位源码再导入时，仅在相应入口允许 `E402`，组件实现仍按正常顺序导入。

## 验证与文档

行为变化应覆盖有效输入、边界条件和实际交互。Qt 组件还需检查键盘、禁用、隐藏与销毁；涉及主题时查看明暗效果。纯格式调整不新增重复测试，沿用现有测试验证行为。

修改后端时分别验证 Python 和 C 路径；C 扩展不可用时应维持自动回退，显式 `native` 模式仍需明确报错。构建方式见[原生扩展说明](docs/native-build.md)。

文档中的源码位置和接口签名由生成器提取。组件文件移动或接口变化后运行：

```console
python sites/fluentpy-docs/build_content.py
python sites/fluentpy-docs/validate_site.py
```

发布前还需验证独立环境安装、许可证和发布文件清单，具体流程见[构建与发布](docs/publishing.md)。已发布版本的文件与标签保持原样，后续改动进入下一版本。
