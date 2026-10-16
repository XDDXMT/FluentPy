"""Constructor visibility includes every QLabel, not only the dialog itself."""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import unittest

from fluentpy import FramelessDialog, MaskedDialog
from fluentpy.qt import QtCore, QtWidgets


class _LabelLifecycleEvents(QtCore.QObject):
    def __init__(self):
        super().__init__()
        self.top_level_shows = []
        self.native_labels = []

    def eventFilter(self, watched, event):
        if isinstance(watched, QtWidgets.QLabel):
            if event.type() == QtCore.QEvent.Type.Show and watched.isWindow():
                self.top_level_shows.append((watched.text(), watched.parentWidget()))
            if event.type() == QtCore.QEvent.Type.WinIdChange and watched.windowHandle() is not None:
                self.native_labels.append(watched.text())
        return False


class DialogChildLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.host = QtWidgets.QWidget()
        self.events = _LabelLifecycleEvents()
        self.app.installEventFilter(self.events)

    def tearDown(self):
        self.app.removeEventFilter(self.events)
        self.host.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)

    def test_constructing_both_dialogs_never_shows_or_creates_a_native_label(self):
        for dialog_type in (FramelessDialog, MaskedDialog):
            for content in ("", "构造时应保持子控件，不能先显示为独立窗口。"):
                with self.subTest(dialog_type=dialog_type.__name__, content=content):
                    dialog = dialog_type("确认", content, self.host)
                    self.assertIs(dialog._title_label.parentWidget(), dialog._panel)
                    self.assertIs(dialog._content_label.parentWidget(), dialog._panel)
                    self.assertFalse(dialog._title_label.isWindow())
                    self.assertFalse(dialog._content_label.isWindow())
                    self.assertIsNone(dialog._title_label.windowHandle())
                    self.assertIsNone(dialog._content_label.windowHandle())
                    self.assertEqual(dialog._content_label.isHidden(), not bool(content))
        self.assertEqual(self.events.top_level_shows, [])
        self.assertEqual(self.events.native_labels, [])


if __name__ == "__main__":
    unittest.main()
