"""Task feedback, interruption, timing and lifetime checks."""

import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from pathlib import Path
import sys
import unittest

from fluentpy import ProgressToast, Toast, theme
from fluentpy.qt import QT_API, QtCore, QtGui, QtWidgets, Signal

if QT_API == "PySide6":
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


class _Worker(QtCore.QThread):
    progress = Signal(float)

    def run(self):
        self.progress.emit(63.0)


class ProgressToastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.errors = []
        self.old_hook = sys.excepthook
        sys.excepthook = lambda _kind, error, _tb: self.errors.append(error)
        self.old_theme = theme.mode
        self.parent = QtWidgets.QWidget()
        self.parent.resize(900, 600)
        self.parent.show()
        self.app.processEvents()

    def tearDown(self):
        if self.parent is not None:
            self.parent.close()
            self.parent.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        theme.set_mode(self.old_theme)
        self.app.processEvents()
        sys.excepthook = self.old_hook
        self.assertEqual(self.errors, [])

    def settle(self, toast):
        toast._reveal.setCurrentTime(toast.SHOW_DURATION)
        self.app.processEvents()

    def settle_state(self, toast):
        for animation in (toast._progress_motion, toast._width_motion, toast._state_motion):
            if animation.state() == QtCore.QAbstractAnimation.State.Running:
                animation.setCurrentTime(animation.duration())
        self.app.processEvents()

    def test_four_corners_animate_as_children_without_transient_windows(self):
        class Monitor(QtCore.QObject):
            def eventFilter(self, obj, event):
                if event.type() == QtCore.QEvent.Type.Show and isinstance(obj, QtWidgets.QLabel) and obj.isWindow():
                    orphan_labels.append(obj.text())
                return False
        orphan_labels = []
        monitor = Monitor()
        self.app.installEventFilter(monitor)
        try:
            for placement in Toast.PLACEMENTS:
                with self.subTest(placement=placement):
                    toast = ProgressToast("正在下载文件，请稍候…", parent=self.parent)
                    self.assertFalse(toast.isVisible())
                    toast.show_at(placement)
                    self.assertFalse(toast.isWindow())
                    self.assertIsNone(toast.windowHandle())
                    self.assertEqual(toast._opacity.opacity(), 0)
                    toast._reveal.setCurrentTime(100)
                    self.assertGreater(toast._opacity.opacity(), 0)
                    self.assertLess(toast._opacity.opacity(), 1)
                    self.assertNotEqual(toast.pos(), toast._rest_pos)
                    self.assertTrue(self.parent.rect().contains(toast.geometry()))
                    self.settle(toast)
                    if placement.endswith("center"):
                        self.assertLessEqual(abs(toast.x()*2+toast.width()-self.parent.width()),1)
                    else:
                        edge = toast.x() if placement.endswith("left") else toast.geometry().right() + 1
                        self.assertEqual(edge, 18 if placement.endswith("left") else self.parent.width()-18)
                    self.assertEqual(toast.y() if placement.startswith("top") else toast.geometry().bottom()+1,
                                     18 if placement.startswith("top") else self.parent.height()-18)
                    toast.hide()
            self.assertEqual(orphan_labels, [])
        finally:
            self.app.removeEventFilter(monitor)

    def test_progress_retargets_from_current_display_and_rejects_nonfinite_values(self):
        toast = ProgressToast("处理中", parent=self.parent)
        toast.show_at()
        self.settle(toast)
        changes = []
        toast.progressChanged.connect(changes.append)
        toast.set_progress(80)
        self.assertEqual(toast.value(), 80)
        self.assertEqual(toast._display_value, 0)
        toast._progress_motion.setCurrentTime(80)
        previous = toast._display_value
        self.assertGreater(previous, 0)
        self.assertLess(previous, .8)
        toast.set_progress(90)
        self.assertAlmostEqual(toast._display_value, previous)
        toast._progress_motion.setCurrentTime(220)
        self.assertAlmostEqual(toast._display_value, .9)
        toast.set_progress(140)
        toast.set_progress(-1)
        self.assertEqual(changes, [80, 90, 100, 0])
        for invalid in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(ValueError):
                toast.set_progress(invalid)

    def test_indeterminate_animation_changes_real_pixels_and_stops_after_completion(self):
        toast = ProgressToast("正在准备…", parent=self.parent, indeterminate=True)
        toast.show_at()
        self.settle(toast)
        toast._activity.setCurrentTime(150)
        first = toast.grab().toImage()
        toast._activity.setCurrentTime(650)
        second = toast.grab().toImage()
        self.assertNotEqual(first, second)
        self.assertTrue(toast.is_indeterminate())
        toast.finish("完成", timeout_ms=0)
        self.settle_state(toast)
        self.assertFalse(toast.is_indeterminate())
        self.assertEqual(toast.value(), 100)
        self.assertEqual(toast._activity.state(), QtCore.QAbstractAnimation.State.Stopped)
        self.assertEqual(toast._icon.accessibleName(), "已完成")

    def test_indeterminate_track_always_has_one_solid_segment_at_different_sizes(self):
        toast = ProgressToast("正在准备文件…", parent=self.parent, indeterminate=True)
        toast.show_at()
        self.settle(toast)
        toast._activity.stop()
        for mode in ("light", "dark"):
            theme.set_mode(mode)
            accent = QtGui.QColor(theme.tokens.accent)
            for width in (180, 220, 360, 620):
                with self.subTest(mode=mode, width=width):
                    toast.resize(width, 80)
                    positions = []
                    for step in range(65):
                        toast._set_phase(step / 64)
                        image = toast.grab().toImage()
                        ratio = image.devicePixelRatio()
                        track = toast._card_rect()
                        row = round((track.bottom() - 1.5) * ratio)
                        columns = []
                        for x in range(round(track.left() * ratio), round(track.right() * ratio)):
                            color = image.pixelColor(x, row)
                            columns.append(max(abs(color.red() - accent.red()), abs(color.green() - accent.green()),
                                               abs(color.blue() - accent.blue())) <= 20)
                        starts = [i for i, on in enumerate(columns) if on and (i == 0 or not columns[i-1])]
                        self.assertEqual(len(starts), 1, f"{mode=} {width=} phase={step}/64: {starts}")
                        solid_width = sum(columns)
                        self.assertGreater(solid_width, len(columns) * .24)
                        self.assertLess(solid_width, len(columns) * .36)
                        positions.append(starts[0])
                    self.assertEqual(positions[0], positions[-1])
                    self.assertGreater(positions[32], positions[0])

    def test_completion_morph_preserves_corner_anchor_and_notifies_once(self):
        for placement in Toast.PLACEMENTS:
            with self.subTest(placement=placement):
                toast = ProgressToast("正在下载一个较长名称的文件，请稍候…", parent=self.parent)
                toast.show_at(placement)
                self.settle(toast)
                completed, states = [], []
                toast.finished.connect(completed.append)
                toast.stateChanged.connect(states.append)
                toast.set_progress(60)
                self.settle_state(toast)
                before = toast.width()
                toast.finish("下载完成", timeout_ms=0)
                toast._width_motion.setCurrentTime(120)
                toast._state_motion.setCurrentTime(100)
                self.assertLess(toast.width(), before)
                self.assertGreater(toast.width(), 220)
                self.assertGreater(toast._icon.mix, 0)
                self.assertLess(toast._icon.mix, 1)
                if placement.endswith("center"):
                    self.assertLessEqual(abs(toast.x()*2+toast.width()-self.parent.width()),1)
                else:
                    self.assertEqual(toast.x() if placement.endswith("left") else toast.x()+toast.width(),
                                     18 if placement.endswith("left") else self.parent.width()-18)
                self.settle_state(toast)
                self.assertEqual(toast.width(), 220)
                toast.set_progress(10)
                toast.fail("晚到的失败")
                toast.finish("重复完成")
                self.assertEqual(toast.state(), "success")
                self.assertEqual(toast.value(), 100)
                self.assertEqual(completed, [True])
                self.assertEqual(states, ["success"])
                toast.hide()

    def test_failure_stays_visible_and_preserves_last_progress(self):
        toast = ProgressToast.start("下载中", parent=self.parent)
        self.settle(toast)
        toast.set_progress(37)
        self.settle_state(toast)
        results = []
        toast.finished.connect(results.append)
        toast.fail("连接中断，请重试")
        self.settle_state(toast)
        self.assertEqual(results, [False])
        self.assertEqual(toast.state(), "error")
        self.assertEqual(toast.value(), 37)
        self.assertAlmostEqual(toast._display_value, .37)
        self.assertFalse(toast._timeout.isActive())
        self.assertIsNone(toast._pending_timeout)
        self.assertTrue(toast.isVisible())

    def test_timeout_starts_after_entry_and_pauses_when_hovered(self):
        toast = ProgressToast.start("下载中", parent=self.parent)
        toast.finish("下载完成", timeout_ms=100)
        self.assertFalse(toast._timeout.isActive())
        self.assertEqual(toast._pending_timeout, 100)
        self.settle(toast)
        self.assertTrue(toast._timeout.isActive())
        enter = QtGui.QEnterEvent(QtCore.QPointF(1, 1), QtCore.QPointF(1, 1), QtCore.QPointF(1, 1))
        self.app.sendEvent(toast, enter)
        self.assertFalse(toast._timeout.isActive())
        QTest.qWait(130)
        self.assertTrue(toast.isVisible())
        self.app.sendEvent(toast, QtCore.QEvent(QtCore.QEvent.Type.Leave))
        self.assertTrue(toast._timeout.isActive())
        destroyed = []
        toast.destroyed.connect(lambda: destroyed.append(True))
        QTest.qWait(100 + ProgressToast.HIDE_DURATION + 60)
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertEqual(destroyed, [True])

    def test_factory_success_is_terminal_and_zero_timeout_is_persistent(self):
        toast = ProgressToast.success("已完成", parent=self.parent, timeout_ms=0)
        self.settle(toast)
        self.settle_state(toast)
        self.assertEqual(toast.state(), "success")
        self.assertEqual(toast.value(), 100)
        self.assertEqual(toast._display_value, 1)
        self.assertFalse(toast._timeout.isActive())

    def test_parent_resize_and_theme_keep_running_toast_inside_window(self):
        toast = ProgressToast("很长的任务名称" * 20, parent=self.parent)
        toast.show_at("bottom-right")
        self.settle(toast)
        for size in ((420, 240), (140, 90), (900, 600)):
            self.parent.resize(*size)
            self.app.processEvents()
            self.assertTrue(self.parent.rect().contains(toast.geometry()))
            for mode in ("light", "dark"):
                theme.set_mode(mode)
                self.app.processEvents()
                self.assertIn("Microsoft YaHei UI", toast._title.font().families())
                self.assertIsNone(toast.windowHandle())
                self.assertFalse(toast.grab().isNull())

    def test_close_during_progress_and_width_animation_stops_every_activity(self):
        toast = ProgressToast.start("很长的下载任务名称，请稍候…", parent=self.parent, indeterminate=True)
        self.settle(toast)
        toast.finish("完成", timeout_ms=100)
        toast._width_motion.setCurrentTime(70)
        destroyed = []
        toast.destroyed.connect(lambda: destroyed.append(True))
        QTest.mouseClick(toast.close_button, QtCore.Qt.MouseButton.LeftButton)
        self.assertFalse(toast._timeout.isActive())
        self.assertEqual(toast._activity.state(), QtCore.QAbstractAnimation.State.Stopped)
        self.assertEqual(toast._width_motion.state(), QtCore.QAbstractAnimation.State.Stopped)
        QTest.qWait(ProgressToast.HIDE_DURATION + 40)
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertEqual(destroyed, [True])
        QTest.qWait(120)
        self.assertEqual(destroyed, [True])

    def test_parent_hide_dismisses_without_resurrection(self):
        toast = ProgressToast("任务进行中", parent=self.parent, indeterminate=True)
        toast.show_at()
        self.settle(toast)
        self.parent.hide()
        self.app.processEvents()
        self.assertFalse(toast.isVisible())
        self.assertEqual(toast._activity.state(), QtCore.QAbstractAnimation.State.Stopped)
        self.parent.show()
        self.app.processEvents()
        self.assertFalse(toast.isVisible())

    def test_worker_signal_updates_progress_on_gui_thread(self):
        toast = ProgressToast.start("处理中", parent=self.parent)
        worker = _Worker()
        received = []
        toast.progressChanged.connect(lambda value: received.append((value, QtCore.QThread.currentThread())))
        worker.progress.connect(toast.set_progress)
        worker.start()
        self.assertTrue(worker.wait(1000))
        self.app.processEvents()
        self.assertEqual(received, [(63.0, self.app.thread())])
        self.assertEqual(toast.value(), 63)

    def test_invalid_placement_and_negative_timeout_have_no_side_effect(self):
        before = len(self.parent.findChildren(ProgressToast))
        with self.assertRaises(ValueError):
            ProgressToast.start("不会创建", parent=self.parent, placement="somewhere")
        self.assertEqual(len(self.parent.findChildren(ProgressToast)), before)
        toast = ProgressToast("任务", parent=self.parent)
        with self.assertRaises(ValueError):
            toast.finish(timeout_ms=-1)
        for invalid in (float("nan"), float("inf"), 1.5, "10"):
            with self.assertRaises((TypeError, ValueError)):
                toast.finish(timeout_ms=invalid)
        with self.assertRaises(ValueError):
            toast.finish(timeout_ms=2**31)
        self.assertEqual(toast.state(), "running")

    def test_demo_rapid_retrigger_close_and_destruction_have_no_late_callbacks(self):
        example_dir = str(Path(__file__).resolve().parents[1] / "examples")
        sys.path.insert(0, example_dir)
        try:
            from progress_toast import ProgressToastExamples
            demo = ProgressToastExamples(self.parent)
        finally:
            sys.path.remove(example_dir)
        demo.show()
        for placement in Toast.PLACEMENTS:
            demo.start_task(placement)
            for _ in range(5):
                demo.start_task(placement)
        QTest.qWait(ProgressToast.HIDE_DURATION + 70)
        self.assertEqual(len(demo._tasks), 6*len(Toast.PLACEMENTS))
        demo.fail_tasks()
        self.assertTrue(all(toast.state() == "error" for toast, _timeline in demo._tasks.values()))
        demo.hide()
        QTest.qWait(ProgressToast.HIDE_DURATION + 40)
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertEqual(demo._tasks, {})
        demo.show()
        demo.start_task("bottom-right")
        self.parent.deleteLater()
        self.parent = None
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        QTest.qWait(100)


if __name__ == "__main__":
    unittest.main()
