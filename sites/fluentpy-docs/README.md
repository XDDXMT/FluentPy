# FluentPy 中文文档站

静态文档站，使用当前本地 FluentPy 源码生成接口签名，组件展示区使用库本身的 Qt 亮色截图与 GIF 动画。提供分类导航、全文接口搜索、代码复制、图标搜索和移动端导航。网站默认跟随系统主题，右上角可在跟随系统、浅色、深色之间切换；图片与动画始终为亮色。

源码位置：`dist/index.html`、`dist/styles.css`、`dist/app.js`。简介原理动画由 `dist/native-flow.js` 与 `dist/native-flow.css` 实现。内容与接口由 `build_content.py` 生成，控件截图由 `capture_previews.py` 生成。生成脚本默认读取此目录上两级的 FluentPy 源码，独立检出时可调整脚本中的 `ROOT`。

消息提示新增两种实际 Qt 动画：紧凑单行侧滑淡入，以及带箭头的双行卡片。`python capture_animations.py` 会生成亮色 GIF 与静态预览；网页可暂停／播放，系统开启减少动画时默认显示静态预览。动图保留自然尺寸，不额外放大控件。

卡片组件页 `#/cards` 展示普通、简洁、悬浮、标题与分组设置五类卡片。`python capture_card_previews.py` 复现其亮色截图及悬浮动画 GIF；演示使用 Unicode 表情与微软官方 Fluent SVG 图标。

卡片示例使用桌面逻辑尺寸：应用行72、标题14px／说明12px、标准80×32按钮，表情卡片128×128。表情动图画布440×168，网站媒体保留自然尺寸；实际窗口随系统DPI缩放，不以参考截图物理像素设置控件大小。

动画录制需要当前 Qt 后端与 Pillow；如未安装，可运行 `python -m pip install Pillow`。站点本身只加载生成后的本地图片，无需这些运行环境。

简介首屏先展示新版工作台的亮色静态截图，让读者看到实际界面；后面的 C 加速说明使用网页原生 JS/SVG 动画，解释 Python 调用、C 后端运算、Qt 呈现三个环节。可切换 JSON 高亮与日期计算，暂停／恢复或重新演示；动画配色跟随网页主题，减少动画时默认静止，离屏或标签页隐藏时自动暂停。动画是原理示意，实测数字另标注来源，不作为实时测速结果。

运行 `python capture_showcase.py --static-only` 可在正常1120×780逻辑尺寸下重新捕获“开始使用”页的亮色工作台PNG。`capture_previews.py` 的工作台截图也来自当前示例，并等待初始侧栏动画结束；“开始使用”展示新的卡片页、统一主图标和紧凑尺寸。`capture_introduction.py` 保留独立的组件组合与代码缩略图捕获，之后运行 `python build_content.py` 更新页面、JS/CSS和媒体缓存版本。

日期选择器和新的示例工作台已加入文档。`capture_previews.py` 会一并生成它们的亮色截图；日期截图来自实际弹出的三列滚轮。运行截图与示例检查前，需先编译包含日期接口的 C 扩展。

“性能与 C 后端”记录同一份完整 JSON 的实测结果。性能 Demo 配图来自 `python examples/text_performance.py --screenshot <绝对输出路径> --quit-after-screenshot` 的实际报告界面，不参与普通控件截图批次生成。

简介新增 Python / C / Qt 职责图和实测摘要，代码编辑器页面也提供 C 后端入口。性能页包含当前接入范围、后续后端运算使用 C 的开发约定、编译方式、模式选择、回退诊断及完整性能表；`native` 代表 C 已启用，`python` 代表兼容实现。

```powershell
python capture_previews.py
python capture_showcase.py --static-only
python capture_animations.py
python build_content.py
python validate_site.py
python -m http.server 8767 --bind 0.0.0.0 --directory dist
```

在浏览器打开 `http://127.0.0.1:8767/#/introduction`。站点无需构建工具或在线字体。

服务监听 `0.0.0.0:8767`。同一局域网内的其他设备可使用 `http://本机局域网IP:8767/#/introduction` 访问；`0.0.0.0` 是监听地址，浏览器访问时使用实际 IP。

日常使用也可以双击本目录的 `启动本地文档.bat`，然后打开上面的本地地址。保持启动窗口运行，关闭窗口即可停止服务。文档现在按本地方式运行与更新，无需登录 ChatGPT。

本站文案和布局为 FluentPy 独立编写，未使用参考站点的源码、文字或图片。截图来自 FluentPy 自身控件。图标来自 Microsoft Fluent System Icons，完整许可随 `dist/assets/icons-LICENSE.txt` 提供。

文档与组件源码一同维护，包含 CodeEdit、日期选择器、五类卡片与新版示例工作台。组件库版本号保持 0.1.0。
