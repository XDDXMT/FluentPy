"""Dialogs must open once at their destination, without hidden warm-up shows."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import unittest

from fluentpy import FramelessDialog
from fluentpy.qt import QtCore, QtWidgets


class _DialogEvents(QtCore.QObject):
    def __init__(self):
        super().__init__()
        self.events = []

    def eventFilter(self, watched, event):
        if isinstance(watched, FramelessDialog) and event.type() in (
            QtCore.QEvent.Type.Show,
            QtCore.QEvent.Type.Hide,
            QtCore.QEvent.Type.Move,
        ):
            self.events.append((watched, event.type(), watched.pos(), watched.windowOpacity()))
        return False


class DialogDisplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.parent = QtWidgets.QWidget()
        self.parent.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        self.parent.setGeometry(110, 90, 800, 600)
        self.parent.show()
        self.app.processEvents()
        self.observer = _DialogEvents()
        self.app.installEventFilter(self.observer)

    def tearDown(self):
        self.app.removeEventFilter(self.observer)
        self.parent.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)

    def test_construction_does_not_show_or_pump_unrelated_events(self):
        ticks = []
        QtCore.QTimer.singleShot(0, lambda: ticks.append(True))
        dialog = FramelessDialog("保存", "现在还不应显示。", self.parent)
        self.assertFalse(dialog.isVisible())
        self.assertEqual(ticks, [])
        self.assertFalse(
            any(
                event[1] in (QtCore.QEvent.Type.Show, QtCore.QEvent.Type.Hide)
                for event in self.observer.events
            )
        )
        self.app.processEvents()
        self.assertEqual(ticks, [True])

    def test_open_is_opaque_and_at_final_position_on_first_show(self):
        dialog = FramelessDialog("保存", "直接在最终位置显示。", self.parent)
        dialog.open()
        self.app.processEvents()
        shows = [
            event
            for event in self.observer.events
            if event[0] is dialog and event[1] == QtCore.QEvent.Type.Show
        ]
        self.assertEqual(len(shows), 1)
        self.assertEqual(shows[0][2], dialog.pos())
        self.assertEqual(shows[0][3], 1.0)
        self.assertTrue(dialog.windowFlags() & QtCore.Qt.WindowType.NoDropShadowWindowHint)
        expected = self.parent.frameGeometry().center() - QtCore.QPoint(
            dialog.width() // 2, dialog.height() // 2
        )
        screen = self.app.primaryScreen().availableGeometry()
        expected.setX(max(screen.left(), min(expected.x(), screen.right() - dialog.width() + 1)))
        expected.setY(max(screen.top(), min(expected.y(), screen.bottom() - dialog.height() + 1)))
        self.assertEqual(dialog.pos(), expected)
        before = dialog.pos()
        wait = QtCore.QEventLoop()
        QtCore.QTimer.singleShot(85, wait.quit)
        wait.exec()
        self.assertEqual(dialog.pos(), before)
        self.assertEqual(dialog.windowOpacity(), 1.0)
        self.assertEqual(
            len(
                [
                    event
                    for event in self.observer.events
                    if event[0] is dialog and event[1] == QtCore.QEvent.Type.Show
                ]
            ),
            1,
        )
        dialog.reject()

    def test_repeated_open_and_cancel_only_show_the_requested_dialog(self):
        dialog = FramelessDialog("保存", parent=self.parent)
        accepted, rejected = [], []
        dialog.accepted.connect(lambda: accepted.append(True))
        dialog.rejected.connect(lambda: rejected.append(True))
        for _ in range(3):
            dialog.open()
            self.app.processEvents()
            self.assertTrue(dialog.isVisible())
            dialog.open()  # Asking again must not hide, teleport or reset opacity.
            dialog.reject()
        shows = [event for event in self.observer.events if event[1] == QtCore.QEvent.Type.Show]
        hides = [event for event in self.observer.events if event[1] == QtCore.QEvent.Type.Hide]
        self.assertEqual(len(shows), 3)
        self.assertEqual(len(hides), 3)
        self.assertEqual(accepted, [])
        self.assertEqual(rejected, [True, True, True])

    def test_exec_returns_the_accepted_result_without_a_reveal_timer(self):
        dialog = FramelessDialog("保存", parent=self.parent)
        observed = []

        def confirm():
            observed.append((dialog.isVisible(), dialog.windowOpacity()))
            dialog.accept()

        QtCore.QTimer.singleShot(0, confirm)
        self.assertEqual(dialog.exec(), QtWidgets.QDialog.DialogCode.Accepted)
        self.assertEqual(observed, [(True, 1.0)])


if __name__ == "__main__":
    unittest.main()
