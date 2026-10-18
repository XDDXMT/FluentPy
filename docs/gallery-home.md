# 半透明卡片首页示例

运行源码目录中的 `python examples/gallery_home.py`，或双击 `examples/run_gallery_home.bat`。
默认深色；添加 `--light` 使用浅色。右上角的开关可以在窗口中切换主题。

这个示例也可以单独复制到已安装 `fluentpy-qt==0.6.9` 的项目中运行，不需要额外下载背景素材。
背景曲线由 Qt 独立绘制，图标使用已有的 FluentPy 标志与随库分发的 Microsoft Fluent System Icons。
参考图仅用于横幅、入口卡片与内容层次的构思，没有使用其中的壁纸、标志或实现代码。

四张卡片均可整卡点击，也支持 Tab 聚焦、Enter／空格激活。点击后由系统浏览器打开对应资源。
窗口变窄时自动改为两列或单列，并可垂直滚动。卡片继承已有 `Button` 的悬浮、按下与键盘行为，
背景通过带透明度的颜色叠加，绘制结果按尺寸与屏幕 DPI 缓存；没有持续运行的背景动画或实时模糊。

修改 `examples/gallery_home.py` 顶部的 `LINKS` 即可替换入口名称、说明、图标和地址。
图标为 `None` 时显示 FluentPy 标志；也可以传入现有 `FluentIcon`。
页面标题、介绍和页脚在 `GalleryHero` 中配置，卡片布局在 `ResourceCard` 中配置。
这两个类属于示例代码，不是 `from fluentpy import ...` 的新组件。

截图可以使用 `--screenshot PATH --quit-after-screenshot`；生成的是实际 Qt 窗口画面。
