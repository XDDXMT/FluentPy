# FluentPy 中文文档站

官网：[fluentpy.mcxmcl.cn](https://fluentpy.mcxmcl.cn/)。纯静态文档，无在线字体或服务器运行时依赖。

独立开源仓库：[XDDXMT/FluentPy-Docs](https://github.com/XDDXMT/FluentPy-Docs)，包含网页源码、完整静态页面及生成、校验和打包工具，采用 MIT 许可。媒体录制脚本统一保留在组件库的本目录，避免在文档仓库根目录重复分发。运行 `python scripts/export_docs.py --output <空目录>` 可导出独立仓库内容，忽略本机配置、缓存和构建产物。

独立检出后，可直接用 `python -m http.server 8767 --bind 0.0.0.0 --directory dist` 预览。生成 API 或 Qt 媒体时，把组件库克隆在旁边的 `FluentPy/` 目录，或设置环境变量 `FLUENTPY_SOURCE_ROOT`；脚本不再依赖固定的本机路径。

## 页面结构

- 简介先展示当前组件示例程序，之后直接展示 Qt → FluentPy 输入框过渡与 Python → C → Qt 流程两组 JS 动画，保留简短的项目说明与许可入口。
- 安装统一使用 `python -m pip install fluentpy-qt`，导入名保留 `fluentpy`。开始使用页提供 Windows／macOS／Linux 虚拟环境命令，并说明 wheel 与源码示例、C 加速包与通用包的区别；首页和常见问题提供 PyPI 入口。
- 组件目录 `#/components` 按用途分组，可按名称、类名和用途搜索，也可筛选分类。
- 组件页分为“示例与用法”和“API 参考”；配图后的代码默认收起，交互动图按需展开、播放或暂停。
- 侧栏按七组组织，当前分组默认展开；窄屏使用可收起的导航。常见问题 `#/faq` 按问题展开。
- 站内搜索支持组件名、方法名和完整类方法，例如 `CalendarPicker.set_disabled_dates`，搜索结果直接进入对应 API。
- C 后端原理动画在简介和 `#/performance/data-flow` 中展示，实测数据与示意动画分开标注。默认 C 优先，扩展不可用时使用 Python 兼容实现。

网页默认跟随系统主题，可切换浅色／深色；控件图片和 GIF 保持亮色。开启减少动画偏好时，动图默认显示静态预览；页面离开可视区域或标签页隐藏时暂停相关网页动画。

## 本地运行与维护

在仓库根目录运行：

```powershell
python sites/fluentpy-docs/build_content.py
python sites/fluentpy-docs/validate_site.py
python -m http.server 8767 --bind 0.0.0.0 --directory sites/fluentpy-docs/dist
```

浏览器打开 [本地简介](http://127.0.0.1:8767/#/introduction)。也可双击本目录的“启动本地文档.bat”。局域网设备使用本机实际 IP 访问；`0.0.0.0` 是监听地址。

| 文件 | 用途 |
| --- | --- |
| `dist/index.html`、`dist/styles.css`、`dist/app.js` | 页面结构、主题、导航与交互 |
| `build_content.py` | 页面内容、分类、源码 API 和资源缓存版本 |
| `dist/native-flow.js`、`dist/native-flow.css` | Python → C → Qt 原理动画 |
| `dist/migration.js`、`dist/migration.css` | Qt → FluentPy 输入框过渡 |
| `validate_site.py` | 资源、导航、接口、可执行示例和 GIF 验证 |

修改后重新生成内容并验证；`dist/data.js` 是生成文件，不直接编辑。网页从组件库源码读取版本号，当前版本为 0.7.3。

## 更新真实 Qt 配图

首页和 README 使用当前组件概览截图，开始使用页与其他工作台展示使用新版页面导航截图；亮暗配图同步生成：

```powershell
python sites/fluentpy-docs/capture_workbench_redesign.py
python sites/fluentpy-docs/build_content.py
python sites/fluentpy-docs/validate_site.py
```

该脚本在隐藏的 Qt 窗口中捕获当前工作台各页的明暗主题，检查常规尺寸和最小窗口布局；检查结果及配图在 `build/workbench-redesign/`。实际控件交互来自本库，截图不是网页模拟。

独立组件媒体由同目录的 `capture_previews.py`、`capture_animations.py`、`capture_card_previews.py`、`capture_button_previews.py`、`capture_drop_previews.py`、`capture_shortcut_previews.py`、`capture_progress_toasts.py`、`capture_time_previews.py` 和 `capture_calendar_previews.py` 维护。录制前查看脚本说明；需要本地 Qt 与 Pillow，服务器不需要这些依赖。基础批次可用默认 Python 回退；展示 C 模式时先构建扩展。

## 完整部署包

在仓库根目录运行：

```powershell
python sites/fluentpy-docs/package_deploy.py --output dist/docs/FluentPy-docs-redesign-20261017.zip
```

打包器验证页面和所有引用资源，刷新缓存版本，生成 `dist/`、`部署说明.txt` 和 `SHA256SUMS.txt`。在宝塔解压覆盖到 `/www/wwwroot/fluentpy.mcxmcl.cn/`，站点根目录保持 `/www/wwwroot/fluentpy.mcxmcl.cn/dist`。图片、GIF、图标和许可文件均随包提供。

此包仅用于静态文档，组件库与 C 扩展通过项目自身的安装流程安装。

## 内容与许可

站点布局和文案独立编写，未使用参考站点的源码、文字或图片。控件截图来自 FluentPy。Microsoft Fluent System Icons 的完整许可位于 `dist/assets/icons-LICENSE.txt`，FluentPy 的 MIT 许可位于 `dist/assets/FluentPy-LICENSE.txt`。
