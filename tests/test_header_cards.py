"""Composition, ownership and layout behavior of the titled cards."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
import unittest

from fluentpy import (
    Button,
    GroupHeaderCardWidget,
    HeaderCardWidget,
    LineEdit,
    SimpleCardWidget,
    theme,
)
from fluentpy.qt import QtCore, QtWidgets

if "PySide6" in QtCore.__name__:
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


class _ConstructorWatch(QtCore.QObject):
    def __init__(self):
        super().__init__()
        self.orphans = []

    def eventFilter(self, obj, event):
        if (
            isinstance(obj, QtWidgets.QLabel)
            and event.type() == QtCore.QEvent.Type.Show
            and obj.isWindow()
        ):
            self.orphans.append(obj.text())
        return False


class HeaderCardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.mode = theme.mode
        self.host = QtWidgets.QWidget()
        self.host.resize(900, 700)
        self.layout = QtWidgets.QVBoxLayout(self.host)
        self.errors = []
        self.old_hook = sys.excepthook
        sys.excepthook = lambda _kind, error, _tb: self.errors.append(str(error))

    def tearDown(self):
        self.host.close()
        self.host.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        theme.set_mode(self.mode)
        self.app.processEvents()
        sys.excepthook = self.old_hook
        self.assertEqual(self.errors, [])

    def test_constructor_never_shows_an_orphan_label_or_native_child(self):
        watch = _ConstructorWatch()
        self.app.installEventFilter(watch)
        try:
            header = HeaderCardWidget("系统要求", self.host)
            group = GroupHeaderCardWidget("基本设置", self.host)
            row = group.add_group("i", "入口脚本", "选择需要运行的 Python 文件", LineEdit())
            self.assertIsInstance(header, SimpleCardWidget)
            self.assertIs(header.title_label.parentWidget(), header.header_widget)
            self.assertIs(row.title_label.parentWidget(), row.content_label.parentWidget())
            for label in self.host.findChildren(QtWidgets.QLabel):
                self.assertFalse(label.isWindow())
                self.assertIsNone(label.windowHandle())
            self.assertEqual(watch.orphans, [])
            self.assertFalse(header.isVisible())
            self.assertFalse(group.isVisible())
        finally:
            self.app.removeEventFilter(watch)

    def test_header_content_layout_and_title_changes_keep_existing_widgets(self):
        header = HeaderCardWidget("系统要求", self.host)
        content = QtWidgets.QLabel("这台设备可以运行。")
        header.body_layout.addWidget(content)
        self.assertIs(header.viewLayout, header.body_layout)
        self.assertIs(content.parentWidget(), header.view)
        header.setTitle("更新后的标题")
        self.assertEqual(header.title(), "更新后的标题")
        header.set_title("")
        self.assertEqual(header.title(), "")
        self.assertEqual(header.body_layout.count(), 1)

    def test_parent_only_qt_style_constructor_is_supported(self):
        for kind in (HeaderCardWidget, GroupHeaderCardWidget):
            card = kind(self.host)
            self.assertIs(card.parentWidget(), self.host)
            self.assertEqual(card.title(), "")
            with self.assertRaises(TypeError):
                kind(self.host, self.host)

    def test_header_visibility_controls_divider_and_keeps_body(self):
        header = HeaderCardWidget("标题", self.host)
        header.body_layout.addWidget(QtWidgets.QLabel("正文"))
        header.set_header_visible(False)
        self.assertFalse(header.is_header_visible())
        self.assertTrue(header._header_divider.isHidden())
        self.assertFalse(header.view.isHidden())
        header.set_header_visible(True)
        self.assertTrue(header.is_header_visible())
        self.assertFalse(header._header_divider.isHidden())

    def test_group_add_aliases_and_owned_controls(self):
        group = GroupHeaderCardWidget("设置", self.host)
        first_control = Button("选择")
        first = group.add_group("i", "构建目录", "选择输出位置", first_control)
        second = group.addGroup(None, "终端", "", QtWidgets.QComboBox())
        self.assertEqual(group.groups(), (first, second))
        self.assertIs(group.viewLayout, group.vBoxLayout)
        self.assertIs(group.body_layout, group.vBoxLayout)
        self.assertIs(first_control.parentWidget(), first)
        self.assertEqual(first.title_label.text(), "构建目录")
        self.assertFalse(first.content_label.isHidden())
        self.assertTrue(second.content_label.isHidden())
        self.assertEqual(group.body_layout.count(), 3)

    def test_remove_first_middle_and_last_group_releases_children_and_separators(self):
        group = GroupHeaderCardWidget(parent=self.host)
        rows = [group.add_group(None, str(index), control=Button("操作")) for index in range(3)]
        destroyed = []
        rows[0].control.destroyed.connect(lambda *_: destroyed.append(True))
        self.assertTrue(group.remove_group(rows[0]))
        self.assertIsNone(group._separators[0])
        self.assertEqual(group.body_layout.count(), 3)
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertEqual(destroyed, [True])
        self.assertFalse(group.remove_group(rows[0]))
        self.assertTrue(group.remove_group(rows[2]))
        self.assertEqual(group.body_layout.count(), 1)
        self.assertTrue(group.remove_group(rows[1]))
        self.assertEqual(group.groups(), ())
        self.assertEqual(group.body_layout.count(), 0)

    def test_replacing_control_deletes_old_widget_and_keeps_the_row(self):
        group = GroupHeaderCardWidget(parent=self.host)
        old = Button("旧操作")
        row = group.add_group(None, "操作", control=old)
        destroyed = []
        old.destroyed.connect(lambda *_: destroyed.append(True))
        new = LineEdit()
        group.set_group_control(row, new)
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertEqual(destroyed, [True])
        self.assertIs(row.control, new)
        self.assertIs(new.parentWidget(), row)
        group.set_group_control(row, None)
        self.assertIsNone(row.control)

    def test_invalid_control_does_not_add_partial_group(self):
        group = GroupHeaderCardWidget(parent=self.host)
        with self.assertRaises(TypeError):
            group.add_group(None, "标题", control="not a widget")
        self.assertEqual(group.groups(), ())
        with self.assertRaises(ValueError):
            group.set_group_control(QtWidgets.QWidget(self.host), None)

    def test_control_reflows_below_text_at_narrow_width_without_reparenting(self):
        group = GroupHeaderCardWidget(parent=self.host)
        control = LineEdit()
        control.setFixedWidth(280)
        row = group.add_group("i", "运行方式", "较长说明能够自然换行。" * 3, control)
        self.layout.addWidget(group)
        self.layout.addStretch()
        self.host.show()
        self.app.processEvents()
        self.assertFalse(row._control_below)
        self.host.resize(420, 700)
        self.app.processEvents()
        self.assertTrue(row._control_below)
        self.assertIs(control.parentWidget(), row)
        self.assertGreaterEqual(control.y(), row._text.y() + row._text.height())
        self.host.resize(900, 700)
        self.app.processEvents()
        self.assertFalse(row._control_below)

    def test_internal_button_and_line_edit_keep_their_own_interaction(self):
        group = GroupHeaderCardWidget("设置", self.host)
        button = Button("选择")
        group.add_group(None, "路径", "选择一个目录", button)
        edit = LineEdit()
        group.add_group(None, "名称", control=edit)
        self.layout.addWidget(group)
        self.host.show()
        self.app.processEvents()
        controls = []
        button.clicked.connect(lambda: controls.append(True))
        QTest.mouseClick(button, QtCore.Qt.MouseButton.LeftButton)
        QTest.mouseClick(edit, QtCore.Qt.MouseButton.LeftButton)
        QTest.keyClicks(edit, "demo")
        self.assertEqual(controls, [True])
        self.assertEqual(edit.text(), "demo")
        self.assertFalse(group.hasFocus())
        self.assertFalse(hasattr(group, "clicked"))

    def test_group_text_is_plain_unicode_and_updates_optional_description(self):
        group = GroupHeaderCardWidget(parent=self.host)
        row = group.add_group(None, "<b>项目 😀</b>", "说明")
        self.assertEqual(row.title_label.textFormat(), QtCore.Qt.TextFormat.PlainText)
        group.set_group_text(row, "新标题", "")
        self.assertEqual(row.title_label.text(), "新标题")
        self.assertTrue(row.content_label.isHidden())
        group.set_group_text(row, "新标题", "恢复正文")
        self.assertFalse(row.content_label.isHidden())

    def test_theme_typography_and_callbacks_after_removal(self):
        group = GroupHeaderCardWidget("设置", self.host)
        row = group.add_group("i", "字体", "中文说明", Button("操作"))
        for mode in ("light", "dark"):
            theme.set_mode(mode)
            self.assertIn("Microsoft YaHei UI", group.title_label.font().families())
            self.assertEqual(group.title_label.font().pixelSize(), theme.tokens.font_size + 2)
            self.assertIn(theme.tokens.text_muted, row.content_label.styleSheet())
        group.remove_group(row)
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        theme.toggle()
        self.app.processEvents()
        self.assertEqual(self.errors, [])


if __name__ == "__main__":
    unittest.main()
