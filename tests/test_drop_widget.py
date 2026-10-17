"""Real Qt drag/drop, browsing, async delivery, theme and destruction checks."""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from fluentpy import DropArea, FileDropWidget, FolderDropWidget, theme
from fluentpy.qt import QtCore, QtGui, QtWidgets
from fluentpy.widgets import drop as widgets
if "PySide6" in QtCore.__name__:
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


class DropWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.mode = theme.mode
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.png = self.root / "一张 图片 😀 %20.PNG"
        self.png.write_bytes(b"not decoded by the drop widget")
        self.gif = self.root / "second.gif"
        self.gif.write_bytes(b"original")
        self.txt = self.root / "notes.txt"
        self.txt.write_text("original", encoding="utf-8")
        self.folder = self.root / "文件夹"
        self.folder.mkdir()
        self.host = QtWidgets.QWidget()
        self.layout = QtWidgets.QVBoxLayout(self.host)
        self.view = FileDropWidget(self.host)
        self.layout.addWidget(self.view)
        self.host.show()
        self.app.processEvents()
        self.errors = []
        self.hook = sys.excepthook
        sys.excepthook = lambda _kind, error, _tb: self.errors.append(str(error))

    def tearDown(self):
        try:
            QtCore.QThreadPool.globalInstance().waitForDone(3000)
            self.app.processEvents()
            self.host.close()
            self.host.deleteLater()
            self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
            theme.set_mode(self.mode)
            self.app.processEvents()
            self.assertEqual(self.errors, [])
        finally:
            sys.excepthook = self.hook
            self.directory.cleanup()

    def canonical(self, path):
        return QtCore.QFileInfo(str(path)).canonicalFilePath()

    def wait_done(self, view=None):
        view = view or self.view
        for _ in range(200):
            if not view.is_busy():
                return
            QTest.qWait(5)
        self.fail("drop validation did not finish")

    def test_defaults_real_labels_and_normal_logical_sizes(self):
        self.assertEqual(self.view.file_extensions(), (".jpg", ".png", ".gif"))
        self.assertEqual(self.view.sizeHint(), QtCore.QSize(300, 144))
        self.assertEqual(FolderDropWidget(self.host).sizeHint(), QtCore.QSize(246, 144))
        self.assertIn("JPG、PNG、GIF", self.view.text())
        self.assertTrue(self.view.browse_files_button.isVisible())
        self.assertTrue(self.view.browse_folder_button.isVisible())
        for label in self.view.findChildren(QtWidgets.QLabel):
            self.assertIsNotNone(label.parentWidget())
            self.assertIsNone(label.windowHandle())
        self.assertEqual(self.view.font().weight(), QtGui.QFont.Weight.Normal)

    def test_file_folder_signals_canonical_paths_and_copy_only_data(self):
        selected, files, folders, rejected = [], [], [], []
        self.view.pathsSelected.connect(selected.append)
        self.view.filesSelected.connect(files.append)
        self.view.folderSelected.connect(folders.append)
        self.view.pathsRejected.connect(rejected.append)
        actual = self.view.accept_paths([self.png, self.folder, self.txt, self.png])
        expected = [self.canonical(self.png), self.canonical(self.folder)]
        self.assertEqual(actual, expected)
        self.assertEqual(selected, [expected])
        self.assertEqual(files, [[expected[0]]])
        self.assertEqual(folders, [expected[1]])
        self.assertEqual([r for _path, r in rejected[0]], ["extension", "duplicate"])
        self.assertEqual(self.png.read_bytes(), b"not decoded by the drop widget")
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_folder_only_rejects_file_and_excess_folder(self):
        view = FolderDropWidget(self.host)
        self.layout.addWidget(view)
        second = self.root / "second"
        second.mkdir()
        rejections = []
        view.pathsRejected.connect(rejections.append)
        self.assertEqual(view.accept_paths([self.png, self.folder, second]), [self.canonical(self.folder)])
        self.assertEqual([r for _p, r in rejections[0]], ["type", "multiple"])
        self.assertTrue(view.browse_files_button.isHidden())
        self.assertTrue(view.separator_label.isHidden())

    def test_invalid_selection_preserves_previous_and_clear_emits_once(self):
        changes = []
        self.view.selectionChanged.connect(changes.append)
        self.view.accept_paths([self.png])
        self.view.accept_paths([self.txt, self.root / "missing.png"])
        self.assertEqual(self.view.selected_paths(), [self.canonical(self.png)])
        copy = self.view.selected_paths()
        copy.clear()
        self.assertEqual(len(self.view.selected_paths()), 1)
        self.view.clear()
        self.view.clear()
        self.assertEqual(changes, [[self.canonical(self.png)], []])

    def test_suffix_change_custom_text_and_single_selection(self):
        self.view.setFileExtensions([".txt"])
        self.view.set_multiple(False)
        self.assertFalse(self.view.is_multiple())
        self.assertEqual(self.view.fileExtensions(), (".txt",))
        self.assertIn("TXT", self.view.text())
        self.assertEqual(self.view.accept_paths([self.png, self.txt]), [self.canonical(self.txt)])
        self.view.setText("放下你的素材")
        self.assertEqual(self.view.text(), "放下你的素材")
        self.view.set_text(None)
        self.assertIn("TXT", self.view.text())
        with self.assertRaises(TypeError):
            self.view.accept_paths(str(self.png))

    def test_native_dialog_actions_and_cancel_preserve_selection(self):
        with patch.object(QtWidgets.QFileDialog, "getOpenFileNames", return_value=([str(self.png)], "")) as dialog:
            QTest.mouseClick(self.view.browse_files_button, QtCore.Qt.MouseButton.LeftButton)
            self.wait_done()
            self.assertIn("*.png", dialog.call_args.args[3])
        with patch.object(QtWidgets.QFileDialog, "getExistingDirectory", return_value=""):
            self.view.browse_folder()
        self.assertEqual(self.view.selected_paths(), [self.canonical(self.png)])
        with patch.object(QtWidgets.QFileDialog, "getExistingDirectory", return_value=str(self.folder)):
            self.view.browse_folder()
            self.wait_done()
        self.assertEqual(self.view.selected_paths(), [self.canonical(self.folder)])
        self.view.set_multiple(False)
        with patch.object(QtWidgets.QFileDialog, "getOpenFileName", return_value=(str(self.gif), "")) as dialog:
            self.view.setFocus()
            QTest.keyClick(self.view, QtCore.Qt.Key.Key_Space)
            self.wait_done()
            self.assertEqual(dialog.call_count, 1)

    def test_real_drag_drop_decodes_local_urls_and_forces_copy(self):
        mime = QtCore.QMimeData()
        mime.setUrls([QtCore.QUrl.fromLocalFile(str(self.png)), QtCore.QUrl.fromLocalFile(str(self.txt))])
        actions = QtCore.Qt.DropAction.CopyAction | QtCore.Qt.DropAction.MoveAction
        enter = QtGui.QDragEnterEvent(QtCore.QPoint(10, 10), actions, mime, QtCore.Qt.MouseButton.LeftButton, QtCore.Qt.KeyboardModifier.NoModifier)
        self.app.sendEvent(self.view, enter)
        self.assertTrue(enter.isAccepted())
        self.assertEqual(enter.dropAction(), QtCore.Qt.DropAction.CopyAction)
        self.assertTrue(self.view._drag_active)
        drop = QtGui.QDropEvent(QtCore.QPointF(10, 10), actions, mime, QtCore.Qt.MouseButton.LeftButton, QtCore.Qt.KeyboardModifier.NoModifier)
        self.app.sendEvent(self.view, drop)
        self.assertTrue(drop.isAccepted())
        self.assertEqual(drop.dropAction(), QtCore.Qt.DropAction.CopyAction)
        self.wait_done()
        self.assertEqual(self.view.selected_paths(), [self.canonical(self.png)])
        self.assertTrue(self.png.exists())

    def test_remote_text_and_move_only_drags_are_ignored(self):
        for url, action in (("https://example.com/pic.png", QtCore.Qt.DropAction.CopyAction),
                            (QtCore.QUrl.fromLocalFile(str(self.png)).toString(), QtCore.Qt.DropAction.MoveAction)):
            mime = QtCore.QMimeData()
            mime.setUrls([QtCore.QUrl(url)])
            event = QtGui.QDragEnterEvent(QtCore.QPoint(5, 5), action, mime, QtCore.Qt.MouseButton.LeftButton, QtCore.Qt.KeyboardModifier.NoModifier)
            self.app.sendEvent(self.view, event)
            self.assertFalse(event.isAccepted())
        mime = QtCore.QMimeData()
        mime.setText(str(self.png))
        event = QtGui.QDragEnterEvent(QtCore.QPoint(5, 5), QtCore.Qt.DropAction.CopyAction, mime, QtCore.Qt.MouseButton.LeftButton, QtCore.Qt.KeyboardModifier.NoModifier)
        self.app.sendEvent(self.view, event)
        self.assertFalse(event.isAccepted())

    def test_async_result_on_gui_thread_and_resets_busy(self):
        threads, busy = [], []
        self.view.pathsSelected.connect(lambda _paths: threads.append(QtCore.QThread.currentThread()))
        self.view.busyChanged.connect(busy.append)
        self.view.submit_paths([self.png, self.gif])
        self.assertTrue(self.view.is_busy())
        self.assertFalse(self.view.browse_files_button.isEnabled())
        self.wait_done()
        self.assertEqual(threads, [self.app.thread()])
        self.assertEqual(busy, [True, False])
        self.assertTrue(self.view.browse_files_button.isEnabled())

    def test_stale_worker_result_cannot_restore_cleared_selection(self):
        gate = threading.Event()
        original = widgets._candidates
        def slow(paths):
            gate.wait(1)
            return original(paths)
        with patch.object(widgets, "_candidates", side_effect=slow):
            self.view.submit_paths([self.png])
            self.view.clear()
            gate.set()
            QtCore.QThreadPool.globalInstance().waitForDone(3000)
            self.app.processEvents()
        self.assertEqual(self.view.selected_paths(), [])
        self.assertFalse(self.view.is_busy())

    def test_newer_request_wins_even_if_older_request_finishes_last(self):
        gate = threading.Event()
        original = widgets._candidates
        def ordered(paths):
            if str(self.png) in paths:
                gate.wait(2)
            return original(paths)
        selected = []
        self.view.pathsSelected.connect(selected.append)
        try:
            with patch.object(widgets, "_candidates", side_effect=ordered):
                self.view.submit_paths([self.png])
                self.view.submit_paths([self.gif])
                self.wait_done()
                self.assertEqual(self.view.selected_paths(), [self.canonical(self.gif)])
                gate.set()
                QtCore.QThreadPool.globalInstance().waitForDone(3000)
                self.app.processEvents()
            self.assertEqual(selected, [[self.canonical(self.gif)]])
        finally:
            gate.set()

    def test_background_error_preserves_selection_and_clears_busy(self):
        self.view.accept_paths([self.png])
        errors = []
        self.view.errorOccurred.connect(errors.append)
        with patch.object(widgets, "_candidates", side_effect=RuntimeError("metadata unavailable")):
            self.view.submit_paths([self.gif])
            self.wait_done()
        self.assertEqual(errors, ["metadata unavailable"])
        self.assertFalse(self.view.is_busy())
        self.assertEqual(self.view.selected_paths(), [self.canonical(self.png)])

    def test_missing_native_backend_fails_before_allocating_child_widgets(self):
        before = self.host.findChildren(QtWidgets.QWidget)
        with patch.object(widgets.selection, "_extension", None), patch.dict(os.environ, {"FLUENTPY_BACKEND": "native"}):
            with self.assertRaisesRegex(RuntimeError, "compiled.*drop backend"):
                FileDropWidget(self.host)
        self.assertEqual(self.host.findChildren(QtWidgets.QWidget), before)

    def test_disable_hide_and_destroy_during_worker_are_safe(self):
        self.view._set_drag_active(True)
        self.view._animation.setCurrentTime(80)
        self.assertGreater(self.view._drag_progress, 0)
        self.view.setEnabled(False)
        self.assertEqual(self.view._drag_progress, 0)
        self.assertFalse(self.view.acceptDrops())
        with patch.object(QtWidgets.QFileDialog, "getOpenFileNames") as dialog:
            self.view.browse_files()
            self.assertFalse(dialog.called)
        self.view.setEnabled(True)
        self.assertTrue(self.view.acceptDrops())
        self.view.submit_paths([self.png])
        self.view.hide()
        self.assertFalse(self.view.is_busy())
        self.view.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        QtCore.QThreadPool.globalInstance().waitForDone(3000)
        self.app.processEvents()
        theme.toggle()
        self.app.processEvents()

    def test_light_dark_paint_animation_and_layout_stay_fixed(self):
        geometry = QtCore.QRect(self.view.geometry())
        for mode in ("light", "dark"):
            theme.set_mode(mode)
            self.view._set_drag_active(True)
            self.view._animation.setCurrentTime(75)
            self.assertGreater(self.view._drag_progress, 0)
            self.assertLess(self.view._drag_progress, 1)
            self.assertFalse(self.view.grab().isNull())
            self.assertEqual(self.view.geometry(), geometry)
            leave = QtGui.QDragLeaveEvent()
            self.app.sendEvent(self.view, leave)
            self.assertFalse(self.view._drag_active)
