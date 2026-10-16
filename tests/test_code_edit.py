import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
import unittest
from unittest.mock import patch

from fluentpy import CodeEdit, theme
from fluentpy.qt import QtCore, QtGui, QtWidgets
from fluentpy.backends.text import native_available


class CodeEditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.previous_mode = theme.mode
        theme.set_mode("light")
        self.view = CodeEdit()
        self.view.resize(600, 240)
        self.view.show()
        self.area = self.view.text_edit
        self.app.processEvents()

    def tearDown(self):
        self.view.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        theme.set_mode(self.previous_mode)
        self.app.processEvents()

    def key(self, key, text="", modifiers=QtCore.Qt.KeyboardModifier.NoModifier):
        event = QtGui.QKeyEvent(QtCore.QEvent.Type.KeyPress, key, modifiers, text)
        self.app.sendEvent(self.area, event)

    def color_at(self, text, needle, occurrence=0):
        block = self.area.document().firstBlock()
        index = text.index(needle, occurrence)
        position = len(text[:index].encode("utf-16-le")) // 2
        for run in block.layout().formats():
            if run.start <= position < run.start + run.length:
                return run.format.foreground().color().name()
        return None

    def test_json_tokens_handle_escaped_quotes_and_unicode_offsets(self):
        source = '{"title": "🎵 true \\"quoted\\"", "ready": false, "gain": -1.5e+2, "value": null}'
        self.view.set_code(source)
        self.view._highlighter.rehighlight()
        self.assertEqual(self.color_at(source, "title"), "#9640ad")
        self.assertEqual(self.color_at(source, "true"), "#00a42f")
        self.assertEqual(self.color_at(source, "quoted"), "#00a42f")
        self.assertEqual(self.color_at(source, "ready"), "#9640ad")
        self.assertEqual(self.color_at(source, "false"), "#003fff")
        self.assertEqual(self.color_at(source, "-1.5e+2"), "#0059ff")
        self.assertEqual(self.color_at(source, "null"), "#003fff")

    def test_edits_rehighlight_and_undo_without_changing_text(self):
        self.view.setPlainText('{"value": 1}')
        seen = []
        self.view.textChanged.connect(lambda: seen.append(self.view.code()))
        cursor = self.area.textCursor()
        cursor.setPosition(10)
        cursor.setPosition(11, QtGui.QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText("false")
        self.app.processEvents()
        self.assertEqual(self.view.toPlainText(), '{"value": false}')
        self.assertEqual(self.color_at(self.view.code(), "false"), "#003fff")
        self.area.undo()
        self.assertEqual(self.view.code(), '{"value": 1}')
        self.assertTrue(seen)

    def test_gutter_grows_and_tracks_scrolled_current_line(self):
        initial_width = self.area.gutter_width()
        self.view.set_code("\n".join(str(i) for i in range(1000)))
        self.assertGreater(self.area.gutter_width(), initial_width)
        cursor = QtGui.QTextCursor(self.area.document().findBlockByNumber(900))
        self.area.setTextCursor(cursor)
        self.area.centerCursor()
        self.app.processEvents()
        self.assertGreater(self.area.firstVisibleBlock().blockNumber(), 0)
        self.assertEqual(self.area.line_numbers.height(), self.area.viewport().height())
        y = self.area.blockBoundingGeometry(cursor.block()).translated(self.area.contentOffset()).center().y()
        gutter = self.area.line_numbers.grab().toImage()
        body = self.area.viewport().grab().toImage()
        self.assertEqual(gutter.pixelColor(2, int(y)).name(), "#f3f6fa")
        self.assertEqual(body.pixelColor(body.width() - 5, int(y)).name(), "#f3f6fa")

    def test_indent_guides_follow_text_during_horizontal_scroll(self):
        self.view.set_code('{\n' + ' ' * 40 + '"value": "' + 'x' * 150 + '"\n}')
        self.area.clearFocus()
        cursor = QtGui.QTextCursor(self.area.document().findBlockByNumber(1))
        cursor.setPosition(cursor.position() + 16)
        for offset in (0, 80):
            self.area.horizontalScrollBar().setValue(offset)
            self.app.processEvents()
            rect = self.area.cursorRect(cursor)
            image = self.area.viewport().grab().toImage()
            x, y = rect.left(), rect.center().y()
            self.assertTrue(any(image.pixelColor(x + dx, y).name() == "#e8eaf0" for dx in (-1, 0, 1)))
        self.assertGreater(self.area.horizontalScrollBar().value(), 0)

    def test_custom_indent_width_controls_editing_and_survives_theme(self):
        self.assertEqual(self.view.indent_size(), 4)
        self.view.set_indent_size(2)
        self.view.set_code("{")
        self.area.moveCursor(QtGui.QTextCursor.MoveOperation.End)
        self.key(QtCore.Qt.Key.Key_Return, "\r")
        self.key(QtCore.Qt.Key.Key_Tab, "\t")
        self.assertEqual(self.view.code(), "{\n    ")
        self.key(QtCore.Qt.Key.Key_Backtab, modifiers=QtCore.Qt.KeyboardModifier.ShiftModifier)
        self.assertEqual(self.view.code(), "{\n  ")
        theme.set_mode("dark")
        self.assertEqual(self.view.indent_size(), 2)
        for invalid in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                self.view.set_indent_size(invalid)
        self.assertEqual(self.view.indent_size(), 2)

    def test_gutter_does_not_add_a_fourth_line_beside_three_indent_guides(self):
        self.view.set_indent_size(2)
        self.view.set_code('{\n      "value": 1\n}')
        self.area.clearFocus()
        self.app.processEvents()
        cursor = QtGui.QTextCursor(self.area.document().findBlockByNumber(1))
        y = self.area.cursorRect(cursor).center().y()
        gutter = self.area.line_numbers.grab().toImage()
        self.assertEqual(gutter.pixelColor(gutter.width() - 1, y).name(), "#ffffff")
        body = self.area.viewport().grab().toImage()
        cursor.setPosition(cursor.position() + 6)
        text_x = self.area.cursorRect(cursor).left()
        guide_columns = [x for x in range(text_x) if body.pixelColor(x, y).name() == "#e8eaf0"]
        self.assertEqual(len(guide_columns), 3)
        gaps = [b - a for a, b in zip(guide_columns, guide_columns[1:])]
        self.assertLessEqual(max(gaps) - min(gaps), 1)

    def test_selection_indent_outdent_and_single_step_undo(self):
        original = "one\ntwo\nthree"
        self.view.set_code(original)
        cursor = self.area.textCursor()
        cursor.setPosition(0)
        cursor.setPosition(8, QtGui.QTextCursor.MoveMode.KeepAnchor)
        self.area.setTextCursor(cursor)
        self.key(QtCore.Qt.Key.Key_Tab, "\t")
        self.assertEqual(self.view.code(), "    one\n    two\nthree")
        self.area.undo()
        self.assertEqual(self.view.code(), original)
        self.area.redo()
        self.area.selectAll()
        self.key(QtCore.Qt.Key.Key_Backtab, modifiers=QtCore.Qt.KeyboardModifier.ShiftModifier)
        self.assertEqual(self.view.code(), original)

    def test_return_autoindent_and_read_only(self):
        self.view.set_code("    {")
        self.area.moveCursor(QtGui.QTextCursor.MoveOperation.End)
        self.key(QtCore.Qt.Key.Key_Return, "\r")
        self.assertEqual(self.view.code(), "    {\n        ")
        self.area.undo()
        self.assertEqual(self.view.code(), "    {")
        self.view.setReadOnly(True)
        self.key(QtCore.Qt.Key.Key_Tab, "\t")
        self.key(QtCore.Qt.Key.Key_Return, "\r")
        self.key(QtCore.Qt.Key.Key_A, "a")
        self.assertTrue(self.view.isReadOnly())
        self.assertEqual(self.view.code(), "    {")

    def test_plain_mode_removes_syntax_without_resetting_document(self):
        source = '{"enabled": true}'
        self.view.set_code(source)
        cursor = self.area.textCursor()
        cursor.setPosition(4)
        self.area.setTextCursor(cursor)
        self.view.set_language("plain")
        self.assertEqual(self.area.document().firstBlock().layout().formats(), [])
        self.assertEqual(self.view.code(), source)
        self.assertEqual(self.area.textCursor().position(), 4)
        with self.assertRaises(ValueError):
            self.view.set_language("unknown")
        self.assertEqual(self.view.language(), "plain")

    def test_theme_switch_preserves_content_and_destroyed_editor_disconnects(self):
        source = '{"title": "FluentPy"}'
        self.view.set_code(source)
        theme.set_mode("dark")
        self.assertEqual(self.view.code(), source)
        self.assertEqual(self.color_at(source, "title"), "#c179b6")
        errors = []
        previous_hook = sys.excepthook
        sys.excepthook = lambda kind, error, traceback: errors.append(error)
        try:
            retired = CodeEdit()
            retired.deleteLater()
            self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
            theme.toggle()
            self.app.processEvents()
            self.assertEqual(errors, [])
        finally:
            sys.excepthook = previous_hook

    @unittest.skipUnless(native_available(), "requires the optional C backend")
    def test_backend_reselection_keeps_text_and_utf16_formats(self):
        source = '{"title": "😀", "enabled": true}'
        with patch.dict(os.environ, {"FLUENTPY_BACKEND": "python"}):
            self.view.set_code(source)
            self.assertEqual(self.view.acceleration_backend(), "python")
        with patch.dict(os.environ, {"FLUENTPY_BACKEND": "native"}):
            self.view._highlighter.rehighlight()
            self.assertEqual(self.view.acceleration_backend(), "native")
            self.assertEqual(self.view.code(), source)
            self.assertEqual(self.color_at(source, "enabled"), "#9640ad")
            self.assertEqual(self.color_at(source, "true"), "#003fff")

    def test_forced_missing_backend_fails_before_qt_callbacks_or_text_mutation(self):
        self.view.set_code('{"before": 1}')
        errors = []
        previous_hook = sys.excepthook
        sys.excepthook = lambda kind, error, traceback: errors.append(error)
        try:
            with patch("fluentpy.backends.text._extension", None), patch.dict(os.environ, {"FLUENTPY_BACKEND": "native"}):
                with self.assertRaises(RuntimeError):
                    CodeEdit()
                with self.assertRaises(RuntimeError):
                    self.view.set_code('{"after": 2}')
            self.assertEqual(self.view.code(), '{"before": 1}')
            self.assertEqual(errors, [])
        finally:
            sys.excepthook = previous_hook


if __name__ == "__main__":
    unittest.main()
