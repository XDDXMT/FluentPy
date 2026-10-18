"""Record the real three-region sidebar without displaying desktop windows."""
from pathlib import Path
import sys

SITE = Path(__file__).resolve().parent
from source_project import source_root
ROOT = source_root()
sys.path[:0] = [str(ROOT / "src"), str(SITE)]
from capture_animations import _image, _capture_font
from PIL import Image, ImageChops, ImageStat
from fluentpy import NavigationSidebar, SearchLineEdit, FluentIcon, fluent_icon, theme, QT_API
from fluentpy.qt import QtCore, QtWidgets
if QT_API == "PySide6":
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest

app = QtWidgets.QApplication([])
app.setQuitOnLastWindowClosed(False)
app.setFont(_capture_font())
output = SITE / "dist/assets/previews"
output.mkdir(parents=True, exist_ok=True)
errors = []
sys.excepthook = lambda _kind, error, _tb: errors.append(str(error))
for mode in ("light", "dark"):
    theme.set_mode(mode)
    theme.set_accent(None)
    host = QtWidgets.QWidget()
    host.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    host.setObjectName("sidebarCanvas")
    host.setStyleSheet(f"QWidget#sidebarCanvas {{ background: {theme.tokens.background}; }}")
    host.setFixedSize(240, 560)
    layout = QtWidgets.QHBoxLayout(host)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(0)
    sidebar = NavigationSidebar(host)
    sidebar.set_expanded_width(216)
    sidebar.set_expanded(True)
    layout.addWidget(sidebar)
    layout.addStretch()
    search = SearchLineEdit("搜索导航")
    sidebar.set_header_widget(search)
    search.textChanged.connect(sidebar.set_filter_text)
    home = sidebar.add_header_item(fluent_icon(FluentIcon.HOME), "组件概览")
    names = ["按钮与菜单", "文本与选择", "日期与时间", "日历选择", "文件拖放", "快捷键", "卡片容器", "页面导航", "消息与对话框", "代码编辑器", "音符时间轴", "日期区间"]
    for title in names:
        sidebar.add_item(fluent_icon(FluentIcon.APPS), title)
    settings = sidebar.add_footer_item(fluent_icon(FluentIcon.SETTINGS), "设置")
    host.show()
    QTest.qWait(150)
    if app.focusWidget():
        app.focusWidget().clearFocus()
    QTest.qWait(150)
    assert host.grab().save(str(output / f"sidebar-regions-{mode}.png"))
    bar = sidebar.scroll_area.verticalScrollBar()
    scroll = QtCore.QPropertyAnimation(bar, b"value", sidebar)
    scroll.setEasingCurve(QtCore.QEasingCurve.Type.InOutCubic)
    def move_scroll(target):
        scroll.stop()
        scroll.setStartValue(bar.value())
        scroll.setEndValue(target)
        scroll.setDuration(450)
        scroll.start()
    actions = [
        (400, lambda: move_scroll(bar.maximum())),
        (1300, lambda: settings.clicked.emit(True)),
        (2200, lambda: search.setText("日期")),
        (2950, search.clear),
        (3400, sidebar.toggle),
        (3850, sidebar.toggle),
        (4300, lambda: home.clicked.emit(True)),
        (4310, lambda: move_scroll(0)),
    ]
    frames, times = [], []
    clock = QtCore.QElapsedTimer()
    clock.start()
    next_action = 0
    while clock.elapsed() < 5200:
        elapsed = clock.elapsed()
        while next_action < len(actions) and elapsed >= actions[next_action][0]:
            actions[next_action][1]()
            next_action += 1
        app.processEvents()
        frames.append(_image(host))
        times.append(clock.elapsed())
        QTest.qWait(25)
    palette = frames[0].quantize(colors=256)
    encoded = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    boundaries = [round(value / 10) * 10 for value in times] + [max(5200, round(times[-1] / 10) * 10 + 30)]
    durations = [max(10, end - start) for start, end in zip(boundaries, boundaries[1:])]
    target = output / f"sidebar-regions-{mode}.gif"
    encoded[0].save(target, save_all=True, append_images=encoded[1:], duration=durations, loop=0, disposal=2, optimize=True)
    with Image.open(target) as gif:
        first = gif.convert("RGB")
        for index in range(gif.n_frames):
            gif.seek(index)
            if mode == "light":
                assert min(ImageStat.Stat(gif.convert("RGB")).mean) > 180, "Dark capture artifact"
        assert ImageChops.difference(first, gif.convert("RGB")).getbbox() is None, "Animation must loop to its initial layout"
        print(f"{target.name}: {gif.n_frames} frames, {target.stat().st_size} bytes, {gif.size}")
    host.close()
    host.deleteLater()
    app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
assert not errors, errors
print("Native Qt captures: no callback errors or visible desktop windows")
